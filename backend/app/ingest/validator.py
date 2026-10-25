from typing import Dict, Any, List
import pandas as pd
from ..db.engine import get_connection, list_all_tables, execute_query_to_df

def validate_table_quality(table_name: str) -> Dict[str, Any]:
    """
    Performs comprehensive data quality audit for a given table:
    - Missingness analysis
    - Duplicate detection
    - Data type distribution
    - Anomaly warnings (negative values, excessive nulls)
    - Data Health Score (0-100)
    """
    df, err = execute_query_to_df(f"SELECT * FROM \"{table_name}\";")
    if err or df is None:
        return {"error": err or "Failed to load table"}

    total_rows = len(df)
    total_cols = len(df.columns)
    if total_rows == 0:
        return {
            "table_name": table_name,
            "row_count": 0,
            "column_count": total_cols,
            "health_score": 0,
            "warnings": ["Table is empty"],
        }

    # Missing values
    null_counts = df.isnull().sum()
    null_pct = (null_counts / total_rows * 100).round(2)
    missing_summary = [
        {"column": col, "null_count": int(null_counts[col]), "null_pct": float(null_pct[col])}
        for col in df.columns if null_counts[col] > 0
    ]

    # Duplicate rows
    duplicate_count = int(df.duplicated().sum())
    duplicate_pct = round(duplicate_count / total_rows * 100, 2)

    # Health score calculations
    # Start with 100, deduct points for nulls, duplicates, zero-variance
    score = 100.0
    warnings = []

    # Penalty for missing values
    overall_null_pct = float(df.isnull().mean().mean() * 100)
    score -= min(30.0, overall_null_pct * 1.5)
    if overall_null_pct > 15:
        warnings.append(f"High overall missingness: {overall_null_pct:.1f}% of data is null.")

    # Penalty for duplicates
    score -= min(25.0, duplicate_pct * 2.0)
    if duplicate_count > 0:
        warnings.append(f"Found {duplicate_count} ({duplicate_pct}%) duplicate rows.")

    # Check for constant / zero-variance columns
    constant_cols = [col for col in df.columns if df[col].nunique(dropna=True) <= 1 and total_rows > 1]
    if constant_cols:
        score -= min(15.0, len(constant_cols) * 5.0)
        warnings.append(f"Constant/Zero-variance columns detected: {', '.join(constant_cols)}")

    # Check for domain anomalies (negative values in price/quantity/revenue)
    for col in df.select_dtypes(include=["number"]).columns:
        if any(term in col.lower() for term in ["price", "quantity", "cost", "revenue", "amount"]):
            neg_count = int((df[col] < 0).sum())
            if neg_count > 0:
                score -= 10.0
                warnings.append(f"Column '{col}' has {neg_count} negative values, which may violate business rules.")
        if "discount" in col.lower():
            over_one = int((df[col] > 1.0).sum())
            if over_one > 0:
                warnings.append(f"Column '{col}' has {over_one} values exceeding 1.0 (100% discount).")

    final_score = max(0, min(100, round(score, 1)))

    return {
        "table_name": table_name,
        "row_count": total_rows,
        "column_count": total_cols,
        "health_score": final_score,
        "duplicate_rows": duplicate_count,
        "duplicate_pct": duplicate_pct,
        "missing_summary": missing_summary,
        "constant_columns": constant_cols,
        "warnings": warnings,
        "is_healthy": final_score >= 80,
    }

def discover_inter_table_relationships() -> List[Dict[str, Any]]:
    """
    Scans all tables in the database to detect potential foreign key joins.
    E.g. sales.customer_id -> customers.customer_id
    """
    tables = list_all_tables()
    table_schemas: Dict[str, List[str]] = {}
    for tbl in tables:
        df, _ = execute_query_to_df(f"SELECT * FROM \"{tbl}\" LIMIT 1;")
        if df is not None:
            table_schemas[tbl] = list(df.columns)

    relationships = []
    for source_tbl, s_cols in table_schemas.items():
        for target_tbl, t_cols in table_schemas.items():
            if source_tbl == target_tbl:
                continue
            for col in s_cols:
                # Direct match on *_id or id
                if (col.endswith("_id") or col == "id") and col in t_cols:
                    # Avoid duplicate inverted reporting
                    join_key = f"{source_tbl}.{col} -> {target_tbl}.{col}"
                    relationships.append({
                        "source_table": source_tbl,
                        "source_column": col,
                        "target_table": target_tbl,
                        "target_column": col,
                        "join_sql": f"JOIN \"{target_tbl}\" ON \"{source_tbl}\".\"{col}\" = \"{target_tbl}\".\"{col}\"",
                        "description": f"Enables multi-file join between '{source_tbl}' and '{target_tbl}' on '{col}'",
                    })

    return relationships
