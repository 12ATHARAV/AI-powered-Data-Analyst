from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from ..eda.profiler import generate_table_eda_profile
from ..eda.anomaly import detect_all_workspace_anomalies, detect_all_table_anomalies
from ..db.engine import list_all_tables

router = APIRouter(prefix="/api/eda", tags=["Exploratory Data Analysis"])

@router.get("/profile/{table_name}")
async def get_table_eda(table_name: str) -> Dict[str, Any]:
    """Returns complete univariate and bivariate statistics for a table."""
    tables = list_all_tables()
    if table_name not in tables:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist.")
    profile = generate_table_eda_profile(table_name)
    if "error" in profile:
        raise HTTPException(status_code=400, detail=profile["error"])
    return profile

@router.get("/anomalies")
async def get_workspace_anomalies() -> List[Dict[str, Any]]:
    """Scans all tables and returns statistical outliers with causal explanations."""
    return detect_all_workspace_anomalies()

@router.get("/anomalies/{table_name}")
async def get_table_anomalies(table_name: str) -> List[Dict[str, Any]]:
    """Returns anomalies for a specific table."""
    tables = list_all_tables()
    if table_name not in tables:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist.")
    return detect_all_table_anomalies(table_name)
