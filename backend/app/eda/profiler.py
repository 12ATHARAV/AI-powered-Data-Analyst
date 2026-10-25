from typing import Dict, Any, List
import numpy as np
import pandas as pd
from ..db.engine import execute_query_to_df, list_all_tables

def generate_table_eda_profile(table_name: str) -> Dict[str, Any]:
    """
    Performs full automated Exploratory Data Analysis (EDA) on a table:
    1. Univariate analysis (numeric distribution + categorical frequencies)
    2. Correlation matrix (numeric variables)
    3. Temporal range analysis (for date columns)
    """
    df, err = execute_query_to_df(f"SELECT * FROM \"{table_name}\";")
    if err or df is None or df.empty:
        return {"error": err or "Table is empty"}

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]

    # 1. Numeric Univariate Statistics
    numeric_stats: List[Dict[str, Any]] = []
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        q25 = float(series.quantile(0.25))
        q75 = float(series.quantile(0.75))
        iqr = float(q75 - q25)
        skew = float(series.skew()) if len(series) > 2 else 0.0

        numeric_stats.append({
            "column": col,
            "count": int(series.count()),
            "mean": round(float(series.mean()), 2),
            "std": round(float(series.std()), 2) if len(series) > 1 else 0.0,
            "min": round(float(series.min()), 2),
            "p25": round(q25, 2),
            "median": round(float(series.median()), 2),
            "p75": round(q75, 2),
            "max": round(float(series.max()), 2),
            "iqr": round(iqr, 2),
            "skewness": round(skew, 2),
            "distribution_shape": "symmetric" if abs(skew) < 0.5 else ("right_skewed" if skew > 0.5 else "left_skewed"),
        })

    # 2. Categorical Univariate Frequencies
    categorical_stats: List[Dict[str, Any]] = []
    for col in categorical_cols:
        if col in date_cols:
            continue
        series = df[col].dropna().astype(str)
        if len(series) == 0:
            continue
        val_counts = series.value_counts()
        total_non_null = len(series)
        top_values = [
            {"value": str(val), "count": int(count), "percentage": round(count / total_non_null * 100, 1)}
            for val, count in val_counts.head(5).items()
        ]
        categorical_stats.append({
            "column": col,
            "unique_count": int(series.nunique()),
            "cardinality": "high" if series.nunique() > 50 else ("medium" if series.nunique() > 10 else "low"),
            "top_values": top_values,
        })

    # 3. Date Span Analysis
    date_stats: List[Dict[str, Any]] = []
    for col in date_cols:
        try:
            converted = pd.to_datetime(df[col], errors="coerce").dropna()
            if not converted.empty:
                min_d = converted.min()
                max_d = converted.max()
                span_days = int((max_d - min_d).days)
                date_stats.append({
                    "column": col,
                    "earliest_date": str(min_d.date()),
                    "latest_date": str(max_d.date()),
                    "span_days": span_days,
                })
        except Exception:
            pass

    # 4. Correlation Matrix
    correlations: Dict[str, Any] = {}
    strong_correlations: List[Dict[str, Any]] = []
    if len(numeric_cols) >= 2:
        corr_df = df[numeric_cols].corr().fillna(0).round(3)
        correlations = corr_df.to_dict()
        
        # Identify strong pairs
        cols = corr_df.columns
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                r = corr_df.iloc[i, j]
                if abs(r) >= 0.5:
                    strong_correlations.append({
                        "var1": cols[i],
                        "var2": cols[j],
                        "correlation": float(r),
                        "direction": "positive" if r > 0 else "negative",
                        "strength": "strong" if abs(r) >= 0.7 else "moderate",
                    })

    return {
        "table_name": table_name,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "numeric_stats": numeric_stats,
        "categorical_stats": categorical_stats,
        "date_stats": date_stats,
        "correlations": correlations,
        "strong_correlations": strong_correlations,
    }

def get_complete_eda_summary_text() -> str:
    """Returns a textual EDA brief of all tables for prompt context."""
    tables = list_all_tables()
    if not tables:
        return "No tables available."

    lines = ["Comprehensive Multi-Table EDA Overview:"]
    for tbl in tables:
        eda = generate_table_eda_profile(tbl)
        if "error" in eda:
            continue
        lines.append(f"\n--- Table '{tbl}' ({eda['total_rows']} rows) ---")
        if eda["numeric_stats"]:
            stats_str = ", ".join([f"{s['column']}: [mean={s['mean']}, median={s['median']}, min={s['min']}, max={s['max']}]" for s in eda["numeric_stats"][:5]])
            lines.append(f"  Key Numeric Stats: {stats_str}")
        if eda["strong_correlations"]:
            corr_str = ", ".join([f"{c['var1']} ~ {c['var2']} (r={c['correlation']})" for c in eda["strong_correlations"][:3]])
            lines.append(f"  Strong Correlations: {corr_str}")
        if eda["date_stats"]:
            d_str = ", ".join([f"{d['column']} from {d['earliest_date']} to {d['latest_date']}" for d in eda["date_stats"]])
            lines.append(f"  Timeline: {d_str}")

    return "\n".join(lines)
