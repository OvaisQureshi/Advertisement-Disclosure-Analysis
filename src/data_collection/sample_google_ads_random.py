"""
sample_google_ads_random.py
---------------------------
Step 1.5 of the Political Ad Disclosure Analysis Pipeline.

TRUE RANDOM SAMPLING across the full dataset.

Strategy:
  - Read the ENTIRE raw 2.5GB CSV in chunks of 5,000 rows (no early stop).
  - From each chunk, keep a small random fraction (SAMPLE_FRAC = 0.3%) using
    random_state=42 for reproducibility.
  - Accumulate all sampled rows across every chunk in the file.
  - After reading 100% of the file, randomly downsample to exactly
    TARGET_ROWS (10,000) using the same fixed seed.

Why 0.3% per chunk instead of 20%?
  The file has approximately 5 million rows.
  20% x 5M = 1,000,000 rows accumulated in RAM -> potential OOM crash.
  0.3% x 5M =    15,000 rows accumulated in RAM -> ~10MB, perfectly safe.
  We then downsample those 15,000 to exactly 10,000 for the final output.

Why this is a TRUE random sample:
  Every row in the entire file has an equal probability of being selected.
  The final 10,000 rows are drawn uniformly from the full dataset, not
  just from the first N rows.  This is the gold-standard approach.

Reproducibility:
  random_state=42 is used both for per-chunk sampling AND for the final
  downsample, so re-running the script produces the identical output.

Runtime:
  Expect 5-15 minutes depending on disk speed (reads the full 2.5GB).

Output:
  data/raw/google_ads_sample_random.csv

Usage:
    Standalone:
        python src/data_collection/sample_google_ads_random.py

    Imported:
        from src.data_collection.sample_google_ads_random import create_random_sample
        df = create_random_sample()
"""

import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
RAW_FILE_PATH    = Path("data/raw/google_political_ads_raw.csv")
OUTPUT_FILE_PATH = Path("data/raw/google_ads_sample_random.csv")

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
CHUNK_SIZE   = 5_000    # rows read per iteration — keeps peak RAM flat
SAMPLE_FRAC  = 0.10     # fraction kept per chunk (10% of each chunk to ensure we hit 50k after US filter)
TARGET_ROWS  = 50_000   # final output size — 5x more data for richer analysis
RANDOM_STATE = 42       # fixed seed — guarantees identical output every run


def create_random_sample() -> pd.DataFrame | None:
    """
    Perform a true random sample of the full Google political ads CSV.

    Reads every chunk of the file, samples a small fraction from each,
    then randomly downsamples the accumulated result to TARGET_ROWS.
    Every row in the file has an equal probability of being chosen.

    Returns:
        Sampled DataFrame (TARGET_ROWS rows) on success, or None if the
        raw file is missing.
    """

    # ------------------------------------------------------------------
    # Guard: make sure the raw file exists before starting
    # ------------------------------------------------------------------
    if not RAW_FILE_PATH.exists():
        print("\n[random_sample] ERROR: Raw file not found.")
        print(f"  Expected: {RAW_FILE_PATH.resolve()}")
        print("  Download the Google Political Ads CSV and place it there.")
        return None

    print("\n[random_sample] TRUE random sampling — reading full dataset...")
    print(f"  Raw file      : {RAW_FILE_PATH.resolve()}")
    print(f"  Chunk size    : {CHUNK_SIZE:,} rows")
    print(f"  Per-chunk frac: {SAMPLE_FRAC} ({SAMPLE_FRAC*100:.1f}% of each chunk)")
    print(f"  Final rows    : {TARGET_ROWS:,} (after full-file downsample)")
    print(f"  Random seed   : {RANDOM_STATE}")
    print(f"  NOTE: reads the ENTIRE file — expect 5-15 minutes.\n")

    accumulated: list[pd.DataFrame] = []
    chunks_processed = 0
    rows_accumulated = 0

    # ------------------------------------------------------------------
    # PASS 1: Stream every chunk, sample a small fraction from each.
    #
    # Because we sample uniformly from EVERY chunk before stopping, each
    # row in the file has the same probability of appearing in the pool.
    # We never break early — the loop runs until pandas exhausts the file.
    # ------------------------------------------------------------------
    try:
        chunk_iter = pd.read_csv(
            RAW_FILE_PATH,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            on_bad_lines="skip",    # skip malformed rows without crashing
        )

        for chunk in chunk_iter:
            chunks_processed += 1

            # Filter to US ads only to match Meta dataset
            if "Regions" in chunk.columns:
                is_us = chunk["Regions"].fillna("").astype(str).str.strip().str.upper() == "US"
                chunk = chunk[is_us]
                
            # If the chunk has no US ads, skip sampling for this chunk
            if len(chunk) == 0:
                continue

            # Sample a small random fraction of this chunk.
            # min(frac=1.0) guards against edge case where chunk is tiny.
            n_to_sample = max(1, int(len(chunk) * SAMPLE_FRAC))
            sampled = chunk.sample(
                n=min(n_to_sample, len(chunk)),
                random_state=RANDOM_STATE,
            )

            accumulated.append(sampled)
            rows_accumulated += len(sampled)

            # Print progress every 100 chunks (~500k raw rows)
            if chunks_processed % 100 == 0:
                print(f"  ... {chunks_processed:,} chunks read, "
                      f"{rows_accumulated:,} rows in pool so far")

    except Exception as exc:
        print(f"\n[random_sample] ERROR reading file: {exc}")
        return None

    if not accumulated:
        print("[random_sample] No data could be read from the file.")
        return None

    print(f"\n  Full file read complete.")
    print(f"  Total chunks processed : {chunks_processed:,}")
    print(f"  Total rows in pool     : {rows_accumulated:,}")

    # ------------------------------------------------------------------
    # PASS 2: Combine the pool and downsample to exactly TARGET_ROWS.
    #
    # If the pool already has fewer rows than TARGET_ROWS (very small
    # file), just use all of them.
    # ------------------------------------------------------------------
    pool_df = pd.concat(accumulated, ignore_index=True)

    if len(pool_df) <= TARGET_ROWS:
        sample_df = pool_df
        print(f"  Pool smaller than target — using all {len(pool_df):,} rows.")
    else:
        sample_df = pool_df.sample(
            n=TARGET_ROWS,
            random_state=RANDOM_STATE,
        ).reset_index(drop=True)
        print(f"  Downsampled pool {len(pool_df):,} -> {len(sample_df):,} rows.")

    # ------------------------------------------------------------------
    # Save the final random sample
    # ------------------------------------------------------------------
    OUTPUT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample_df.to_csv(OUTPUT_FILE_PATH, index=False)

    print(f"\n[random_sample] Sampling complete.")
    print(f"  Rows in output : {len(sample_df):,}")
    print(f"  Saved to       : {OUTPUT_FILE_PATH.resolve()}\n")

    return sample_df


# ---------------------------------------------------------------------------
# Allow direct execution: python src/data_collection/sample_google_ads_random.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = create_random_sample()
    if result is not None:
        print(f"Done. True random sample of {len(result):,} rows saved.")
