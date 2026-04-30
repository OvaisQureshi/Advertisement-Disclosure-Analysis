"""
load_meta_ads.py
----------------
Step 8A of the Political Ad Disclosure Analysis Pipeline.

Loads the combined Meta Ad Library CSV (data/raw/meta_ads_raw.csv) and
maps its columns to the standardized schema used by the Google pipeline.

ACTUAL Meta columns (from the US lifelong regional export):
    Page ID             -> ad_id
    Page name           -> sponsor_name
    Disclaimer          -> ad_text  (the "Paid for by" disclosure text)
    Amount spent (USD)  -> spend_lower AND spend_upper
                           (Meta reports a single value, not a range.
                            We set both lower and upper to the same number
                            so downstream scripts don't need special casing.)

NOTE: This export has NO date columns, impressions columns, or ad type.
      Those fields will be filled with None.
      This is an important transparency gap to highlight in the paper.

Output: data/processed/meta_ads_standardized.csv

Usage:
    Standalone:
        python src/data_collection/load_meta_ads.py

    Imported:
        from src.data_collection.load_meta_ads import load_and_standardize_meta_ads
        df = load_and_standardize_meta_ads()
"""

import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
RAW_FILE_PATH    = Path("data/raw/meta_ads_raw.csv")
OUTPUT_FILE_PATH = Path("data/processed/meta_ads_standardized.csv")

# ---------------------------------------------------------------------------
# COLUMN MAP
# Maps standardized column names -> ranked list of actual Meta column names.
# The first match found in the file wins (handles any future format changes).
# ---------------------------------------------------------------------------
COLUMN_MAP = {
    "ad_id": [
        "Page ID", "page_id", "Ad ID", "ad_id",
    ],
    "sponsor_name": [
        "Page name", "page_name", "Page Name", "Advertiser_Name",
        "advertiser_name", "Sponsor",
    ],
    "ad_text": [
        "Disclaimer", "disclaimer", "Ad Text", "ad_text",
        "Ad_Creative_Body", "Body",
    ],
    # Meta provides a single "Amount spent (USD)" — we use it for both bounds.
    "spend_lower": [
        "Amount spent (USD)", "amount_spent_usd", "Spend", "spend",
        "Spend_Lower_Bound", "spend_lower_bound",
    ],
    "spend_upper": [
        "Amount spent (USD)", "amount_spent_usd", "Spend", "spend",
        "Spend_Upper_Bound", "spend_upper_bound",
    ],
    # These fields do not exist in this Meta export — will be None.
    "start_date": [
        "Ad_Delivery_Start_Time", "start_date", "Start Date",
    ],
    "end_date": [
        "Ad_Delivery_Stop_Time", "end_date", "End Date",
    ],
    "impressions_lower": [
        "Impressions_Lower_Bound", "impressions_lower",
    ],
    "impressions_upper": [
        "Impressions_Upper_Bound", "impressions_upper",
    ],
}


def _find_column(raw_cols: list, candidates: list):
    """Return the first candidate that exists in raw_cols (case-insensitive)."""
    raw_lower = {c.lower(): c for c in raw_cols}
    for cand in candidates:
        if cand in raw_cols:
            return cand
        if cand.lower() in raw_lower:
            return raw_lower[cand.lower()]
    return None


