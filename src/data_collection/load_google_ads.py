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

# Sample output: first N rows kept for fast local debugging.
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

    1. Checks that the raw Google CSV exists; prints instructions if not.
    2. Reads the raw file in small chunks to avoid out-of-memory errors.
    3. Stops reading as soon as SAMPLE_ROWS rows have been collected.
    4. Prints an inspection summary (columns + first 5 rows).
    5. Saves the sample to data/raw/google_ads_sample.csv.
    6. Builds a standardized DataFrame using COLUMN_MAP.
    7. Saves the standardized output to data/processed/google_ads_standardized.csv.

    Returns:
        Standardized pandas DataFrame on success, or None if the raw file is
        missing.
    """

    # ------------------------------------------------------------------
    # STEP 1 — Check that the raw file exists
    # ------------------------------------------------------------------
    if not os.path.exists(RAW_FILE_PATH):
        print("\n" + "=" * 60)
        print("  [load_google_ads] Raw file NOT found.")
        print("=" * 60)
        print(f"\n  Expected location : {os.path.abspath(RAW_FILE_PATH)}")
        print(f"  Expected filename : google_political_ads_raw.csv")
        print()
        print("  This script expects a locally downloaded copy of the")
        print("  Google Political Advertising Transparency Report.")
        print()
        print("  How to get it:")
        print("  1. Go to: https://transparencyreport.google.com/political-ads/home")
        print("  2. Download the ZIP for your region (e.g. US).")
        print("  3. Unzip and find the CSV file (e.g. google-political-ads-")
        print("     creative-stats.csv or similar).")
        print("  4. Rename it to:  google_political_ads_raw.csv")
        print(f"  5. Place it in:   {os.path.abspath(os.path.join('data', 'raw'))}")
        print("  6. Re-run this script.\n")
        return None

    # ------------------------------------------------------------------
    # STEP 2 — Read the CSV in chunks to avoid loading the whole file
    #
    # Google's political ads file can be hundreds of MB.  Instead of
    # reading everything into RAM at once (which caused the OOM crash),
    # we stream it 5,000 rows at a time and stop as soon as we have
    # collected SAMPLE_ROWS rows.  This keeps memory usage tiny.
    # ------------------------------------------------------------------
    print("\n[load_google_ads] Loading raw file (chunked — large file safe)...")
    print(f"  Path: {os.path.abspath(RAW_FILE_PATH)}")
    print(f"  Will read at most {SAMPLE_ROWS:,} rows then stop.")

    CHUNK_SIZE = 5_000          # rows per chunk — tune down if still tight on RAM
    collected_chunks: list[pd.DataFrame] = []
    rows_collected = 0

    try:
        # pd.read_csv with chunksize returns an iterator; we never load
        # the whole file into memory.
        chunk_iter = pd.read_csv(
            RAW_FILE_PATH,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            on_bad_lines="skip",   # skip any malformed rows instead of crashing
        )

        for chunk in chunk_iter:
            rows_needed = SAMPLE_ROWS - rows_collected
            collected_chunks.append(chunk.iloc[:rows_needed])
            rows_collected += min(len(chunk), rows_needed)
            if rows_collected >= SAMPLE_ROWS:
                break   # we have enough — stop reading

    except Exception as exc:
        print(f"\n[load_google_ads] ERROR reading file: {exc}")
        print("  Try opening the file in a text editor to check it is a valid CSV.")
        return None

    if not collected_chunks:
        print("[load_google_ads] No data could be read from the file.")
        return None

    # Combine all collected chunks into one working DataFrame
    raw_df = pd.concat(collected_chunks, ignore_index=True)

    # ------------------------------------------------------------------
    # STEP 3 — Inspect and print a summary of the loaded sample
    # ------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("  RAW DATA INSPECTION  (first chunk sample)")
    print("-" * 60)
    print(f"  Rows loaded : {raw_df.shape[0]:,}  (capped at {SAMPLE_ROWS:,})")
    print(f"  Columns     : {raw_df.shape[1]:,}")
    print(f"\n  Column names ({raw_df.shape[1]} total):")
    for i, col in enumerate(raw_df.columns, start=1):
        print(f"    {i:>3}. {col}")
    print("\n  First 5 rows:")
    print(raw_df.head(5).to_string(index=False))
    print("-" * 60)

    # ------------------------------------------------------------------
    # STEP 4 — Save the sample CSV
    #   raw_df already contains at most SAMPLE_ROWS rows, so we can save
    #   it directly as the sample without any further slicing.
    # ------------------------------------------------------------------
    os.makedirs(os.path.dirname(SAMPLE_FILE_PATH), exist_ok=True)
    raw_df.to_csv(SAMPLE_FILE_PATH, index=False)
    print(f"\n[load_google_ads] Saved {len(raw_df):,}-row sample to:")
    print(f"  {os.path.abspath(SAMPLE_FILE_PATH)}")

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
