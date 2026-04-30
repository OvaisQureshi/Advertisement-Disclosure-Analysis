"""
run_meta_pipeline.py
--------------------
Step 8B of the Political Ad Disclosure Analysis Pipeline.

Runs the full preprocessing and analysis pipeline on the Meta dataset.
All outputs use the meta_ prefix so Google outputs are never overwritten.

Pipeline:
    meta_ads_standardized.csv
        -> meta_ads_cleaned.csv       (clean_sponsors)
        -> meta_ads_grouped.csv       (group_sponsors)
        -> meta_dataset_summary.json  (dataset_summary)
        -> meta_top_sponsors.csv      (dataset_summary)

Usage:
    Standalone:
        python src/data_collection/run_meta_pipeline.py

    Imported:
        from src.data_collection.run_meta_pipeline import run_meta_pipeline
        run_meta_pipeline()
"""

import pandas as pd
import re
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS — all use meta_ prefix to avoid overwriting Google outputs
# ---------------------------------------------------------------------------
INPUT_PATH      = Path("data/processed/meta_ads_standardized.csv")
CLEANED_PATH    = Path("data/processed/meta_ads_cleaned.csv")
GROUPED_PATH    = Path("data/processed/meta_ads_grouped.csv")
SUMMARY_PATH    = Path("data/processed/meta_dataset_summary.json")
TOP_SPONS_PATH  = Path("data/processed/meta_top_sponsors.csv")

# ---------------------------------------------------------------------------
# LEGAL SUFFIXES to strip from sponsor names (same list as Google pipeline)
# ---------------------------------------------------------------------------
LEGAL_SUFFIXES = r"\b(inc|llc|corp|pac|committee|ltd|co|association|fund|org)\b"


# ===========================================================================
# Step 8B-1: Clean sponsor names  (mirrors clean_sponsors.py logic)
# ===========================================================================

def _clean_name(name: str) -> str:
    """Normalize a single sponsor name string."""
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = re.sub(r"[^a-z0-9\s]", " ", name)        # strip punctuation
    name = re.sub(LEGAL_SUFFIXES, " ", name)          # remove legal suffixes
    name = re.sub(r"\s+", " ", name).strip()          # collapse whitespace
    return name


def _clean_meta_sponsors(df: pd.DataFrame) -> pd.DataFrame:
    """Add clean_sponsor_name column to the Meta DataFrame."""
    print("\n[meta_clean] Cleaning Meta sponsor names...")
    df = df.copy()
    df["clean_sponsor_name"] = df["sponsor_name"].apply(_clean_name)

    unique_raw   = df["sponsor_name"].nunique()
    unique_clean = df["clean_sponsor_name"].nunique()
    print(f"  Unique raw names   : {unique_raw:,}")
    print(f"  Unique clean names : {unique_clean:,}")

    df.to_csv(CLEANED_PATH, index=False)
    print(f"  Saved -> {CLEANED_PATH.resolve()}")
    return df


# ===========================================================================
# Step 8B-2: Fuzzy group sponsors  (mirrors group_sponsors.py logic)
# ===========================================================================