def load_and_standardize_meta_ads() -> pd.DataFrame | None:
    """
    Load the combined Meta Ad Library CSV and produce the standardized
    schema used by all downstream pipeline steps.

    Because the Meta dataset has 11M+ rows (one row per page-region pair),
    we read it in chunks and sample down to a manageable size so the fuzzy
    grouping step doesn't take hours.

    Target sample size: 100,000 rows (random, reproducible).

    Returns:
        Standardized DataFrame on success, or None if the raw file is missing.
    """

    if not RAW_FILE_PATH.exists():
        print("\n[meta_load] ERROR: Combined Meta file not found.")
        print(f"  Expected: {RAW_FILE_PATH.resolve()}")
        print("  Run first: python src/data_collection/combine_meta_regions.py")
        return None

    print(f"\n[meta_load] Loading combined Meta data from:")
    print(f"  {RAW_FILE_PATH.resolve()}")

    # ------------------------------------------------------------------
    # SAMPLING STRATEGY — Top spenders, not random rows.
    #
    # Meta's transparency report is PAGE-LEVEL, not AD-LEVEL:
    #   1 row = 1 Facebook page × 1 US state (aggregate spend)
    #   A major advertiser like Biden for President appears ~57 times
    #   (once per state), regardless of total spend.
    #
    # Random sampling would surface thousands of tiny $0-$100 issue
    # advertisers while burying the major political campaigns.
    #
    # Instead: deduplicate by Page ID (summing spend across states),
    # then take the top 50,000 unique pages by total spend.
    # This is equivalent in intent to Google's volume-based sampling:
    # both capture the most politically active advertisers on each platform.
    # ------------------------------------------------------------------
    TARGET_ROWS  = 50_000
    CHUNK_SIZE   = 50_000

    print(f"  Strategy: top {TARGET_ROWS:,} unique pages by total political ad spend")
    print(f"  Reading {RAW_FILE_PATH.stat().st_size / 1e9:.2f} GB file in chunks...")

    frames     = []
    total_seen = 0
    chunk_num  = 0

    try:
        chunk_iter = pd.read_csv(
            RAW_FILE_PATH,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding="utf-8",
            on_bad_lines="skip",
        )
        for chunk in chunk_iter:
            frames.append(chunk)
            total_seen += len(chunk)
            chunk_num  += 1
            if chunk_num % 50 == 0:
                print(f"  ... {total_seen:,} rows read")

    except Exception as exc:
        print(f"[meta_load] ERROR reading file: {exc}")
        return None

    print(f"\n  Total rows read : {total_seen:,}")
    full_df = pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------
    # Parse spend as numeric so we can sort by it
    # ------------------------------------------------------------------
    spend_col = "Amount spent (USD)"
    if spend_col in full_df.columns:
        full_df[spend_col] = (
            full_df[spend_col]
            .astype(str)
            .str.replace(r"[$,]", "", regex=True)
            .pipe(pd.to_numeric, errors="coerce")
            .fillna(0)
        )

    # ------------------------------------------------------------------
    # Deduplicate: one row per unique Page ID, sum spend across states
    # ------------------------------------------------------------------
    if "Page ID" in full_df.columns and spend_col in full_df.columns:
        # Keep first occurrence of text columns, sum spend
        agg = {spend_col: "sum"}
        for col in full_df.columns:
            if col not in ("Page ID", spend_col):
                agg[col] = "first"
        deduped = full_df.groupby("Page ID", as_index=False).agg(agg)
        print(f"  Unique pages (nationwide): {len(deduped):,}")

        # Take top N by total spend
        raw_df = (deduped.sort_values(spend_col, ascending=False)
                  .head(TARGET_ROWS)
                  .reset_index(drop=True))
        print(f"  Selected top {len(raw_df):,} pages by spend")
        print(f"  Spend range: ${int(raw_df[spend_col].min()):,} – ${int(raw_df[spend_col].max()):,}")
    else:
        # Fallback: just take first TARGET_ROWS rows
        raw_df = full_df.head(TARGET_ROWS)
        print(f"  Fallback: took first {len(raw_df):,} rows")

    raw_cols = list(raw_df.columns)
    print(f"\n  Columns in Meta file:")
    for col in raw_cols:
        null_pct = raw_df[col].isna().mean() * 100
        print(f"    '{col}'  ({null_pct:.0f}% null)")

    # ------------------------------------------------------------------
    # Build standardized DataFrame
    # ------------------------------------------------------------------
    print("\n  Column mapping:")
    std_data   = {}
    col_report = {}

    for std_col, candidates in COLUMN_MAP.items():
        found = _find_column(raw_cols, candidates)
        col_report[std_col] = found or "NOT FOUND -> None"
        std_data[std_col]   = raw_df[found].copy() if found else None

    for std_col, source in col_report.items():
        print(f"    {std_col:<22} <- {source}")

    # Parse spend as numeric (remove $ signs or commas if present)
    for spend_col in ("spend_lower", "spend_upper"):
        if std_data.get(spend_col) is not None:
            std_data[spend_col] = (
                std_data[spend_col]
                .astype(str)
                .str.replace(r"[$,]", "", regex=True)
                .pipe(pd.to_numeric, errors="coerce")
            )

    std_df = pd.DataFrame(std_data)
    std_df.insert(0, "platform",   "Meta")
    std_df["raw_source"] = str(RAW_FILE_PATH)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    OUTPUT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    std_df.to_csv(OUTPUT_FILE_PATH, index=False)

    print(f"\n[meta_load] Done.")
    print(f"  Rows standardized : {len(std_df):,}")
    print(f"  Columns           : {list(std_df.columns)}")
    print(f"  Saved to          : {OUTPUT_FILE_PATH.resolve()}\n")

    return std_df


if __name__ == "__main__":
    result = load_and_standardize_meta_ads()
    if result is not None:
        print(f"Done. {len(result):,} Meta ads standardized.")
        print("Next: python src/data_collection/run_meta_pipeline.py")
