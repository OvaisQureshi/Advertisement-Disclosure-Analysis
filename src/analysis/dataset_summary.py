"""
dataset_summary.py
------------------
Step 6 of the Political Ad Disclosure Analysis Pipeline.

Loads the fully grouped Google ads dataset and computes high-level statistics
that describe what the dataset actually looks like.  The output of this step
feeds directly into the paper tables, presentation slides, and charts.

Computes:
  - Basic counts (total ads, unique sponsors at each normalization level)
  - Top sponsors by ad volume
  - Spend distribution (mean, min, max of lower/upper bounds)
  - Date range (earliest start, latest end)

Outputs:
  data/processed/dataset_summary.json   -- machine-readable stats dictionary
  data/processed/top_sponsors.csv       -- top 20 sponsor groups by ad count

Usage:
    Standalone:
        python src/analysis/dataset_summary.py

    Imported:
        from src.analysis.dataset_summary import generate_dataset_summary
        summary = generate_dataset_summary()
"""

import json
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
INPUT_PATH   = Path("data/processed/google_ads_grouped.csv")
SUMMARY_PATH = Path("data/processed/dataset_summary.json")
TOP_SPONSORS_PATH = Path("data/processed/top_sponsors.csv")


def generate_dataset_summary() -> dict | None:
    """
    Load the grouped Google ads dataset and compute summary statistics.

    Returns:
        Dictionary of summary stats on success, or None if input is missing.
    """

    # ------------------------------------------------------------------
    # Check that the grouped file exists (created by Step 4)
    # ------------------------------------------------------------------
    if not INPUT_PATH.exists():
        print("\n[dataset_summary] ERROR: Input file not found.")
        print(f"  Expected: {INPUT_PATH.resolve()}")
        print("  Run group_similar_sponsors() first (Step 4).")
        return None

    # ------------------------------------------------------------------
    # Load the grouped dataset
    # ------------------------------------------------------------------
    print("\n[dataset_summary] Loading grouped Google ads data...")
    df = pd.read_csv(INPUT_PATH)
    print(f"  Loaded {len(df):,} rows, {df.shape[1]} columns.")

    # ---------------------------------------------------------------------------
    # SECTION 1: BASIC COUNTS
    # How many ads are in the dataset, and how many distinct sponsors at each
    # level of normalization (raw -> cleaned -> grouped)?
    # ---------------------------------------------------------------------------
    total_ads            = len(df)
    unique_raw_sponsors  = df["sponsor_name"].nunique()
    unique_clean_sponsors = df["clean_sponsor_name"].nunique()

    # Exclude the catch-all group -1 (rows with no usable sponsor name)
    unique_sponsor_groups = df[df["sponsor_group_id"] >= 0]["sponsor_group_id"].nunique()

    print("\n" + "=" * 55)
    print("  BASIC COUNTS")
    print("=" * 55)
    print(f"  Total ads                  : {total_ads:,}")
    print(f"  Unique raw sponsor names   : {unique_raw_sponsors:,}")
    print(f"  Unique cleaned sponsors    : {unique_clean_sponsors:,}")
    print(f"  Unique sponsor groups      : {unique_sponsor_groups:,}")

    # ---------------------------------------------------------------------------
    # SECTION 2: TOP SPONSORS BY AD COUNT
    # Group by sponsor_group_id + canonical_sponsor_name and count ads.
    # This tells us which political advertisers ran the most ads in the dataset.
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 55)
    print("  TOP SPONSORS BY AD COUNT")
    print("=" * 55)

    # Only include rows with a valid group assignment
    valid_df = df[df["sponsor_group_id"] >= 0].copy()

    top_sponsors = (
        valid_df
        .groupby(["sponsor_group_id", "canonical_sponsor_name"])
        .agg(num_ads=("sponsor_group_id", "count"))
        .reset_index()
        .sort_values("num_ads", ascending=False)
        .reset_index(drop=True)
    )

    # Add a readable rank column (1-indexed)
    top_sponsors.insert(0, "rank", top_sponsors.index + 1)

    # Print top 10 in the terminal
    print(f"\n  {'Rank':<6} {'Ads':>6}  Sponsor")
    print("  " + "-" * 55)
    for _, row in top_sponsors.head(10).iterrows():
        print(f"  {int(row['rank']):<6} {int(row['num_ads']):>6}  {row['canonical_sponsor_name']}")

    # Save top 20 to CSV
    OUTPUT_PATH_SPONSORS = TOP_SPONSORS_PATH
    OUTPUT_PATH_SPONSORS.parent.mkdir(parents=True, exist_ok=True)
    top_sponsors.head(20).to_csv(OUTPUT_PATH_SPONSORS, index=False)
    print(f"\n  Top 20 saved -> {OUTPUT_PATH_SPONSORS.resolve()}")

    # ---------------------------------------------------------------------------
    # SECTION 3: SPEND ANALYSIS
    # The dataset provides spend as a range (lower bound, upper bound) in USD.
    # We summarize both bounds to understand the distribution of ad spending.
    # Null values are ignored safely via pandas skipna behavior.
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 55)
    print("  SPEND ANALYSIS (USD)")
    print("=" * 55)

    # Convert spend columns to numeric — coerce any non-numeric strings to NaN
    spend_lower = pd.to_numeric(df["spend_lower"], errors="coerce")
    spend_upper = pd.to_numeric(df["spend_upper"], errors="coerce")

    spend_summary = {
        "mean_spend_lower" : round(float(spend_lower.mean(skipna=True)), 2) if spend_lower.notna().any() else None,
        "mean_spend_upper" : round(float(spend_upper.mean(skipna=True)), 2) if spend_upper.notna().any() else None,
        "min_spend_lower"  : float(spend_lower.min(skipna=True))            if spend_lower.notna().any() else None,
        "max_spend_lower"  : float(spend_lower.max(skipna=True))            if spend_lower.notna().any() else None,
        "min_spend_upper"  : float(spend_upper.min(skipna=True))            if spend_upper.notna().any() else None,
        "max_spend_upper"  : float(spend_upper.max(skipna=True))            if spend_upper.notna().any() else None,
        "null_spend_lower" : int(spend_lower.isna().sum()),
        "null_spend_upper" : int(spend_upper.isna().sum()),
    }

    print(f"  Mean spend lower bound  : ${spend_summary['mean_spend_lower']:,.2f}"
          if spend_summary['mean_spend_lower'] is not None else "  Mean spend lower bound  : N/A")
    print(f"  Mean spend upper bound  : ${spend_summary['mean_spend_upper']:,.2f}"
          if spend_summary['mean_spend_upper'] is not None else "  Mean spend upper bound  : N/A")
    print(f"  Min  spend lower bound  : ${spend_summary['min_spend_lower']:,.2f}"
          if spend_summary['min_spend_lower'] is not None else "  Min spend lower         : N/A")
    print(f"  Max  spend lower bound  : ${spend_summary['max_spend_lower']:,.2f}"
          if spend_summary['max_spend_lower'] is not None else "  Max spend lower         : N/A")
    print(f"  Max  spend upper bound  : ${spend_summary['max_spend_upper']:,.2f}"
          if spend_summary['max_spend_upper'] is not None else "  Max spend upper         : N/A")
    print(f"  Rows missing spend_lower: {spend_summary['null_spend_lower']:,}")
    print(f"  Rows missing spend_upper: {spend_summary['null_spend_upper']:,}")

    # ---------------------------------------------------------------------------
    # SECTION 4: DATE RANGE ANALYSIS
    # Convert start_date and end_date to datetime objects and find the overall
    # date range covered by the dataset.
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 55)
    print("  DATE RANGE")
    print("=" * 55)

    # Use errors="coerce" so unparseable dates become NaT instead of crashing
    start_dates = pd.to_datetime(df["start_date"], errors="coerce")
    end_dates   = pd.to_datetime(df["end_date"],   errors="coerce")

    earliest_start = start_dates.min()
    latest_end     = end_dates.max()

    earliest_str = earliest_start.strftime("%Y-%m-%d") if pd.notna(earliest_start) else "N/A"
    latest_str   = latest_end.strftime("%Y-%m-%d")     if pd.notna(latest_end)     else "N/A"

    date_range = {
        "earliest_start_date": earliest_str,
        "latest_end_date":     latest_str,
        "null_start_dates":    int(start_dates.isna().sum()),
        "null_end_dates":      int(end_dates.isna().sum()),
    }

    print(f"  Earliest ad start date  : {earliest_str}")
    print(f"  Latest   ad end date    : {latest_str}")
    print(f"  Rows missing start_date : {date_range['null_start_dates']:,}")
    print(f"  Rows missing end_date   : {date_range['null_end_dates']:,}")

    # ---------------------------------------------------------------------------
    # SECTION 5: ASSEMBLE AND SAVE SUMMARY DICTIONARY AS JSON
    # This machine-readable file can be loaded by visualization scripts or
    # referenced directly when writing up results.
    # ---------------------------------------------------------------------------
    summary = {
        "total_ads":             total_ads,
        "unique_raw_sponsors":   unique_raw_sponsors,
        "unique_clean_sponsors": unique_clean_sponsors,
        "unique_sponsor_groups": unique_sponsor_groups,
        "spend_summary":         spend_summary,
        "date_range":            date_range,
    }

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[dataset_summary] Summary JSON saved -> {SUMMARY_PATH.resolve()}")
    print(f"[dataset_summary] Top sponsors CSV   -> {TOP_SPONSORS_PATH.resolve()}\n")

    return summary


# ---------------------------------------------------------------------------
# Allow direct execution: python src/analysis/dataset_summary.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = generate_dataset_summary()
    if result is not None:
        print("Done. Summary statistics generated successfully.")
