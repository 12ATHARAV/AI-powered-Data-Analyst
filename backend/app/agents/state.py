from typing import Any, Dict, List, Optional, TypedDict

class LogEntry(TypedDict, total=False):
    timestamp: str
    level: str  # info, warn, error, success
    agent: str  # Supervisor, SQLCoder, AnomalyHunter, etc.
    action: str
    details: Optional[Any]

class AgentState(TypedDict, total=False):
    session_id: str
    query: str
    messages: List[Dict[str, str]]
    schema_context: str
    eda_context: str
    plan: List[str]
    current_agent: str
    active_logs: List[Dict[str, Any]]
    
    # Tool outputs
    sql_query: Optional[str]
    sql_columns: Optional[List[str]]
    sql_rows: Optional[List[Dict[str, Any]]]
    sql_error: Optional[str]
    pandas_code: Optional[str]
    pandas_result: Optional[Any]
    
    anomalies: Optional[List[Dict[str, Any]]]
    chart_spec: Optional[Dict[str, Any]]
    
    # Synthesis
    reasoning: Optional[str]
    final_answer: Optional[str]
    model_used: Optional[str]
    provider: Optional[str]
