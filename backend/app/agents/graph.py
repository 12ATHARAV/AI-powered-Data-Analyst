import json
import re
import datetime
from typing import Any, Callable, Dict, List, Optional
from langgraph.graph import StateGraph, END

from .state import AgentState, LogEntry
from .prompts import (
    SUPERVISOR_PROMPT,
    SQL_CODER_PROMPT,
    CHART_DESIGNER_PROMPT,
    SYNTHESIZER_PROMPT,
)
from ..llm.client import llm_client
from ..db.engine import (
    execute_safe_query,
    get_complete_db_schema_prompt,
    list_all_tables,
)
from ..eda.profiler import get_complete_eda_summary_text
from ..eda.anomaly import detect_all_table_anomalies, detect_column_anomalies
from ..ingest.validator import discover_inter_table_relationships

def extract_json_block(text: str) -> Dict[str, Any]:
    """Robust extractor for JSON objects from LLM output."""
    clean = text.strip()
    # Try finding ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Try finding outermost { ... }
    first_brace = clean.find("{")
    last_brace = clean.rfind("}")
    if first_brace != -1 and last_brace != -1:
        try:
            return json.loads(clean[first_brace : last_brace + 1])
        except Exception:
            pass
    # Direct parse
    return json.loads(clean)

def create_log(agent: str, action: str, level: str = "info", details: Any = None) -> Dict[str, Any]:
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    return {
        "timestamp": now_str,
        "agent": agent,
        "action": action,
        "level": level,
        "details": details,
    }

# ----------------- NODE IMPLEMENTATIONS ----------------- #

def supervisor_node(state: AgentState, log_hook: Optional[Callable[[Dict[str, Any]], None]] = None) -> AgentState:
    """Decomposes the query and sets analytical plan and agent routing."""
    query = state.get("query", "")
    schema = state.get("schema_context", "") or get_complete_db_schema_prompt()
    eda = state.get("eda_context", "") or get_complete_eda_summary_text()
    rels = discover_inter_table_relationships()
    rel_text = "\n".join([r["description"] for r in rels]) if rels else "None detected"

    log_entry = create_log(
        "Chief Data Analyst (Supervisor)",
        f"Analyzing query: '{query}' and decomposing into analytical plan.",
        "info"
    )
    if log_hook:
        log_hook(log_entry)

    system_prompt = f"{SUPERVISOR_PROMPT}\n\n{schema}\n\nDetected Relationships:\n{rel_text}\n\n{eda}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"User Analytical Query: {query}"},
    ]

    # Incorporate previous conversation context if available
    prev_msgs = state.get("messages", [])[-4:]
    if prev_msgs:
        context_str = "\n".join([f"{m['role']}: {m['content']}" for m in prev_msgs])
        messages.insert(1, {"role": "system", "content": f"Previous conversation context:\n{context_str}"})

    failover_log = None
    def handle_failover(orig_m, fall_m):
        nonlocal failover_log
        failover_log = create_log(
            "System Failover",
            f"Primary model {orig_m} hit limit/timeout. Rerouted to fallback {fall_m}.",
            "warn"
        )
        if log_hook:
            log_hook(failover_log)

    res = llm_client.chat_completion(messages, temperature=0.1, on_failover=handle_failover)
    
    plan = ["Query interpretation"]
    requires_sql = True
    requires_anomaly = any(w in query.lower() for w in ["anomaly", "outlier", "unusual", "underperform", "weird", "flag"])
    requires_chart = any(w in query.lower() for w in ["chart", "trend", "show", "visualize", "plot", "distribution", "breakdown", "top", "monthly", "revenue"])
    chart_type = "bar"

    try:
        parsed = extract_json_block(res["content"])
        plan = parsed.get("plan", plan)
        requires_sql = parsed.get("requires_sql", requires_sql)
        requires_anomaly = parsed.get("requires_anomaly", requires_anomaly) or requires_anomaly
        requires_chart = parsed.get("requires_chart", requires_chart) or requires_chart
        chart_type = parsed.get("suggested_chart_type", "bar")
    except Exception:
        pass

    state["plan"] = plan
    state["current_agent"] = "Supervisor"
    state["model_used"] = res["model_used"]
    state["provider"] = res["provider"]
    state.setdefault("active_logs", []).append(log_entry)

    plan_log = create_log(
        "Chief Data Analyst (Supervisor)",
        f"Execution Plan: {', '.join(plan)} | SQL: {requires_sql} | Anomaly: {requires_anomaly} | Chart: {requires_chart} ({chart_type})",
        "info",
        {"plan": plan, "requires_sql": requires_sql, "requires_anomaly": requires_anomaly, "requires_chart": requires_chart}
    )
    if log_hook:
        log_hook(plan_log)
    state["active_logs"].append(plan_log)

    return state

