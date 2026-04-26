"""
load_google_ads.py
------------------
Step 2 of the Political Ad Disclosure Analysis Pipeline.

Loads a locally downloaded Google Political Advertising Transparency Report CSV,
inspects the raw columns, creates a manageable sample, then produces a
standardized output with consistent column names for downstream processing.

Usage:
    As a standalone script:
        python src/data_collection/load_google_ads.py

    Imported into main.py:
        from src.data_collection.load_google_ads import load_and_standardize_google_ads
        result = load_and_standardize_google_ads()
"""

import os
import pandas as pd

# ---------------------------------------------------------------------------
# PATHS
# Raw input file the user must download and place here manually.
RAW_FILE_PATH = os.path.join("data", "raw", "google_political_ads_raw.csv")

# Random sample created by sample_google_ads_random.py (preferred input).
# If this file exists, standardization reads from it instead of the raw CSV.
RANDOM_SAMPLE_PATH = os.path.join("data", "raw", "google_ads_sample_random.csv")

# Legacy sequential sample path (kept for reference / fallback).
SAMPLE_FILE_PATH = os.path.join("data", "raw", "google_ads_sample.csv")
SAMPLE_ROWS = 10_000

# Final standardized output used by the rest of the pipeline.
STANDARDIZED_FILE_PATH = os.path.join("data", "processed", "google_ads_standardized.csv")
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# COLUMN MAPPING DICTIONARY
#
# Keys   = the target column names we want in our standardized output.
# Values = possible raw Google CSV column names that could match (in priority
#          order).  If none of the candidates are found in the raw file the
#          column will be filled with None rather than crashing.
#
# Update the candidate lists here if Google changes their export format.
# ---------------------------------------------------------------------------
COLUMN_MAP: dict[str, list[str]] = {
    "ad_id":              ["Ad_ID", "ad_id", "AdID", "id"],
    "sponsor_name":       ["Advertiser_Name", "advertiser_name", "AdvertiserName",
                           "Sponsor", "sponsor_name"],
    "ad_text":            ["Ad_Title", "ad_title", "AdTitle",
                           "Description", "description", "ad_text"],
    "start_date":         ["Ad_Delivery_Start_Time", "Start_Date", "start_date",
                           "Date_Range_Start"],
    "end_date":           ["Ad_Delivery_Stop_Time",  "Stop_Date",  "end_date",
                           "Date_Range_End"],
    "spend_lower":        ["Lower_Bound_of_Cost_USD", "Spend_Lower", "spend_lower",
                           "lower_spend", "spend_range_min_usd"],
    "spend_upper":        ["Upper_Bound_of_Cost_USD", "Spend_Upper", "spend_upper",
                           "upper_spend", "spend_range_max_usd"],
    "impressions_lower":  ["Lower_Bound_of_Impressions", "Impressions_Lower",
                           "impressions_lower", "lower_impressions",
                           "impressions_min"],
    "impressions_upper":  ["Upper_Bound_of_Impressions", "Impressions_Upper",
                           "impressions_upper", "upper_impressions",
                           "impressions_max"],
}


