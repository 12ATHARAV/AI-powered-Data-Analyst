import os
import pytest
from pathlib import Path
from backend.app.config import settings
from backend.app.ingest.csv_parser import parse_and_load_csv
from backend.app.ingest.validator import validate_table_quality, discover_inter_table_relationships
from backend.app.eda.profiler import generate_table_eda_profile
from backend.app.eda.anomaly import detect_all_table_anomalies, detect_column_anomalies
from backend.app.db.engine import list_all_tables, execute_safe_query

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "samples"

def test_csv_ingestion_and_sqlite_loading():
    """Verify that sample CSVs load into SQLite properly."""
    sales_csv = SAMPLE_DIR / "sales.csv"
    assert sales_csv.exists(), "sales.csv must exist in data/samples"
    
    table_name, meta = parse_and_load_csv(str(sales_csv))
    assert table_name == "sales"
    assert meta["row_count"] > 1000
    assert "revenue" in [c["name"] for c in meta["columns"]]
    
    # Verify table exists in SQLite
    tables = list_all_tables()
    assert "sales" in tables

def test_duplicate_headers_and_mojibake_are_fixed(tmp_path):
    """Messy CSVs with duplicate headers must not crash and get unique column names."""
    csv = tmp_path / "dup_headers.csv"
    csv.write_text("name,score,raw,name,score\na,1,\"x\ufffd?ÿ\",2,3\nb,2,\"y\ufffd\",4,5\n", encoding="utf-8")
    table_name, meta = parse_and_load_csv(str(csv))
    cols = [c["name"] for c in meta["columns"]]
    # 5 headers sanitized -> name, score, raw, name_2, score_2
    assert len(cols) == len(set(cols)), f"columns must be unique, got {cols}"
    assert "name" in cols and "score_2" in cols

    rows, r_cols, err = execute_safe_query(f'SELECT * FROM "{table_name}"')
    assert err is None and len(rows) == 2
    # Mojibake markers (U+FFFD and legacy '?ÿ' byte pair) fully stripped
    assert rows[0]["raw"] == "x"
    assert "\ufffd" not in str(rows[1]["raw"])
    # Structural fixes surfaced in the audit
    audit = meta["cleaning_audit"]
    assert any(f.get("action") == "Duplicate Header Renamed" for f in audit["structural_fixes"])

def test_generic_messy_csv_is_auto_fixed(tmp_path):
    """ANY messy CSV (not just unclean_data.csv) must auto-repair: ragged rows, '$' text money,
    negative values, inconsistent casing and missing values — no file-specific logic."""
    csv = tmp_path / "another_messy.csv"
    csv.write_text(
        "city,temp,region,revenue,likes\n"
        'Mumbai,32,NORTH,"$1,200",5\n'
        'Delhi,41,north,-300,"475"\n'
        ",,south,600,\n"
        "Extra,Cairo,25,south,100,999\n",  # 6 fields vs 5-header -> ragged, must be dropped
        encoding="utf-8",
    )
    table_name, meta = parse_and_load_csv(str(csv))
    cols = [c["name"] for c in meta["columns"]]
    assert list(dict.fromkeys(cols)) == cols

    rows, r_cols, err = execute_safe_query(f'SELECT * FROM "{table_name}"')
    assert err is None and len(rows) == 3, "ragged row must be dropped, 3 clean rows remain"

    # '$1,200' text money coerced to a real number; -300 sign-inverted
    assert rows[0]["revenue"] == 1200.0
    assert rows[1]["revenue"] == 300.0

    # '"475"' (number in literal quotes) must parse to 475 — NOT fall to median
    assert rows[1]["likes"] == 475.0

    # Missing numeric imputed with column median of [32, 41] = 36.5
    assert rows[2]["temp"] == 36.5

    # Casing harmonized NORTH/north -> North
    assert set(r["region"] for r in rows) == {"North", "south"}

    audit = meta["cleaning_audit"]
    actions = [f["action"] for f in audit["structural_fixes"]]
    assert "Ragged Row Removal" in actions
    assert "Numeric Type Coercion" in actions
    assert audit["duplicates_removed"] == 0

    # No nulls left anywhere — dataset fully queryable
    remaining = sum(int(df_null) for df_null in [sum(v is None for v in r.values()) for r in rows])
    assert remaining == 0


def test_multi_table_relationships():
    """Verify customer and product tables ingestion and foreign key detection."""
    cust_csv = SAMPLE_DIR / "customers.csv"
    prod_csv = SAMPLE_DIR / "products.csv"
    
    parse_and_load_csv(str(cust_csv))
    parse_and_load_csv(str(prod_csv))
    
    tables = list_all_tables()
    assert "customers" in tables
    assert "products" in tables
    
    rels = discover_inter_table_relationships()
    rel_names = [f"{r['source_table']}.{r['source_column']}" for r in rels]
    assert "sales.customer_id" in rel_names
    assert "sales.product_id" in rel_names