def sql_coder_node(state: AgentState, log_hook: Optional[Callable[[Dict[str, Any]], None]] = None) -> AgentState:
    """Generates, sanitizes, and executes SQLite queries with self-healing error recovery."""
    query = state.get("query", "")
    schema = state.get("schema_context", "") or get_complete_db_schema_prompt()
    rels = discover_inter_table_relationships()
    rel_text = "\n".join([f"- {r['description']} (SQL: {r['join_sql']})" for r in rels])

    log_entry = create_log(
        "SQL & Pandas Coder Agent",
        "Formulating relational SQL query across active tables...",
        "info"
    )
    if log_hook:
        log_hook(log_entry)

    system_prompt = f"{SQL_CODER_PROMPT}\n\n{schema}\n\nInter-Table Join Reference:\n{rel_text}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"User Analytical Query: {query}\nSupervisor Plan: {state.get('plan', [])}"},
    ]

    max_attempts = 2
    executed_rows = []
    columns = []
    sql_error = None
    final_sql = ""
    pandas_code = ""

    for attempt in range(max_attempts):
        res = llm_client.chat_completion(messages, temperature=0.1)
        try:
            parsed = extract_json_block(res["content"])
            final_sql = parsed.get("sql_query", "").strip()
            pandas_code = parsed.get("pandas_alternative", "")
        except Exception:
            # Multi-strategy fallback extraction: fenced sql block first, then any SELECT
            match = re.search(
                r"```(?:sql)?\s*(SELECT\b.*?|WITH\b.*?)(?:```|$)",
                res["content"],
                re.IGNORECASE | re.DOTALL,
            )
            if not match:
                match = re.search(r"((?:SELECT|WITH)\s+.*?;?)", res["content"], re.IGNORECASE | re.DOTALL)
            final_sql = match.group(1).strip().rstrip(";") + ";" if match else "SELECT 1;"

        # Log query attempt
        sql_log = create_log(
            "SQL & Pandas Coder Agent",
            f"Executing SQL (attempt {attempt+1}): {final_sql}",
            "info",
            {"sql": final_sql}
        )
        if log_hook:
            log_hook(sql_log)

        rows, cols, err = execute_safe_query(final_sql, max_rows=150)
        if not err:
            executed_rows = rows
            columns = cols
            sql_error = None
            success_log = create_log(
                "SQL & Pandas Coder Agent",
                f"Query succeeded with {len(rows)} rows returned in {cols}.",
                "success",
                {"row_count": len(rows), "columns": cols}
            )
            if log_hook:
                log_hook(success_log)
            state.setdefault("active_logs", []).append(success_log)
            break
        else:
            sql_error = err
            err_log = create_log(
                "SQL & Pandas Coder Agent",
                f"SQL Execution Error: {err}. Attempting self-healing query repair...",
                "warn",
                {"error": err, "failed_sql": final_sql}
            )
            if log_hook:
                log_hook(err_log)
            # Add error feedback to prompt for retry
            messages.append({"role": "assistant", "content": json.dumps({"sql_query": final_sql})})
            messages.append({"role": "user", "content": f"SQL Error encountered: {err}. Please fix the query."})

    state["sql_query"] = final_sql
    state["pandas_code"] = pandas_code
    state["sql_rows"] = executed_rows
    state["sql_columns"] = columns
    state["sql_error"] = sql_error
    return state

