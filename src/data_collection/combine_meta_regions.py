"""
combine_meta_regions.py
-----------------------
Step 8A.1 of the Political Ad Disclosure Analysis Pipeline.

The Meta Ad Library exports one CSV per region/state.
This script combines all of them into a single unified file.

Input folder:   data/raw/meta_regions/    (place all region CSVs here)
Output file:    data/raw/meta_ads_raw.csv

Usage:
    python src/data_collection/combine_meta_regions.py
"""

import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
INPUT_FOLDER = Path("data/raw/meta_regions")
OUTPUT_FILE  = Path("data/raw/meta_ads_raw.csv")


def combine_meta_regions() -> pd.DataFrame | None:
    """
    Find every CSV inside data/raw/meta_regions/, load and combine them
    into a single DataFrame, then save to data/raw/meta_ads_raw.csv.

    Skips empty or corrupted files gracefully.

    Returns:
        Combined DataFrame on success, or None if no files were found.
    """

    # ------------------------------------------------------------------
    # Confirm the input folder exists
    # ------------------------------------------------------------------
    if not INPUT_FOLDER.exists():
        print(f"\n[combine_meta] ERROR: Input folder not found.")
        print(f"  Expected: {INPUT_FOLDER.resolve()}")
        print()
        print("  How to fix:")
        print("  1. Create the folder:  data/raw/meta_regions/")
        print("  2. Copy all region CSVs from your Meta download into it.")
        print("  3. Re-run this script.")
        return None

    # ------------------------------------------------------------------
    # Find all CSV files in the folder (non-recursive)
    # ------------------------------------------------------------------
    csv_files = sorted(INPUT_FOLDER.glob("*.csv"))

    if not csv_files:
        print(f"\n[combine_meta] ERROR: No CSV files found in {INPUT_FOLDER.resolve()}")
        print("  Make sure you copied the region CSV files into that folder.")
        return None

    print(f"\n[combine_meta] Found {len(csv_files)} CSV file(s) in {INPUT_FOLDER.resolve()}")

    # ------------------------------------------------------------------
    # Load each CSV, tagging it with its source filename for traceability
    # ------------------------------------------------------------------
    frames = []
    files_ok      = 0
    files_skipped = 0

    for csv_path in csv_files:
        try:
            # Try UTF-8 first; fall back to latin-1 for Windows-encoded exports
            try:
                df = pd.read_csv(csv_path, low_memory=False, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, low_memory=False, encoding="latin-1")

            if df.empty:
                print(f"  [skip] {csv_path.name}  (empty file)")
                files_skipped += 1
                continue

            # Tag each row with its source region file name
            df["_source_file"] = csv_path.name

            frames.append(df)
            files_ok += 1
            print(f"  [ok]   {csv_path.name}  ({len(df):,} rows)")

        except Exception as exc:
            print(f"  [skip] {csv_path.name}  (error: {exc})")
            files_skipped += 1

    if not frames:
        print("\n[combine_meta] No valid CSV files could be loaded.")
        return None

    # ------------------------------------------------------------------
    # Concatenate all frames into one unified DataFrame
    # Missing columns from one file are filled with NaN automatically.
    # ------------------------------------------------------------------
    print(f"\n[combine_meta] Combining {files_ok} file(s)...")
    combined = pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------
    # Remove exact duplicate rows (same ad appearing in multiple regions)
    # ------------------------------------------------------------------
    before = len(combined)
    combined = combined.drop_duplicates()
    after  = len(combined)
    if before != after:
        print(f"  Removed {before - after:,} duplicate rows across regions.")

    # ------------------------------------------------------------------
    # Print summary
    # ------------------------------------------------------------------
    print(f"\n  Files processed : {files_ok}")
    print(f"  Files skipped   : {files_skipped}")
    print(f"  Total rows      : {len(combined):,}")
    print(f"  Columns ({combined.shape[1]}):")
    for col in combined.columns:
        null_pct = combined[col].isna().mean() * 100
        print(f"    - {col}  ({null_pct:.0f}% null)")

    # ------------------------------------------------------------------
    # Save to output file
    # ------------------------------------------------------------------
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[combine_meta] Saved combined file -> {OUTPUT_FILE.resolve()}")

    return combined


# ---------------------------------------------------------------------------
# Allow direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = combine_meta_regions()
    if result is not None:
        print(f"\nDone. {len(result):,} combined Meta rows ready.")
        print(f"Next step: python src/data_collection/load_meta_ads.py")
