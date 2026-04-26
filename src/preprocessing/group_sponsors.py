"""
group_sponsors.py
-----------------
Step 4 of the Political Ad Disclosure Analysis Pipeline.

Uses fuzzy string similarity to group cleaned sponsor names that are likely
the same advertiser written slightly differently (e.g. "jane smith for
congress" and "friends of jane smith" would NOT group, but "jane smith pac"
and "jane smith political action" would if they score above the threshold).

Algorithm:
  1. Collect every unique non-empty clean_sponsor_name.
  2. Compare every pair using rapidfuzz token_sort_ratio, which is
     insensitive to word-order differences.
  3. Pairs scoring >= SIMILARITY_THRESHOLD are flagged as belonging to
     the same group via a Union-Find data structure.
  4. Each group gets a numeric sponsor_group_id.
  5. The canonical_sponsor_name for a group is the *raw* sponsor_name that
     appears most frequently in that group — giving a human-readable label.

Why token_sort_ratio?
  It sorts the tokens alphabetically before comparing, so
  "john smith for senate" and "for senate john smith" score 100.
  This handles PAC naming conventions like "Friends of X" vs "X for Office".

Why Union-Find?
  Fuzzy similarity is not transitive (A~B, B~C does not guarantee A~C).
  Union-Find lets us group transitively without manually checking all triples.

Usage:
    Standalone:
        python src/preprocessing/group_sponsors.py

    Imported:
        from src.preprocessing.group_sponsors import group_similar_sponsors
        df = group_similar_sponsors()
"""

import pandas as pd
from pathlib import Path
from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
INPUT_PATH  = Path("data/processed/google_ads_cleaned.csv")
OUTPUT_PATH = Path("data/processed/google_ads_grouped.csv")

# ---------------------------------------------------------------------------
# CONFIGURATION
# Raise threshold -> fewer, tighter groups (fewer false positives).
# Lower threshold -> more groups merged (more false positives).
# 85 is a reasonable starting point for political sponsor names.
# ---------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 90   # score out of 100


# ---------------------------------------------------------------------------
# UNION-FIND (Disjoint Set Union)
# A lightweight data structure that efficiently tracks which items belong
# to the same group and merges groups in near-constant time.
# ---------------------------------------------------------------------------

class UnionFind:
    """Simple Union-Find / Disjoint Set Union for grouping strings."""

    def __init__(self, items: list):
        # Each item starts as its own parent (its own group)
        self.parent = {item: item for item in items}

    def find(self, x):
        """Return the root representative of x's group (with path compression)."""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])   # path compression
        return self.parent[x]

    def union(self, x, y):
        """Merge the groups containing x and y."""
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[ry] = rx   # attach y's root under x's root


# ---------------------------------------------------------------------------
# CORE GROUPING FUNCTION
# ---------------------------------------------------------------------------

