from typing import Dict, Any, List
from fastapi import APIRouter
from ..ingest.cleaner import (
    get_cleaning_audit_summary,
    get_table_cleaning_audit,
    clean_and_remediate_dataframe,
)
from ..db.engine import list_all_tables, execute_query_to_df, get_connection

router = APIRouter(prefix="/api/cleaning", tags=["Data Cleaning & Remediation"])

@router.get("/audit")
async def get_all_cleaning_audits() -> List[Dict[str, Any]]:
    """Returns the full data quality and cleaning audit report for all loaded datasets."""
    return get_cleaning_audit_summary()

@router.get("/audit/{table_name}")
async def get_single_table_audit(table_name: str) -> Dict[str, Any]:
    """Returns specific data quality and cleaning remediation report for a table."""
    return get_table_cleaning_audit(table_name)

@router.post("/remediate")
async def remediate_all_tables() -> Dict[str, Any]:
    """Runs automated data cleaning and casing harmonization across all active tables."""
    tables = list_all_tables()
    remediated = []
    for tbl in tables:
        df, err = execute_query_to_df(f"SELECT * FROM \"{tbl}\";")
        if err or df is None:
            continue
        df_clean, audit = clean_and_remediate_dataframe(df, tbl)
        with get_connection(readonly=False) as conn:
            df_clean.to_sql(name=tbl, con=conn, if_exists="replace", index=False)
        remediated.append(audit)

    return {
        "status": "success",
        "message": f"Successfully remediated {len(remediated)} tables in SQLite.",
        "audits": get_cleaning_audit_summary(),
    }

