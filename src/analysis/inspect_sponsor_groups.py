"""
inspect_sponsor_groups.py
-------------------------
Step 5 of the Political Ad Disclosure Analysis Pipeline.

Loads the fuzzy-grouped Google ads dataset and produces two inspection files:

  1. sponsor_group_summary.csv   -- full picture of every group
  2. sponsor_groups_to_review.csv -- only groups where multiple distinct
     cleaned names were merged together (i.e., the groups most likely to
     contain accidental matches that need human review)

Why this matters:
  Fuzzy matching can accidentally group unrelated sponsors that happen to
  share common words ("friends of", "for congress", etc.).  Before trusting
  any downstream analysis, a human needs to look at the merged groups and
  decide whether the matches make sense.

Usage:
    Standalone:
        python src/analysis/inspect_sponsor_groups.py

    Imported:
        from src.analysis.inspect_sponsor_groups import inspect_sponsor_groups
        summary_df, review_df = inspect_sponsor_groups()
"""

import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
INPUT_PATH   = Path("data/processed/google_ads_grouped.csv")
SUMMARY_PATH = Path("data/processed/sponsor_group_summary.csv")
REVIEW_PATH  = Path("data/processed/sponsor_groups_to_review.csv")


def inspect_sponsor_groups() -> tuple[pd.DataFrame, pd.DataFrame] | tuple[None, None]:
    """
    Load the grouped ads dataset, compute per-group statistics, and save
    two CSVs for manual review.

    Returns:
        (summary_df, review_df) on success, or (None, None) if input missing.
    """

    # ------------------------------------------------------------------
    # Check input exists
    # ------------------------------------------------------------------
    if not INPUT_PATH.exists():
        print("\n[inspect_groups] ERROR: Input file not found.")
        print(f"  Expected: {INPUT_PATH.resolve()}")
        print("  Run group_similar_sponsors() first (Step 4).")
        return None, None

    # ------------------------------------------------------------------
    # Load the grouped dataset
    # ------------------------------------------------------------------
    print("\n[inspect_groups] Loading grouped Google ads data...")
    df = pd.read_csv(INPUT_PATH)
    print(f"  Loaded {len(df):,} rows, {df.shape[1]} columns.")

    # Verify required columns are present
    required_cols = {"sponsor_group_id", "canonical_sponsor_name",
                     "clean_sponsor_name", "sponsor_name"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"[inspect_groups] ERROR: Missing columns: {missing}")
        return None, None

    # ------------------------------------------------------------------
    # Filter out the catch-all group -1 (rows with no clean sponsor name)
    # Those are not meaningful to group-level analysis.
    # ------------------------------------------------------------------
    valid_df = df[df["sponsor_group_id"] >= 0].copy()
    print(f"  Rows with valid group assignment: {len(valid_df):,}")
    print(f"  Rows with no group (id=-1):       {(df['sponsor_group_id'] == -1).sum():,}")

    # ------------------------------------------------------------------
    # Build the per-group summary
    #
    # For each group we compute:
    #   - canonical_sponsor_name  (the chosen label for this group)
    #   - num_ads                 (total rows belonging to this group)
    #   - num_unique_clean_names  (how many distinct cleaned names were merged)
    #   - unique_clean_names      (pipe-separated list of those names)
    #   - unique_raw_names        (pipe-separated list of raw original names)
    # ------------------------------------------------------------------
    print("[inspect_groups] Computing per-group statistics...")

    summary_df = (
        valid_df
        .groupby(["sponsor_group_id", "canonical_sponsor_name"])
        .agg(
            num_ads                = ("sponsor_group_id", "count"),
            num_unique_clean_names = ("clean_sponsor_name", "nunique"),
            unique_clean_names     = ("clean_sponsor_name",
                                      lambda x: " | ".join(sorted(x.dropna().unique()))),
            unique_raw_names       = ("sponsor_name",
                                      lambda x: " | ".join(sorted(x.dropna().unique()))),
        )
        .reset_index()
        # Sort: groups with most ads first for easy scanning
        .sort_values("num_ads", ascending=False)
    )

    # ------------------------------------------------------------------
    # Save the full summary
    # ------------------------------------------------------------------
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(SUMMARY_PATH, index=False)
    print(f"  Full group summary saved -> {SUMMARY_PATH.resolve()}")

    # ------------------------------------------------------------------
    # Build the review file
    # Only include groups where num_unique_clean_names > 1.
    # These are the groups where the fuzzy matcher merged 2+ different
    # cleaned names — the ones that most need a human to verify.
    # Sort by: most names merged first, then by ad count descending.
    # ------------------------------------------------------------------
    review_df = (
        summary_df[summary_df["num_unique_clean_names"] > 1]
        .sort_values(["num_unique_clean_names", "num_ads"], ascending=[False, False])
        .reset_index(drop=True)
    )

    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    review_df.to_csv(REVIEW_PATH, index=False)
    print(f"  Review file saved          -> {REVIEW_PATH.resolve()}")

    # ------------------------------------------------------------------
    # Print terminal summary
    # ------------------------------------------------------------------
    total_groups  = summary_df["sponsor_group_id"].nunique()
    review_groups = len(review_df)

    print("\n" + "-" * 60)
    print("  SPONSOR GROUP INSPECTION SUMMARY")
    print("-" * 60)
    print(f"  Total sponsor groups                : {total_groups:,}")
    print(f"  Groups with 1 cleaned name (clean)  : {total_groups - review_groups:,}")
    print(f"  Groups with 2+ cleaned names (review): {review_groups:,}")
    print("-" * 60)

    # Print the top 20 groups to review so the user can spot-check
    # directly in the terminal without opening the CSV.
    if review_groups > 0:
        print(f"\n  Top {min(20, review_groups)} groups to review "
              f"(sorted by merged-name count, then ad count):\n")
        print(f"  {'Group ID':>8}  {'# Ads':>6}  {'# Names':>7}  "
              f"{'Canonical Name':<35}  Merged Cleaned Names")
        print("  " + "-" * 110)

        for _, row in review_df.head(20).iterrows():
            canonical  = str(row["canonical_sponsor_name"])[:34]
            merged     = str(row["unique_clean_names"])[:60]
            print(f"  {int(row['sponsor_group_id']):>8}  "
                  f"{int(row['num_ads']):>6}  "
                  f"{int(row['num_unique_clean_names']):>7}  "
                  f"{canonical:<35}  {merged}")
    else:
        print("\n  No multi-name groups found — all groups look clean!")

    print()
    return summary_df, review_df


# ---------------------------------------------------------------------------
# Allow direct execution: python src/analysis/inspect_sponsor_groups.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    summary, review = inspect_sponsor_groups()
    if summary is not None:
        print(f"Done.")
        print(f"  sponsor_group_summary.csv   : {len(summary):,} groups")
        print(f"  sponsor_groups_to_review.csv: {len(review):,} groups need review")