def group_similar_sponsors() -> pd.DataFrame | None:
    """
    Load google_ads_cleaned.csv, group similar sponsor names, and save
    google_ads_grouped.csv with two new columns:
        sponsor_group_id      -- integer group identifier
        canonical_sponsor_name -- most-frequent raw name within the group

    Returns:
        Grouped DataFrame, or None if the input file is missing.
    """

    # ------------------------------------------------------------------
    # Check input exists
    # ------------------------------------------------------------------
    if not INPUT_PATH.exists():
        print("\n[group_sponsors] ERROR: Input file not found.")
        print(f"  Expected: {INPUT_PATH.resolve()}")
        print("  Run clean_google_sponsors() first (Step 3).")
        return None

    # ------------------------------------------------------------------
    # Load cleaned data
    # ------------------------------------------------------------------
    print("\n[group_sponsors] Loading cleaned Google ads data...")
    df = pd.read_csv(INPUT_PATH)
    print(f"  Loaded {len(df):,} rows.")

    if "clean_sponsor_name" not in df.columns:
        print("[group_sponsors] ERROR: 'clean_sponsor_name' column missing.")
        return None

    # ------------------------------------------------------------------
    # Collect unique non-empty cleaned sponsor names to compare
    # ------------------------------------------------------------------
    unique_names = [
        name for name in df["clean_sponsor_name"].dropna().unique()
        if str(name).strip() != ""
    ]
    n = len(unique_names)
    print(f"  Unique non-empty cleaned names to compare: {n:,}")
    total_pairs = n * (n - 1) // 2
    print(f"  Total pairwise comparisons: {total_pairs:,}")

    # ------------------------------------------------------------------
    # Build Union-Find and run fuzzy comparisons
    # Every pair with token_sort_ratio >= threshold gets merged into
    # the same group.
    # ------------------------------------------------------------------
    print(f"  Running fuzzy comparisons (threshold={SIMILARITY_THRESHOLD})...")
    uf = UnionFind(unique_names)

    merges = 0
    for i in range(n):
        for j in range(i + 1, n):
            score = fuzz.token_sort_ratio(unique_names[i], unique_names[j])
            if score >= SIMILARITY_THRESHOLD:
                uf.union(unique_names[i], unique_names[j])
                merges += 1

    print(f"  Pairs merged into same group: {merges:,}")

    # ------------------------------------------------------------------
    # Assign integer group IDs  (root -> group_id mapping)
    # ------------------------------------------------------------------
    # Find each name's root, then map unique roots to sequential integers
    root_to_id: dict[str, int] = {}
    name_to_group: dict[str, int] = {}
    next_id = 0

    for name in unique_names:
        root = uf.find(name)
        if root not in root_to_id:
            root_to_id[root] = next_id
            next_id += 1
        name_to_group[name] = root_to_id[root]

    total_groups = len(root_to_id)
    print(f"  Total sponsor groups formed: {total_groups:,}")

    # ------------------------------------------------------------------
    # Map group IDs back on to every row in the DataFrame
    # Rows with empty clean_sponsor_name get group_id = -1
    # ------------------------------------------------------------------
    df["sponsor_group_id"] = df["clean_sponsor_name"].map(
        lambda x: name_to_group.get(str(x).strip(), -1)
        if pd.notna(x) and str(x).strip() != ""
        else -1
    )

    # ------------------------------------------------------------------
    # Determine canonical_sponsor_name for each group
    # Strategy: use the most-frequent RAW sponsor_name within the group.
    # This gives a readable, real-world label rather than the cleaned token.
    # ------------------------------------------------------------------
    print("  Determining canonical sponsor names...")

    # Count occurrences of each raw sponsor_name per group
    freq = (
        df[df["sponsor_group_id"] >= 0]
        .groupby(["sponsor_group_id", "sponsor_name"])
        .size()
        .reset_index(name="count")
    )

    # For each group, pick the raw name with the highest count
    canonical_map = (
        freq.sort_values("count", ascending=False)
        .drop_duplicates(subset="sponsor_group_id")
        .set_index("sponsor_group_id")["sponsor_name"]
        .to_dict()
    )

    df["canonical_sponsor_name"] = df["sponsor_group_id"].map(canonical_map)

    # ------------------------------------------------------------------
    # Save output
    # ------------------------------------------------------------------
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    multi_name_groups = (
        df.groupby("sponsor_group_id")["clean_sponsor_name"].nunique()
        > 1
    ).sum()

    print("\n" + "-" * 55)
    print("  SPONSOR GROUPING SUMMARY")
    print("-" * 55)
    print(f"  Total rows processed          : {len(df):,}")
    print(f"  Unique cleaned names compared : {n:,}")
    print(f"  Total groups formed           : {total_groups:,}")
    print(f"  Groups with 2+ merged names   : {multi_name_groups:,}")
    print(f"  Similarity threshold used     : {SIMILARITY_THRESHOLD}")
    print(f"  Algorithm                     : token_sort_ratio (rapidfuzz)")
    print("-" * 55)
    print(f"\n[group_sponsors] Saved {len(df):,} rows to:")
    print(f"  {OUTPUT_PATH.resolve()}\n")

    return df


# ---------------------------------------------------------------------------
# Allow direct execution: python src/preprocessing/group_sponsors.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = group_similar_sponsors()
    if result is not None:
        print(f"Done. {len(result):,} rows with sponsor group assignments saved.")
