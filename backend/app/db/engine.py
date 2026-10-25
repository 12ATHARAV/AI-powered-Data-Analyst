import sqlite3
import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from ..config import settings

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)

def get_connection(readonly: bool = False) -> sqlite3.Connection:
    """Return a standard sqlite3 connection with row dictionary access."""
    if readonly:
        # URI mode for read-only connection
        uri = f"file:{settings.DATABASE_PATH}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(settings.DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def execute_safe_query(
    query: str,
    max_rows: int = 200,
    allow_write: bool = False,
) -> Tuple[List[Dict[str, Any]], List[str], Optional[str]]:
    """
    Executes a SELECT query safely against the SQLite database.
    Returns: (rows as list of dicts, column_names, error_message)
    """
    cleaned_query = query.strip().rstrip(";")
    if not cleaned_query:
        return [], [], "Empty query provided"

    # Enforce SELECT only unless allow_write is explicitly True
    if not allow_write:
        # Check forbidden keywords
        # Note: CTEs with WITH ... SELECT are allowed
        first_token = cleaned_query.split()[0].upper()
        if first_token not in ("SELECT", "WITH", "EXPLAIN"):
            return [], [], f"Only SELECT/WITH analytical queries are permitted. Got: {first_token}"

        if FORBIDDEN_SQL_PATTERN.search(cleaned_query):
            # Verify if it's within quotes or actually a mutation statement
            match = FORBIDDEN_SQL_PATTERN.search(cleaned_query)
            # Extra safety check
            if match and any(cleaned_query.upper().startswith(kw) for kw in ["DROP", "DELETE", "UPDATE", "INSERT"]):
                return [], [], f"Mutation operation '{match.group()}' is strictly prohibited."

    try:
        with get_connection(readonly=not allow_write) as conn:
            cursor = conn.cursor()
            cursor.execute(cleaned_query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [dict(row) for row in cursor.fetchmany(max_rows)]
            return rows, columns, None
    except Exception as e:
        return [], [], str(e)

def execute_query_to_df(query: str, allow_write: bool = False) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Executes a query and returns a pandas DataFrame."""
    cleaned_query = query.strip().rstrip(";")
    if not allow_write and FORBIDDEN_SQL_PATTERN.search(cleaned_query):
        return None, "Mutation operations are prohibited"
    try:
        with get_connection(readonly=not allow_write) as conn:
            df = pd.read_sql_query(cleaned_query, conn)
            return df, None
    except Exception as e:
        return None, str(e)

def list_all_tables() -> List[str]:
    """Returns list of user tables in the SQLite database."""
    try:
        with get_connection(readonly=True) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_system_%';")
            return [row["name"] for row in cursor.fetchall()]
    except Exception:
        return []

def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
    """Returns column information for a table: name, type, notnull, dflt_value, pk."""
    try:
        with get_connection(readonly=True) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []

def get_table_row_count(table_name: str) -> int:
    """Returns total row count for a table."""
    try:
        with get_connection(readonly=True) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) as cnt FROM \"{table_name}\";")
            res = cursor.fetchone()
            return res["cnt"] if res else 0
    except Exception:
        return 0

def get_complete_db_schema_prompt() -> str:
    """
    Builds a formatted DDL and schema context prompt for LLMs to generate valid SQL.
    Includes table names, column names, types, row counts, and sample row.
    """
    tables = list_all_tables()
    if not tables:
        return "No tables currently loaded in the database. Please prompt the user to upload CSV files first."

    lines = ["Available Database Tables & Schema:"]
    for tbl in tables:
        cols = get_table_schema(tbl)
        cnt = get_table_row_count(tbl)
        col_desc = ", ".join([f"{c['name']} ({c['type']})" for c in cols])
        lines.append(f"\nTable '{tbl}' (Row count: {cnt}):\n  Columns: {col_desc}")
        
        # Sample row
        rows, _, _ = execute_safe_query(f"SELECT * FROM \"{tbl}\" LIMIT 1;", max_rows=1)
        if rows:
            lines.append(f"  Sample row: {rows[0]}")

    return "\n".join(lines)
