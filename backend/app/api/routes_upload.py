import os
import io
import shutil
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from ..config import settings
from ..ingest.csv_parser import parse_and_load_csv, sanitize_identifier
from ..ingest.validator import validate_table_quality, discover_inter_table_relationships
from ..db.engine import list_all_tables, get_table_schema, get_table_row_count, execute_safe_query, get_connection

router = APIRouter(prefix="/api", tags=["Data Ingestion"])

@router.post("/upload")
async def upload_csv_files(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """Uploads one or multiple CSV files, validates schemas, and creates SQLite tables."""
    uploaded_tables = []
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        if not file.filename.lower().endswith(".csv"):
            continue
        dest_path = upload_dir / file.filename
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            table_name, meta = parse_and_load_csv(str(dest_path))
            quality = validate_table_quality(table_name)
            uploaded_tables.append({
                "table_name": table_name,
                "original_file": file.filename,
                "metadata": meta,
                "quality": quality,
            })
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process '{file.filename}': {str(e)}")

    relationships = discover_inter_table_relationships()
    from ..ingest.cleaner import get_cleaning_audit_summary, purge_stale_audits
    purge_stale_audits()
    return {
        "status": "success",
        "tables_created": uploaded_tables,
        "relationships_detected": relationships,
        "cleaning_audits": get_cleaning_audit_summary(),
    }

@router.post("/samples/load")
async def load_sample_datasets() -> Dict[str, Any]:
    """Convenient 1-click loading of the provided customer, product, and sales sample CSVs."""
    sample_dir = Path(settings.SAMPLE_DIR)
    if not sample_dir.exists():
        raise HTTPException(status_code=404, detail="Sample directory not found.")

    results = []
    for csv_file in sample_dir.glob("*.csv"):
        table_name, meta = parse_and_load_csv(str(csv_file))
        quality = validate_table_quality(table_name)
        results.append({
            "table_name": table_name,
            "filename": csv_file.name,
            "metadata": meta,
            "quality": quality,
            "cleaning_audit": meta.get("cleaning_audit", {}),
        })

    relationships = discover_inter_table_relationships()
    from ..ingest.cleaner import get_cleaning_audit_summary, purge_stale_audits
    purge_stale_audits()
    return {
        "status": "success",
        "message": f"Successfully loaded and remediated {len(results)} sample datasets into SQLite.",
        "tables": results,
        "relationships": relationships,
        "cleaning_audits": get_cleaning_audit_summary(),
    }

@router.get("/tables")
async def get_all_tables() -> List[Dict[str, Any]]:
    """Lists all user tables with row counts, columns, and quality scores."""
    tables = list_all_tables()
    result = []
    for tbl in tables:
        schema = get_table_schema(tbl)
        cnt = get_table_row_count(tbl)
        quality = validate_table_quality(tbl)
        result.append({
            "name": tbl,
            "row_count": cnt,
            "column_count": len(schema),
            "columns": schema,
            "health_score": quality.get("health_score", 100),
            "warnings": quality.get("warnings", []),
        })
    return result

@router.get("/tables/{name}/preview")
async def get_table_preview(name: str) -> Dict[str, Any]:
    """Returns top 25 rows for a table."""
    rows, cols, err = execute_safe_query(f"SELECT * FROM \"{name}\" LIMIT 25;")
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"table_name": name, "columns": cols, "rows": rows}

@router.get("/tables/{name}/export-csv")
async def export_table_csv(name: str) -> StreamingResponse:
    """Streams the cleaned dataset back to the user as a downloadable CSV file."""
    if name not in list_all_tables():
        raise HTTPException(status_code=404, detail=f"Table '{name}' not found.")
    rows, cols, err = execute_safe_query(f'SELECT * FROM "{name}"')
    if err:
        raise HTTPException(status_code=500, detail=err or "Query failed.")
    df = pd.DataFrame(rows, columns=cols)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    filename = f"{sanitize_identifier(name)}_cleaned.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.get("/relationships")
async def get_relationships() -> List[Dict[str, Any]]:
    """Returns all detected cross-table foreign key relationships."""
    return discover_inter_table_relationships()

@router.delete("/tables/{name}")
async def delete_table(name: str) -> Dict[str, str]:
    """Drops a table from SQLite and removes its cleaning audit."""
    try:
        with get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS \"{name}\";")
            conn.commit()
        from ..ingest.cleaner import remove_table_audit
        remove_table_audit(name)
        return {"status": "success", "message": f"Table '{name}' deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/reset")
async def reset_database() -> Dict[str, str]:
    """Drops all user tables and system metadata to restore clean state."""
    tables = list_all_tables()
    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()
        for tbl in tables:
            cursor.execute(f"DROP TABLE IF EXISTS \"{tbl}\";")
        cursor.execute("DROP TABLE IF EXISTS _system_cleaning_audits;")
        conn.commit()
    from ..ingest.cleaner import clear_all_audits
    clear_all_audits()
    return {"status": "success", "message": "All tables removed from SQLite database."}
