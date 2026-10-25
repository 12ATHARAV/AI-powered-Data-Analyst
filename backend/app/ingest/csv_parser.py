import csv as _csv_module
import re
import os
import warnings
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
from ..db.engine import get_connection

def sanitize_identifier(name: str) -> str:
    """Sanitizes file and column names to be valid SQLite identifiers."""
    # Strip extension if present
    base = os.path.splitext(name)[0]
    # Replace non-alphanumeric characters with underscore
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", base.strip().lower())
    # Collapse multiple underscores
    clean = re.sub(r"_+", "_", clean).strip("_")
    # If starts with digit, prepend 't_' or 'col_'
    if clean and clean[0].isdigit():
        clean = f"t_{clean}"
    return clean or "unnamed_table"

def infer_and_convert_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Attempts to convert object columns with date-like patterns to ISO strings."""
    date_patterns = [
        r"^\d{4}-\d{2}-\d{2}$",
        r"^\d{4}/\d{2}/\d{2}$",
        r"^\d{2}/\d{2}/\d{4}$",
        r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}",
    ]
    for col in df.columns:
        if df[col].dtype == "object":
            sample = df[col].dropna().astype(str).head(20)
            if sample.empty:
                continue
            is_date_candidate = any(
                sample.str.match(pattern).all() for pattern in date_patterns
            ) or ("date" in col.lower() or "time" in col.lower())
            
            if is_date_candidate:
                try:
                    converted = pd.to_datetime(df[col], errors="coerce")
                    if converted.notnull().mean() > 0.8:
                        df[col] = converted.dt.strftime("%Y-%m-%d %H:%M:%S").replace("NaT", None)
                except Exception:
                    pass
    return df

def parse_and_load_csv(
    file_path: str,
    custom_table_name: str = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Parses a CSV file, sanitizes columns, types, loads into SQLite, and returns metadata.
    """
    file_p = Path(file_path)
    if not file_p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Determine table name
    raw_name = custom_table_name or file_p.stem
    table_name = sanitize_identifier(raw_name)

    # Robust read: utf-8 / latin-1, and for ragged files (rows with extra fields
    # or junk delimiters) fall back to delimiter-sniffing with bad-line skipping.
    structural_fixes: List[Dict[str, Any]] = []
    skipped_rows = {"count": 0}

    def _on_bad_line(cells: List[str]):
        skipped_rows["count"] += 1
        return None

    def _read_python_engine(encoding: str) -> pd.DataFrame:
        """Delimiter-sniffing read that drops malformed rows instead of truncating them."""
        return pd.read_csv(
            file_path, encoding=encoding, sep=None, engine="python",
            on_bad_lines=_on_bad_line, index_col=False,
        )

    def _load_ragged_safe(encoding: str) -> pd.DataFrame:
        """Quote-aware stdlib parse: keeps only rows whose field count matches
        the header, dropping malformed rows entirely. Works regardless of
        pandas version behavior for ragged rows."""
        with open(file_path, encoding=encoding, newline="") as fh:
            reader = _csv_module.reader(fh)
            try:
                header = next(reader)
            except StopIteration:
                return pd.DataFrame()
            kept: List[List[str]] = []
            dropped = 0
            for row in reader:
                if not row or (len(row) == 1 and str(row[0]).strip() == ""):
                    continue
                if len(row) != len(header):
                    dropped += 1
                    continue
                # Blank cells become None (-> NaN) so pandas/imputation treat them as missing
                kept.append([cell if str(cell).strip() != "" else None for cell in row])
        skipped_rows["count"] += dropped
        return pd.DataFrame(kept, columns=header)

    # Deterministic ragged-row detection: peek raw text with the quote-aware
    # stdlib csv reader and compare each row's field count to the header.
    # This is immune to pandas version differences (older ones raise, newer
    # ones silently truncate ragged rows and merely warn).
    def _peek_is_ragged(encoding: str) -> bool:
        with open(file_path, encoding=encoding, newline="") as fh:
            reader = _csv_module.reader(fh)
            try:
                header = next(reader)
            except StopIteration:
                return False
            for row in reader:
                if not row or (len(row) == 1 and str(row[0]).strip() == ""):
                    continue
                if len(row) != len(header):
                    return True
        return False

    ragged = False
    enc_used = None
    for enc in ("utf-8", "latin-1"):
        try:
            ragged = _peek_is_ragged(enc)
            enc_used = enc
            break
        except UnicodeDecodeError:
            continue
    if enc_used is None:
        raise ValueError(f"Could not read '{file_p.name}': unrecognized file encoding.")

    if ragged:
        try:
            df = _load_ragged_safe(enc_used)
        except Exception:
            df = _read_python_engine(enc_used)
    else:
        try:
            df = pd.read_csv(file_path, encoding=enc_used, index_col=False)
        except (pd.errors.ParserError, ValueError):
            df = _read_python_engine(enc_used)
        except UnicodeDecodeError:
            for alt_enc in ("latin-1",):
                try:
                    df = _load_ragged_safe(alt_enc)
                    break
                except Exception:
                    continue
            if df is None:
                raise ValueError(f"Could not parse '{file_p.name}': not a readable CSV file.")

    if skipped_rows["count"] > 0:
        structural_fixes.append({
            "column": "(file)",
            "action": "Ragged Row Removal",
            "original": f"{skipped_rows['count']} malformed rows",
            "new": "dropped",
            "reason": f"Removed {skipped_rows['count']} rows whose field count did not match the header so the dataset parses cleanly.",
        })

    # Sanitize column names and de-duplicate any repeated headers.
    # Without this, a CSV with two identical headers makes df[col] return a
    # DataFrame instead of a Series, crashing every downstream .dtype call.
    used_names: Dict[str, int] = {}
    new_columns: List[str] = []
    for col in df.columns:
        base = sanitize_identifier(str(col))
        if base in used_names:
            used_names[base] += 1
            new_name = f"{base}_{used_names[base]}"
            structural_fixes.append({
                "column": str(col),
                "action": "Duplicate Header Renamed",
                "original": str(col),
                "new": new_name,
                "reason": f"Duplicate column header '{str(col)}' was renamed to '{new_name}' so every column name stays unique.",
            })
        else:
            used_names[base] = 1
            new_name = base
        new_columns.append(new_name)
    df.columns = new_columns

    # Strip corrupted byte markers (mojibake) embedded in text cells.
    # Covers both the U+FFFD replacement char and legacy byte-pair artifacts
    # (U+00FF 'ÿ', U+00BF '¿', U+00BD '½') that trail corrupted strings.
    junk_tail = re.compile(r"[?\ufffd\u00ff\u00bf\u00bd]+$")
    junk_chars = ("\ufffd", "\u00ff", "\u00bf", "\u00bd")
    for col in df.select_dtypes(include=["object", "string"]).columns:
        def _has_junk(x) -> bool:
            return isinstance(x, str) and any(c in x for c in junk_chars)
        mask = df[col].apply(_has_junk)
        junk_count = int(mask.sum())
        if junk_count > 0:
            df.loc[mask, col] = (
                df.loc[mask, col]
                .str.replace("\ufffd", "", regex=False)
                .str.replace(junk_tail, "", regex=True)
            )
            structural_fixes.append({
                "column": str(col),
                "action": "Mojibake Cleanup",
                "original": "corrupted replacement-character bytes",
                "new": "removed",
                "reason": f"Removed corrupted byte markers from {junk_count} text cells in '{col}'.",
            })

    # Coerce text columns whose values are mostly numeric into real numbers,
    # so aggregates (SUM/AVG) work for the SQL agent. Handles "$", commas,
    # surrounding whitespace, wrapper quote characters ("475" style) and
    # percent suffixes; unparseable cells become nulls (imputed later).
    for col in df.select_dtypes(include=["object", "string"]).columns:
        series = df[col].dropna()
        if series.empty:
            continue
        stripped = (
            series.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.strip()
            .str.strip("'\"")
            .str.rstrip("%")
            .str.strip()
        )
        if pd.to_numeric(stripped.head(50), errors="coerce").notnull().mean() < 0.8:
            continue
        numeric = pd.to_numeric(stripped, errors="coerce")
        junk_count = int(series.notnull().sum() - numeric.notnull().sum())
        df[col] = numeric.reindex(df.index)
        structural_fixes.append({
            "column": str(col),
            "action": "Numeric Type Coercion",
            "original": "text",
            "new": "numeric",
            "reason": (
                f"Column '{col}' held numeric values as text — coerced to numbers"
                + (f" ({junk_count} unparseable cells set to null for imputation)." if junk_count else ".")
            ),
        })

    # Infer dates
    df = infer_and_convert_dates(df)

    # Automated Data Cleaning, Deduplication & Casing Harmonization
    from .cleaner import clean_and_remediate_dataframe
    df, cleaning_audit = clean_and_remediate_dataframe(df, table_name, structural_fixes)

    # Ingest into SQLite
    with get_connection(readonly=False) as conn:
        df.to_sql(name=table_name, con=conn, if_exists="replace", index=False)
        
        # Create indexes on likely foreign keys / IDs
        cursor = conn.cursor()
        for col in df.columns:
            if col.endswith("_id") or col == "id":
                try:
                    idx_name = f"idx_{table_name}_{col}"
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON \"{table_name}\" (\"{col}\");")
                except Exception:
                    pass
        conn.commit()

    meta = {
        "table_name": table_name,
        "original_file": file_p.name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [
            {"name": col, "type": str(df[col].dtype), "null_count": int(df[col].isnull().sum())}
            for col in df.columns
        ],
        "cleaning_audit": cleaning_audit,
    }
    return table_name, meta
