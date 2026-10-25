import os
import re
import shutil
import sqlite3
import time
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from ..config import settings

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)

# Request context variable to transparently route database calls to the caller's session DB
session_context: ContextVar[str] = ContextVar("session_context", default="default")

def get_database_path_for_session(session_id: Optional[str] = None) -> str:
    """
    Returns the absolute path to the SQLite database for a given session.
    - If session_id is 'default' or omitted (e.g. tests or initial seeding), uses settings.DATABASE_PATH.
    - If session_id is specified (e.g. LinkedIn visitor), uses an isolated storage/sessions/{session_id}.db.
    - Automatically clones base sample tables into fresh visitor sessions for zero-friction exploration.
    """
    if session_id is None:
        session_id = session_context.get()

    if not session_id or session_id == "default":
        return settings.DATABASE_PATH

    clean_id = re.sub(r"[^a-zA-Z0-9_\-]", "", session_id)
    if not clean_id:
        return settings.DATABASE_PATH

    sessions_dir = Path(settings.DATABASE_PATH).parent / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_db = sessions_dir / f"{clean_id}.db"

    # Seed fresh session with base database tables if it doesn't exist yet
    if not session_db.exists():
        base_db = Path(settings.DATABASE_PATH)
        if base_db.exists() and base_db.stat().st_size > 0:
            try:
                shutil.copyfile(base_db, session_db)
            except Exception:
                pass

    return str(session_db)

def get_connection(readonly: bool = False, session_id: Optional[str] = None) -> sqlite3.Connection:
    """
    Return an optimized SQLite connection with dictionary row access,
    WAL mode, and a 15-second busy timeout to prevent 'database is locked' errors.
    """
    db_path = get_database_path_for_session(session_id)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    if readonly:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False, timeout=15.0)
        try:
            conn.execute("PRAGMA busy_timeout=15000;")
        except Exception:
            pass
    else:
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=15.0)
        try:
            # Enable Write-Ahead Logging (WAL) for high concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=15000;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA cache_size=-64000;")
        except Exception:
            pass

    conn.row_factory = sqlite3.Row
    return conn

def execute_safe_query(
    query: str,
    max_rows: int = 200,
    allow_write: bool = False,
    session_id: Optional[str] = None,
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
        first_token = cleaned_query.split()[0].upper()
        if first_token not in ("SELECT", "WITH", "EXPLAIN"):
            return [], [], f"Only SELECT/WITH analytical queries are permitted. Got: {first_token}"

        if FORBIDDEN_SQL_PATTERN.search(cleaned_query):
            match = FORBIDDEN_SQL_PATTERN.search(cleaned_query)
            if match and any(cleaned_query.upper().startswith(kw) for kw in ["DROP", "DELETE", "UPDATE", "INSERT"]):
                return [], [], f"Mutation operation '{match.group()}' is strictly prohibited."

    try:
        with get_connection(readonly=not allow_write, session_id=session_id) as conn:
            cursor = conn.cursor()
            cursor.execute(cleaned_query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [dict(row) for row in cursor.fetchmany(max_rows)]
            return rows, columns, None
    except Exception as e:
        return [], [], str(e)

def execute_query_to_df(
    query: str,
    allow_write: bool = False,
    session_id: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Executes a query and returns a pandas DataFrame."""
    cleaned_query = query.strip().rstrip(";")
    if not allow_write and FORBIDDEN_SQL_PATTERN.search(cleaned_query):
        return None, "Mutation operations are prohibited"
    try:
        with get_connection(readonly=not allow_write, session_id=session_id) as conn:
            df = pd.read_sql_query(cleaned_query, conn)
            return df, None
    except Exception as e:
        return None, str(e)

def list_all_tables(session_id: Optional[str] = None) -> List[str]:
    """Returns list of user tables in the SQLite database."""
    try:
        with get_connection(readonly=True, session_id=session_id) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_system_%';")
            return [row["name"] for row in cursor.fetchall()]
    except Exception:
        return []

def get_table_schema(table_name: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns column information for a table: name, type, notnull, dflt_value, pk."""
    try:
        with get_connection(readonly=True, session_id=session_id) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []

def get_table_row_count(table_name: str, session_id: Optional[str] = None) -> int:
    """Returns total row count for a table."""
    try:
        with get_connection(readonly=True, session_id=session_id) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) as cnt FROM \"{table_name}\";")
            res = cursor.fetchone()
            return res["cnt"] if res else 0
    except Exception:
        return 0

def get_complete_db_schema_prompt(session_id: Optional[str] = None) -> str:
    """
    Builds a formatted DDL and schema context prompt for LLMs to generate valid SQL.
    Includes table names, column names, types, row counts, and sample row.
    """
    tables = list_all_tables(session_id=session_id)
    if not tables:
        return "No tables currently loaded in the database. Please prompt the user to upload CSV files first."

    lines = ["Available Database Tables & Schema:"]
    for tbl in tables:
        cols = get_table_schema(tbl, session_id=session_id)
        cnt = get_table_row_count(tbl, session_id=session_id)
        col_desc = ", ".join([f"{c['name']} ({c['type']})" for c in cols])
        lines.append(f"\nTable '{tbl}' (Row count: {cnt}):\n  Columns: {col_desc}")
        
        # Sample row
        rows, _, _ = execute_safe_query(f"SELECT * FROM \"{tbl}\" LIMIT 1;", max_rows=1, session_id=session_id)
        if rows:
            lines.append(f"  Sample row: {rows[0]}")

    return "\n".join(lines)

def cleanup_expired_sessions(max_age_hours: int = 4) -> int:
    """Deletes session databases older than max_age_hours to prevent disk bloat."""
    sessions_dir = Path(settings.DATABASE_PATH).parent / "sessions"
    if not sessions_dir.exists():
        return 0

    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    removed_count = 0

    for db_file in sessions_dir.glob("*.db*"):
        try:
            if db_file.stat().st_mtime < cutoff:
                db_file.unlink(missing_ok=True)
                removed_count += 1
        except Exception:
            pass

    return removed_count
