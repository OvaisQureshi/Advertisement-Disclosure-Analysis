"""
clean_sponsors.py
-----------------
Step 3 of the Political Ad Disclosure Analysis Pipeline.

Loads the standardized Google ads data and creates a cleaned version of the
sponsor name column (clean_sponsor_name).  The goal is to normalize advertiser
names so that slight variations ("Jane Smith Inc.", "JANE SMITH, INC") collapse
into the same token for grouping and comparison later.

Cleaning strategy:
  - Lowercase everything.
  - Strip punctuation (replaced with spaces so words do not accidentally join).
  - Remove common legal-suffix / noise words ONLY when they appear as whole,
    standalone words (not substrings inside a real name).
  - Collapse redundant whitespace.

Intentionally NOT done here:
  - Fuzzy / similarity-based deduplication (planned for the next step).
  - Dropping records with missing sponsor names.

Usage:
    Standalone:
        python src/preprocessing/clean_sponsors.py

    Imported into main.py:
        from src.preprocessing.clean_sponsors import clean_google_sponsors
        df = clean_google_sponsors()
"""

import re
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
INPUT_PATH  = Path("data/processed/google_ads_standardized.csv")
OUTPUT_PATH = Path("data/processed/google_ads_cleaned.csv")


# ---------------------------------------------------------------------------
# NOISE WORDS
# These are legal/organizational suffix terms that carry no analytical value.
# They are matched only as WHOLE WORDS (using word-boundary regex) so that
# a name like "Corporate Reform PAC" does not lose "Corp-" mid-word.
# ---------------------------------------------------------------------------
_NOISE_WORDS = {
    "inc",
    "llc",
    "ltd",
    "co",
    "corp",
    "corporation",
    "committee",
    "pac",
}

# Build a single compiled regex that matches any noise word as a whole token.
# \b ensures we only match at word boundaries (i.e. "co" won't eat "company").
_NOISE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _NOISE_WORDS) + r")\b"
)


# ---------------------------------------------------------------------------
# CORE CLEANING FUNCTION
# ---------------------------------------------------------------------------

def clean_sponsor_name(name) -> str:
    """
    Return a normalized version of a raw sponsor/advertiser name.

    Step-by-step transformations:
        1. Return empty string for null / missing values.
        2. Cast to string (handles any numeric IDs that slipped through).
        3. Lowercase.
        4. Replace every punctuation character with a space (prevents
           "Smith,Inc" from becoming "smithinc" after stripping commas).
        5. Collapse multiple consecutive spaces into one.
        6. Strip leading/trailing whitespace.
        7. Remove noise/suffix words as whole words only.
        8. Final whitespace collapse and strip after noise removal.

    Args:
        name: Raw sponsor name value (str, float NaN, or None accepted).

    Returns:
        Cleaned name string, or empty string if input was null/empty.
    """

    # Step 1 — handle missing values
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""

    # Step 2 — force to string (e.g. if a numeric ID ended up in this column)
    name = str(name)

    # Step 3 — lowercase
    name = name.lower()

    # Step 4 — replace any non-alphanumeric character with a space.
    # Using a character class that keeps letters, digits, and spaces.
    name = re.sub(r"[^a-z0-9\s]", " ", name)

    # Step 5 & 6 — collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()

    # Step 7 — remove noise words (legal suffixes, pac, committee …)
    # The compiled pattern matches only whole words.
    name = _NOISE_PATTERN.sub(" ", name)

    # Step 8 — final collapse after possible gaps left by noise removal
    name = re.sub(r"\s+", " ", name).strip()

    return name


# ---------------------------------------------------------------------------
# PIPELINE FUNCTION
# ---------------------------------------------------------------------------

def clean_google_sponsors() -> pd.DataFrame | None:
    """
    Load the standardized Google ads CSV, apply sponsor name cleaning, and
    save the result with an additional clean_sponsor_name column.

    Returns:
        Cleaned DataFrame on success, or None if the input file is missing.
    """

    # ------------------------------------------------------------------
    # Check that the standardized input exists
    # ------------------------------------------------------------------
    if not INPUT_PATH.exists():
        print("\n[clean_sponsors] ERROR: Input file not found.")
        print(f"  Expected: {INPUT_PATH.resolve()}")
        print("  Run load_and_standardize_google_ads() first to create it.")
        return None

    # ------------------------------------------------------------------
    # Load the standardized CSV
    # ------------------------------------------------------------------
    print("\n[clean_sponsors] Loading standardized Google ads data...")
    df = pd.read_csv(INPUT_PATH)
    print(f"  Loaded {len(df):,} rows, {df.shape[1]} columns.")

    # ------------------------------------------------------------------
    # Verify the required sponsor_name column is present
    # ------------------------------------------------------------------
    if "sponsor_name" not in df.columns:
        print("[clean_sponsors] ERROR: 'sponsor_name' column not found.")
        print(f"  Columns present: {list(df.columns)}")
        return None

    # ------------------------------------------------------------------
    # Apply the cleaning function row-by-row to create clean_sponsor_name
    # ------------------------------------------------------------------
    print("[clean_sponsors] Cleaning sponsor names...")
    df["clean_sponsor_name"] = df["sponsor_name"].apply(clean_sponsor_name)

    # ------------------------------------------------------------------
    # Summary statistics
    # ------------------------------------------------------------------
    total_rows          = len(df)
    unique_raw          = df["sponsor_name"].nunique()
    unique_clean        = df["clean_sponsor_name"].nunique()
    missing_clean       = (df["clean_sponsor_name"] == "").sum()

    print("\n" + "-" * 55)
    print("  SPONSOR CLEANING SUMMARY")
    print("-" * 55)
    print(f"  Total rows                   : {total_rows:,}")
    print(f"  Unique raw sponsor names     : {unique_raw:,}")
    print(f"  Unique cleaned sponsor names : {unique_clean:,}")
    print(f"  Rows with empty cleaned name : {missing_clean:,}")
    print("-" * 55)

    # ------------------------------------------------------------------
    # Print first 20 before/after examples so the user can spot-check
    # the cleaning logic visually.
    # ------------------------------------------------------------------
    print("\n  First 20 sponsor name cleaning examples:")
    print(f"  {'Raw sponsor_name':<45}  ->  clean_sponsor_name")
    print("  " + "-" * 75)

    sample = df[["sponsor_name", "clean_sponsor_name"]].drop_duplicates().head(20)
    for _, row in sample.iterrows():
        raw   = str(row["sponsor_name"])[:44]   # truncate long names for display
        clean = str(row["clean_sponsor_name"])
        print(f"  {raw:<45}  ->  {clean}")

    print()

    # ------------------------------------------------------------------
    # Save the cleaned output
    # ------------------------------------------------------------------
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"[clean_sponsors] Saved {len(df):,} rows to:")
    print(f"  {OUTPUT_PATH.resolve()}\n")

    return df


# ---------------------------------------------------------------------------
# Allow running directly: python src/preprocessing/clean_sponsors.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = clean_google_sponsors()
    if result is not None:
        print(f"Done. {len(result):,} rows with cleaned sponsor names saved.")