def _resolve_column(raw_columns: list[str], candidates: list[str]) -> str | None:
    """
    Find the first candidate column name that actually exists in the raw CSV.

    Args:
        raw_columns: List of column names present in the loaded DataFrame.
        candidates:  Ordered list of possible names to look for.

    Returns:
        The first matching column name, or None if none match.
    """
    # Build a lowercase lookup for case-insensitive matching
    lower_map = {col.lower(): col for col in raw_columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return None


def load_and_standardize_google_ads() -> pd.DataFrame | None:
    """
    Main entry point for Step 2.

    Priority logic for input:
      1. If data/raw/google_ads_sample_random.csv exists (created by
         sample_google_ads_random.py), read from it directly.  This is
         preferred because it is a statistically representative random sample.
      2. Otherwise fall back to chunked sequential reading of the raw CSV
         (original behaviour — biased toward first N rows, kept as a fallback).

    Then:
      - Prints an inspection summary (columns + first 5 rows).
      - Builds a standardized DataFrame using COLUMN_MAP.
      - Saves to data/processed/google_ads_standardized.csv.

    Returns:
        Standardized pandas DataFrame on success, or None if neither input
        file is available.
    """

    # ------------------------------------------------------------------
    # STEP 1 — Decide which input file to use
    #
    # Preferred: google_ads_sample_random.csv (random sample — representative)
    # Fallback:  chunked sequential read of the raw 2.5GB file
    # ------------------------------------------------------------------
    if os.path.exists(RANDOM_SAMPLE_PATH):
        # Random sample already created by sample_google_ads_random.py
        print("\n[load_google_ads] Random sample file found — using it for standardization.")
        print(f"  Path: {os.path.abspath(RANDOM_SAMPLE_PATH)}")
        try:
            raw_df = pd.read_csv(RANDOM_SAMPLE_PATH, low_memory=False)
        except Exception as exc:
            print(f"[load_google_ads] ERROR reading random sample: {exc}")
            return None
        sample_source = RANDOM_SAMPLE_PATH

    elif os.path.exists(RAW_FILE_PATH):
        # No random sample yet — fall back to sequential chunked reading
        print("\n[load_google_ads] No random sample found. Falling back to sequential")
        print("  chunked reading of raw file (first 10,000 rows — biased).")
        print(f"  Tip: run sample_google_ads_random.py first for better results.")
        print(f"  Path: {os.path.abspath(RAW_FILE_PATH)}")

        CHUNK_SIZE = 5_000
        collected_chunks: list[pd.DataFrame] = []
        rows_collected = 0

        try:
            chunk_iter = pd.read_csv(
                RAW_FILE_PATH,
                chunksize=CHUNK_SIZE,
                low_memory=False,
                on_bad_lines="skip",
            )
            for chunk in chunk_iter:
                rows_needed = SAMPLE_ROWS - rows_collected
                collected_chunks.append(chunk.iloc[:rows_needed])
                rows_collected += min(len(chunk), rows_needed)
                if rows_collected >= SAMPLE_ROWS:
                    break
        except Exception as exc:
            print(f"\n[load_google_ads] ERROR reading raw file: {exc}")
            return None

        if not collected_chunks:
            print("[load_google_ads] No data could be read.")
            return None

        raw_df = pd.concat(collected_chunks, ignore_index=True)
        # Save the sequential sample so the path is documented
        os.makedirs(os.path.dirname(SAMPLE_FILE_PATH), exist_ok=True)
        raw_df.to_csv(SAMPLE_FILE_PATH, index=False)
        sample_source = RAW_FILE_PATH

    else:
        # Neither file exists
        print("\n" + "=" * 60)
        print("  [load_google_ads] No input file found.")
        print("=" * 60)
        print(f"  Run sample_google_ads_random.py first, OR place the raw CSV at:")
        print(f"  {os.path.abspath(RAW_FILE_PATH)}\n")
        return None

    # ------------------------------------------------------------------
    # STEP 2 — Inspect and print a summary of the loaded data
    # ------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("  RAW DATA INSPECTION")
    print("-" * 60)
    print(f"  Rows loaded : {raw_df.shape[0]:,}")
    print(f"  Columns     : {raw_df.shape[1]:,}")
    print(f"\n  Column names ({raw_df.shape[1]} total):")
    for i, col in enumerate(raw_df.columns, start=1):
        print(f"    {i:>3}. {col}")
    print("\n  First 5 rows:")
    preview = raw_df.head(5).to_string(index=False)
    # Encode to ASCII replacing any non-ASCII characters (e.g. >= symbols in
    # impression range strings) so Windows cp1252 terminals don't crash.
    print(preview.encode("ascii", errors="replace").decode("ascii"))
    print("-" * 60)

    # ------------------------------------------------------------------
    # STEP 5 — Build the standardized DataFrame
    #
    # We iterate over COLUMN_MAP and try to find each target column in the
    # raw data.  If a match is found we copy that column; if not, we fill
    # the target column with None.  This way the script never crashes due
    # to a missing column, and the rest of the pipeline always sees the
    # same predictable schema.
    # ------------------------------------------------------------------
    print("\n[load_google_ads] Standardizing columns...")

    raw_columns = raw_df.columns.tolist()
    standardized: dict[str, pd.Series] = {}

    # Always tag every row with its source platform
    standardized["platform"] = "Google"

    for target_col, candidates in COLUMN_MAP.items():
        match = _resolve_column(raw_columns, candidates)
        if match:
            standardized[target_col] = raw_df[match].values
            print(f"  [OK] '{target_col}'  <-  raw column '{match}'")
        else:
            standardized[target_col] = None
            print(f"  [--] '{target_col}'  not found - filled with None")

    # Add a raw_source column so analysts know where the record came from
    standardized["raw_source"] = RAW_FILE_PATH

    # Assemble into a DataFrame (reset_index so index is 0-based after concat)
    std_df = pd.DataFrame(standardized)

    # ------------------------------------------------------------------
    # STEP 6 — Save the standardized output
    # ------------------------------------------------------------------
    os.makedirs(os.path.dirname(STANDARDIZED_FILE_PATH), exist_ok=True)
    std_df.to_csv(STANDARDIZED_FILE_PATH, index=False)

    print(f"\n[load_google_ads] Saved {len(std_df):,} standardized rows to:")
    print(f"  {os.path.abspath(STANDARDIZED_FILE_PATH)}")
    print(f"\n  Standardized columns: {list(std_df.columns)}\n")

    return std_df


# ---------------------------------------------------------------------------
# Allow running this file directly:  python src/data_collection/load_google_ads.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = load_and_standardize_google_ads()
    if result is not None:
        print(f"Done. {len(result):,} standardized Google ad records ready for analysis.")