def _group_meta_sponsors(df: pd.DataFrame, threshold: int = 90) -> pd.DataFrame:
    """
    Fuzzy-group Meta sponsor names using rapidfuzz token_sort_ratio.
    Identical algorithm to the Google pipeline.
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        print("[meta_group] rapidfuzz not installed — skipping fuzzy grouping.")
        df["sponsor_group_id"]      = -1
        df["canonical_sponsor_name"] = df["sponsor_name"]
        return df

    print(f"\n[meta_group] Fuzzy grouping Meta sponsors (threshold={threshold})...")

    # Union-Find helpers
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent.get(x, x), x)
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Get unique non-empty cleaned names.
    # Meta Page names are already canonical (official FB page names), so
    # fuzzy grouping adds less value than for Google but is still useful
    # for catching minor variations. Cap at 3,000 to stay fast.
    MAX_NAMES = 3_000
    all_names = [n for n in df["clean_sponsor_name"].unique() if n]
    if len(all_names) > MAX_NAMES:
        import random
        random.seed(42)
        # Prioritise the most frequent names so top sponsors are grouped correctly
        top_names = (df[df["clean_sponsor_name"] != ""]
                     .groupby("clean_sponsor_name").size()
                     .sort_values(ascending=False)
                     .head(MAX_NAMES).index.tolist())
        names = top_names
        print(f"  Unique names (total)    : {len(all_names):,}  -> capped at {MAX_NAMES:,} most frequent")
    else:
        names = all_names
    n           = len(names)
    total_pairs = n * (n - 1) // 2
    print(f"  Names being compared    : {n:,}")
    print(f"  Total pairwise comparisons: {total_pairs:,}")

    merges     = 0
    pairs_done = 0
    start_time = time.time()

    def _progress(done: int, total: int) -> None:
        """Print an in-place ASCII progress bar with ETA."""
        pct    = done / total if total else 1
        filled = int(40 * pct)
        bar    = "#" * filled + "-" * (40 - filled)
        elapsed = time.time() - start_time
        eta     = (elapsed / pct - elapsed) if pct > 0 else 0
        eta_str = f"{int(eta // 60)}m {int(eta % 60)}s" if eta > 60 else f"{int(eta)}s"
        sys.stdout.write(
            f"\r  [{bar}] {pct*100:5.1f}%  "
            f"{done:,} / {total:,} pairs  ETA {eta_str}   "
        )
        sys.stdout.flush()

    UPDATE_EVERY = max(1, total_pairs // 200)   # update bar ~200 times total

    for i in range(n):
        for j in range(i + 1, n):
            score = fuzz.token_sort_ratio(names[i], names[j])
            if score >= threshold:
                union(names[i], names[j])
                merges += 1
            pairs_done += 1
            if pairs_done % UPDATE_EVERY == 0:
                _progress(pairs_done, total_pairs)

    _progress(total_pairs, total_pairs)   # final 100%
    print()                               # newline after bar
    elapsed_total = time.time() - start_time
    print(f"  Finished in {int(elapsed_total // 60)}m {int(elapsed_total % 60)}s")
    print(f"  Pairs merged : {merges:,}")


    # Assign group IDs
    roots   = {name: find(name) for name in names}
    root_ids = {root: idx for idx, root in enumerate(sorted(set(roots.values())))}

    df = df.copy()
    df["sponsor_group_id"] = df["clean_sponsor_name"].apply(
        lambda n: root_ids.get(find(n), -1) if n else -1
    )

    # Canonical name = most frequent raw name per group
    freq = (df[df["sponsor_group_id"] >= 0]
            .groupby(["sponsor_group_id", "sponsor_name"])
            .size()
            .reset_index(name="cnt"))
    canonical = (freq.sort_values("cnt", ascending=False)
                 .drop_duplicates("sponsor_group_id")
                 .set_index("sponsor_group_id")["sponsor_name"])
    df["canonical_sponsor_name"] = df["sponsor_group_id"].map(canonical)

    groups = df["sponsor_group_id"].nunique()
    print(f"  Sponsor groups formed : {groups:,}")

    df.to_csv(GROUPED_PATH, index=False)
    print(f"  Saved -> {GROUPED_PATH.resolve()}")
    return df


# ===========================================================================
# Step 8B-3: Dataset summary
# ===========================================================================

def _meta_dataset_summary(df: pd.DataFrame) -> dict:
    """Compute and save dataset summary statistics for Meta data."""
    import json

    print("\n[meta_summary] Computing Meta dataset summary...")

    spend_lower = pd.to_numeric(df["spend_lower"], errors="coerce")
    spend_upper = pd.to_numeric(df["spend_upper"], errors="coerce")

    summary = {
        "platform": "Meta",
        "total_ads":              int(len(df)),
        "unique_raw_sponsors":    int(df["sponsor_name"].nunique()),
        "unique_clean_sponsors":  int(df["clean_sponsor_name"].nunique()),
        "unique_sponsor_groups":  int(df[df["sponsor_group_id"] >= 0]["sponsor_group_id"].nunique()),
        "spend_summary": {
            "mean_spend_lower": round(float(spend_lower.mean()), 2) if spend_lower.notna().any() else None,
            "mean_spend_upper": round(float(spend_upper.mean()), 2) if spend_upper.notna().any() else None,
            "max_spend_upper":  round(float(spend_upper.max()),  2) if spend_upper.notna().any() else None,
        },
    }

    # Date range
    for col in ("start_date", "end_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    if df["start_date"].notna().any():
        summary["earliest_start_date"] = str(df["start_date"].min().date())
    if df["end_date"].notna().any():
        summary["latest_end_date"] = str(df["end_date"].max().date())

    # Save JSON
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary saved -> {SUMMARY_PATH.resolve()}")

    # Top sponsors by SPEND (more meaningful than ad count for page-level Meta data)
    spend_lower = pd.to_numeric(df["spend_lower"], errors="coerce")
    df = df.copy()
    df["_avg_spend"] = spend_lower

    top = (df[df["sponsor_group_id"] >= 0]
           .groupby("canonical_sponsor_name")
           .agg(ad_count=("sponsor_group_id", "count"),
                total_spend=("_avg_spend", "sum"))
           .reset_index()
           .sort_values("total_spend", ascending=False)
           .head(20))
    top.to_csv(TOP_SPONS_PATH, index=False)
    print(f"  Top sponsors   -> {TOP_SPONS_PATH.resolve()}")

    print(f"\n  === META DATASET SUMMARY ===")
    print(f"  Total ads            : {summary['total_ads']:,}")
    print(f"  Unique raw sponsors  : {summary['unique_raw_sponsors']:,}")
    print(f"  Unique sponsor groups: {summary['unique_sponsor_groups']:,}")
    if summary.get("earliest_start_date"):
        print(f"  Date range           : {summary['earliest_start_date']} to {summary.get('latest_end_date','?')}")
    print(f"  Top 10 sponsors by total spend:")
    for _, row in top.head(10).iterrows():
        name = str(row["canonical_sponsor_name"])[:50]
        print(f"    ${int(row['total_spend']):>12,}   {name}")


    return summary


# ===========================================================================
# MAIN
# ===========================================================================

def run_meta_pipeline() -> bool:
    """
    Run the full Meta preprocessing pipeline.
    Input:  data/processed/meta_ads_standardized.csv
    Returns True on success.
    """
    if not INPUT_PATH.exists():
        print(f"\n[meta_pipeline] ERROR: {INPUT_PATH} not found.")
        print("  Run Step 8A first: python src/data_collection/load_meta_ads.py")
        return False

    print("\n[meta_pipeline] Loading standardized Meta data...")
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f"  Rows: {len(df):,}  |  Columns: {list(df.columns)}")

    df = _clean_meta_sponsors(df)
    df = _group_meta_sponsors(df)
    _meta_dataset_summary(df)

    print("\n[meta_pipeline] Meta pipeline complete.")
    print(f"  Cleaned  -> {CLEANED_PATH}")
    print(f"  Grouped  -> {GROUPED_PATH}")
    print(f"  Summary  -> {SUMMARY_PATH}")
    print(f"  Top Spons-> {TOP_SPONS_PATH}\n")
    return True


if __name__ == "__main__":
    ok = run_meta_pipeline()
    if ok:
        print("Done. Now run Step 8C: python src/analysis/compare_platforms.py")