def anomaly_hunter_node(state: AgentState, log_hook: Optional[Callable[[Dict[str, Any]], None]] = None) -> AgentState:
    """Scans for statistical & domain anomalies with explanatory causal reasoning."""
    query = state.get("query", "").lower()
    tables = list_all_tables()
    anomalies_detected = []

    log_entry = create_log(
        "Anomaly Hunter Agent",
        "Executing statistical IQR & Z-score diagnostics on relevant datasets...",
        "info"
    )
    if log_hook:
        log_hook(log_entry)

    # If specific table mentioned, prioritize that table; otherwise scan all
    target_tables = [t for t in tables if t.lower() in query] or tables

    for tbl in target_tables:
        anoms = detect_all_table_anomalies(tbl, max_per_col=3)
        for a in anoms:
            if a.get("anomalies_found", 0) > 0:
                anomalies_detected.append(a)

    if anomalies_detected:
        diag_log = create_log(
            "Anomaly Hunter Agent",
            f"Flagged anomalies across {len(anomalies_detected)} metric columns with statistical explanations.",
            "warn",
            {"anomaly_count": len(anomalies_detected)}
        )
        if log_hook:
            log_hook(diag_log)
        state.setdefault("active_logs", []).append(diag_log)

    state["anomalies"] = anomalies_detected
    return state

def _is_numeric_series(values: List[Any]) -> bool:
    """True if >=80% of non-null values in the column are numbers."""
    nums = [v for v in values if v is not None]
    if not nums:
        return False
    numeric_count = sum(
        1 for v in nums if isinstance(v, (int, float)) and not isinstance(v, bool)
    )
    return numeric_count / len(nums) >= 0.8

def chart_designer_node(state: AgentState, log_hook: Optional[Callable[[Dict[str, Any]], None]] = None) -> AgentState:
    """Formats structured Recharts specification for frontend dynamic rendering."""
    sql_rows = state.get("sql_rows", [])
    sql_cols = state.get("sql_columns", [])
    query = state.get("query", "")

    if not sql_rows or len(sql_rows) == 0 or len(sql_cols) < 2:
        return state

    log_entry = create_log(
        "Visualization Designer Agent",
        "Designing responsive visual chart specification for tabular findings...",
        "info"
    )
    if log_hook:
        log_hook(log_entry)

    # Classify columns so Y axes are always plottable numbers and X is a readable label
    numeric_cols = [c for c in sql_cols if _is_numeric_series([r.get(c) for r in sql_rows])]
    label_cols = [c for c in sql_cols if c not in numeric_cols]
    # Prefer human-readable labels over raw IDs when both exist
    readable_labels = [c for c in label_cols if not c.lower().endswith(("id", "_id", "key", "code"))] or label_cols

    if not numeric_cols:
        viz_skip_log = create_log(
            "Visualization Designer Agent",
            "No numeric columns in result set; skipping chart generation.",
            "warn"
        )
        if log_hook:
            log_hook(viz_skip_log)
        state.setdefault("active_logs", []).append(viz_skip_log)
        return state

    x_cand = readable_labels[0] if readable_labels else sql_cols[0]
    # Avoid plotting raw IDs as metrics when real measures exist
    meaningful_metrics = [c for c in numeric_cols if not c.lower().endswith(("id", "_id", "key", "code"))] or numeric_cols
    y_cand = [c for c in meaningful_metrics if c != x_cand][:2] or [numeric_cols[0]]

    # Sanitize rows: keep only plot keys and coerce numeric Y values, dropping incomplete rows
    chart_data = []
    for row in sql_rows:
        x_val = row.get(x_cand)
        if x_val is None:
            continue
        clean_row: Dict[str, Any] = {x_cand: x_val}
        valid = True
        for key in y_cand:
            val = row.get(key)
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                try:
                    val = float(val)
                except (TypeError, ValueError):
                    valid = False
                    break
            clean_row[key] = val
        if valid:
            chart_data.append(clean_row)

    if not chart_data:
        return state

    # Detect chart type heuristically or through LLM
    q_lower = query.lower()
    c_type = "bar"
    if any(term in x_cand.lower() for term in ["date", "month", "year", "time", "day"]):
        c_type = "line"
    elif "scatter" in q_lower or (len(y_cand) == 2 and "vs" in q_lower):
        c_type = "scatter"
    elif any(t in q_lower for t in ["pie", "share", "proportion", "distribution", "contribution"]) and 2 <= len(chart_data) <= 8:
        c_type = "pie"

    # Never render a single data point as a pie (one-slice donut is meaningless)
    if c_type == "pie" and len(chart_data) < 2:
        c_type = "bar"

    # Cap categories for readable charts (top rows first, data usually pre-sorted)
    max_rows = 8 if c_type == "pie" else 25
    chart_data = chart_data[:max_rows]

    chart_spec = {
        "type": c_type,
        "title": f"Analysis: {x_cand.replace('_', ' ').title()} vs {' & '.join(k.replace('_', ' ').title() for k in y_cand)}",
        "description": f"Visual breakdown answering: '{query}'",
        "xAxisKey": x_cand,
        "yAxisKeys": y_cand,
        "data": chart_data,
    }

    viz_log = create_log(
        "Visualization Designer Agent",
        f"Generated {c_type.upper()} chart spec with {len(chart_data)} data points.",
        "success",
        {"chart_type": c_type, "xAxis": x_cand, "yAxis": y_cand}
    )
    if log_hook:
        log_hook(viz_log)
    state.setdefault("active_logs", []).append(viz_log)

    state["chart_spec"] = chart_spec
    return state