def test_sql_safety_enforcement():
    """Verify mutation queries are blocked."""
    _, _, err1 = execute_safe_query("DROP TABLE sales;")
    assert err1 is not None, "DROP TABLE must be blocked"
    
    _, _, err2 = execute_safe_query("DELETE FROM sales WHERE customer_id = 1;")
    assert err2 is not None, "DELETE statement must be blocked"
    
    # Read query must succeed
    rows, cols, err3 = execute_safe_query("SELECT region, SUM(revenue) as total FROM sales GROUP BY region;")
    assert err3 is None
    assert len(rows) > 0
    assert "region" in cols

def test_data_quality_and_profiling():
    """Verify univariate analysis and health scores."""
    quality = validate_table_quality("sales")
    assert "health_score" in quality
    assert quality["health_score"] > 50
    
    eda = generate_table_eda_profile("sales")
    assert "numeric_stats" in eda
    stat_cols = [s["column"] for s in eda["numeric_stats"]]
    assert "revenue" in stat_cols
    assert "correlations" in eda

def test_anomaly_detection_with_explanations():
    """Verify statistical anomaly detection with causal explanations."""
    anomalies = detect_column_anomalies("sales", "revenue", method="iqr")
    assert anomalies["anomalies_found"] > 0
    assert len(anomalies["flagged_rows"]) > 0
    assert "explanation" in anomalies["flagged_rows"][0]
    assert "IQR" in anomalies["flagged_rows"][0]["explanation"]

def test_automated_data_cleaning_and_casing_remediation():
    """Verify that inconsistent region casing, duplicates, and negative revenue are cleaned."""
    from backend.app.ingest.cleaner import get_table_cleaning_audit
    
    # Check region values in SQLite
    rows, _, err = execute_safe_query("SELECT DISTINCT region FROM sales;")
    assert err is None
    distinct_regions = {r["region"] for r in rows}
    
    # Must only contain the 4 clean regions: East, West, North, South
    assert distinct_regions == {"East", "West", "North", "South"}
    assert " east" not in distinct_regions
    assert "EAST" not in distinct_regions
    
    # Check negative revenue was remediated
    neg_rows, _, _ = execute_safe_query("SELECT COUNT(*) as neg_cnt FROM sales WHERE revenue < 0;")
    assert neg_rows[0]["neg_cnt"] == 0
    
    # Check audit record exists
    audit = get_table_cleaning_audit("sales")
    assert audit["duplicates_removed"] == 5
    assert len(audit["casing_fixes"]) >= 2
    assert audit["total_fixes_applied"] >= 7

def test_llm_client_survives_missing_api_keys(monkeypatch):
    """The backend must start even when no LLM keys are configured."""
    from backend.app.config import settings
    from backend.app.llm.client import DualLLMClient

    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")

    client = DualLLMClient()
    assert client.nvidia_client is None
    assert client.groq_client is None
    with pytest.raises(RuntimeError, match="No LLM provider"):
        client.chat_completion([{"role": "user", "content": "hello"}])

def test_chart_designer_picks_numeric_axes_and_labels():
    """Charts must plot numeric Y columns against readable labels, not ID vs text."""
    from backend.app.agents.graph import chart_designer_node

    state = {
        "query": "which top 3 customers purchased the most",
        "sql_rows": [
            {"customer_id": 179, "name": "Customer 179", "total_revenue": 56347.02, "total_orders": 21},
            {"customer_id": 71, "name": "Customer 071", "total_revenue": 40636.05, "total_orders": 37},
            {"customer_id": 103, "name": "Customer 103", "total_revenue": 36896.29, "total_orders": 36},
        ],
        "sql_columns": ["customer_id", "name", "total_revenue", "total_orders"],
    }
    result = chart_designer_node(state)
    spec = result["chart_spec"]
    assert spec["xAxisKey"] == "name"
    assert "total_revenue" in spec["yAxisKeys"]
    for row in spec["data"]:
        assert isinstance(row["total_revenue"], float)
        assert "customer_id" not in row  # unplotable keys stripped

def test_application_imports_and_routes_registered():
    """Verify the full FastAPI app (incl. agent graph) imports and all routers are wired."""
    from backend.app.main import app

    paths = {route.path for route in app.routes}
    for expected in [
        "/api/health",
        "/api/upload",
        "/api/tables",
        "/api/relationships",
        "/api/eda/anomalies",
        "/api/dashboard/generate",
        "/api/chat/stream",
        "/api/cleaning/audit",
    ]:
        assert expected in paths, f"Route {expected} not registered"

@pytest.mark.anyio
async def test_dashboard_and_health_generation():
    """Verify executive dashboard and health endpoints generate KPIs and charts."""
    from backend.app.api.routes_dashboard import generate_dashboard
    from backend.app.api.routes_health import health_check
    from backend.app.api.routes_cleaning import get_all_cleaning_audits

    dash = await generate_dashboard()
    assert dash["has_data"] is True
    assert len(dash["kpis"]) >= 4
    assert len(dash["charts"]) >= 3
    assert len(dash["anomalies"]) >= 1

    health = await health_check()
    assert health["status"] == "online"
    assert health["database"]["table_count"] >= 3

    audits = await get_all_cleaning_audits()
    assert len(audits) >= 1

