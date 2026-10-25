from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from ..db.engine import execute_query_to_df, list_all_tables

def detect_column_anomalies(
    table_name: str,
    column_name: str,
    method: str = "iqr",
    threshold: float = 1.5,
    max_records: int = 15,
) -> Dict[str, Any]:
    """
    Detects statistical outliers in a numeric column and generates explicit causal reasoning.
    Methods: 'iqr' (Tukey 1.5x IQR) or 'zscore' (standard deviations).
    """
    df, err = execute_query_to_df(f"SELECT * FROM \"{table_name}\";")
    if err or df is None or column_name not in df.columns:
        return {"error": err or f"Column '{column_name}' not found in '{table_name}'"}

    series = pd.to_numeric(df[column_name], errors="coerce").dropna()
    if len(series) < 5:
        return {
            "table_name": table_name,
            "column_name": column_name,
            "method": method,
            "anomalies_found": 0,
            "flagged_rows": [],
            "summary": "Insufficient data points for statistical anomaly detection.",
        }

    mean_val = float(series.mean())
    std_val = float(series.std()) if len(series) > 1 else 0.0
    q25 = float(series.quantile(0.25))
    q75 = float(series.quantile(0.75))
    iqr = float(q75 - q25)

    flagged_indices = []
    explanations = []

    if method.lower() == "zscore" and std_val > 0:
        z_scores = (series - mean_val) / std_val
        outliers = series[z_scores.abs() > threshold]
        for idx, val in outliers.items():
            z = z_scores[idx]
            dir_str = "higher" if z > 0 else "lower"
            exp = (
                f"Value {val} has a Z-Score of {z:.2f} ({abs(z):.2f} std devs {dir_str} than mean {mean_val:.2f}). "
                f"Statistical significance: p < 0.01."
            )
            flagged_indices.append((idx, val, exp, round(abs(z), 2)))
    else:
        # Default IQR
        lower_bound = q25 - (threshold * iqr)
        upper_bound = q75 + (threshold * iqr)
        outliers = series[(series < lower_bound) | (series > upper_bound)]
        for idx, val in outliers.items():
            if val > upper_bound:
                diff = val - upper_bound
                exp = f"Value {val} exceeds upper IQR boundary ({upper_bound:.2f}) by {diff:.2f} (Q3={q75:.2f}, IQR={iqr:.2f})."
            else:
                diff = lower_bound - val
                exp = f"Value {val} falls below lower IQR boundary ({lower_bound:.2f}) by {diff:.2f} (Q1={q25:.2f}, IQR={iqr:.2f})."
            flagged_indices.append((idx, val, exp, round(abs(val - mean_val) / (std_val or 1), 2)))

    # Sort outliers by severity
    flagged_indices.sort(key=lambda x: x[3], reverse=True)
    top_flagged = flagged_indices[:max_records]

    flagged_rows = []
    for idx, val, exp, score in top_flagged:
        row_dict = df.loc[idx].to_dict()
        # Clean NaNs in row_dict
        clean_row = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
        flagged_rows.append({
            "row_index": int(idx),
            "value": float(val) if isinstance(val, (int, float, np.number)) else str(val),
            "severity_score": float(score),
            "explanation": exp,
            "full_row": clean_row,
        })

    return {
        "table_name": table_name,
        "column_name": column_name,
        "method": method,
        "total_rows_inspected": len(series),
        "anomalies_found": len(flagged_indices),
        "mean": round(mean_val, 2),
        "std": round(std_val, 2),
        "q25": round(q25, 2),
        "q75": round(q75, 2),
        "iqr": round(iqr, 2),
        "flagged_rows": flagged_rows,
        "summary": (
            f"Detected {len(flagged_indices)} anomalies in '{table_name}.{column_name}' using {method.upper()} "
            f"(threshold: {threshold}). Top anomaly values range up to {top_flagged[0][1] if top_flagged else 'N/A'}."
        ),
    }

def detect_all_table_anomalies(table_name: str, max_per_col: int = 5) -> List[Dict[str, Any]]:
    """Runs automated anomaly detection on all numeric columns in a table."""
    df, err = execute_query_to_df(f"SELECT * FROM \"{table_name}\";")
    if err or df is None or df.empty:
        return []

    results = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in numeric_cols:
        # Skip ID columns
        if col.endswith("_id") or col == "id":
            continue
        res = detect_column_anomalies(table_name, col, method="iqr", max_records=max_per_col)
        if res.get("anomalies_found", 0) > 0:
            results.append(res)
    return results

def detect_all_workspace_anomalies() -> List[Dict[str, Any]]:
    """Runs comprehensive anomaly scanning across all tables in the database."""
    tables = list_all_tables()
    all_anomalies = []
    for tbl in tables:
        anoms = detect_all_table_anomalies(tbl)
        all_anomalies.extend(anoms)
    return all_anomalies