def synthesizer_node(state: AgentState, log_hook: Optional[Callable[[Dict[str, Any]], None]] = None) -> AgentState:
    """Compiles the final executive summary, business reasoning, and recommendations."""
    query = state.get("query", "")
    sql = state.get("sql_query", "")
    rows = state.get("sql_rows", [])
    anomalies = state.get("anomalies", [])
    chart_spec = state.get("chart_spec", {})

    log_entry = create_log(
        "Executive Synthesizer",
        "Drafting executive business takeaways, reasoning, and recommendations...",
        "info"
    )
    if log_hook:
        log_hook(log_entry)

    data_summary = f"SQL Executed:\n{sql}\n\nTop Results (sample {min(10, len(rows))} of {len(rows)}):\n{rows[:10]}"
    anom_summary = "Anomalies Flagged:\n" + "\n".join([a.get("summary", "") for a in anomalies]) if anomalies else "No critical statistical anomalies flagged."

    messages = [
        {"role": "system", "content": SYNTHESIZER_PROMPT},
        {
            "role": "user",
            "content": f"User Query: {query}\n\nData Evidence:\n{data_summary}\n\n{anom_summary}\n\nChart Generated: {bool(chart_spec)}"
        },
    ]

    res = llm_client.chat_completion(messages, temperature=0.3, max_tokens=1500)
    final_text = res["content"]

    done_log = create_log(
        "Executive Synthesizer",
        f"Analysis complete. Delivered synthesis via {res['provider']} ({res['model_used']}).",
        "success"
    )
    if log_hook:
        log_hook(done_log)
    state.setdefault("active_logs", []).append(done_log)

    state["final_answer"] = final_text
    state["reasoning"] = f"1. Supervisor decomposed user query.\n2. Executed SQL: `{sql}`\n3. Checked anomaly diagnostics (Found {len(anomalies)}).\n4. Generated interactive {chart_spec.get('type', 'bar')} visualization."
    return state

# ----------------- GRAPH COMPILER ----------------- #

def build_data_analyst_graph(log_hook: Optional[Callable[[Dict[str, Any]], None]] = None):
    """Compiles the LangGraph state machine with specialized agents."""
    builder = StateGraph(AgentState)

    # Wrap nodes with log_hook
    def sup(state): return supervisor_node(state, log_hook)
    def sql(state): return sql_coder_node(state, log_hook)
    def anom(state): return anomaly_hunter_node(state, log_hook)
    def viz(state): return chart_designer_node(state, log_hook)
    def syn(state): return synthesizer_node(state, log_hook)

    builder.add_node("supervisor", sup)
    builder.add_node("sql_coder", sql)
    builder.add_node("anomaly_hunter", anom)
    builder.add_node("chart_designer", viz)
    builder.add_node("synthesizer", syn)

    builder.set_entry_point("supervisor")

    def route_from_supervisor(state: AgentState):
        # Route to SQL first
        return "sql_coder"

    def route_from_sql(state: AgentState):
        query = state.get("query", "").lower()
        if any(w in query for w in ["anomaly", "outlier", "underperform", "weird", "unusual", "why"]):
            return "anomaly_hunter"
        return "chart_designer"

    builder.add_conditional_edges("supervisor", route_from_supervisor, {"sql_coder": "sql_coder"})
    builder.add_conditional_edges("sql_coder", route_from_sql, {
        "anomaly_hunter": "anomaly_hunter",
        "chart_designer": "chart_designer"
    })
    builder.add_edge("anomaly_hunter", "chart_designer")
    builder.add_edge("chart_designer", "synthesizer")
    builder.add_edge("synthesizer", END)

    return builder.compile()
