from src.data_collection.meta_ads import fetch_meta_ads
from src.data_collection.google_ads import fetch_google_ads
from src.data_collection.sample_google_ads_random import create_random_sample
from src.data_collection.load_google_ads import load_and_standardize_google_ads
from src.preprocessing.clean_sponsors import clean_google_sponsors
from src.preprocessing.group_sponsors import group_similar_sponsors
from src.analysis.inspect_sponsor_groups import inspect_sponsor_groups
from src.analysis.dataset_summary import generate_dataset_summary
from src.analysis.create_visualizations import create_visualizations
from src.data_collection.load_meta_ads import load_and_standardize_meta_ads
from src.data_collection.run_meta_pipeline import run_meta_pipeline
from src.analysis.compare_platforms import compare_platforms


def main():
    print("=" * 60)
    print("  Political Ad Disclosure Pipeline Starting...")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1a (placeholder) — stub Meta ads record
    # ------------------------------------------------------------------
    print("\n[Step 1a] Fetching placeholder Meta ads...")
    meta_records = fetch_meta_ads()
    print(f"          -> {len(meta_records)} placeholder record(s).")

    # ------------------------------------------------------------------
    # Step 1b (placeholder) — stub Google ads record
    # ------------------------------------------------------------------
    print("\n[Step 1b] Fetching placeholder Google ads...")
    google_records = fetch_google_ads()
    print(f"          -> {len(google_records)} placeholder record(s).")

    # ------------------------------------------------------------------
    # Step 1.5 — Random sampling: draw a representative sample from the
    #             raw 2.5GB CSV (replaces biased sequential first-N-rows).
    # ------------------------------------------------------------------
    print("\n[Step 1.5] Creating random sample from raw Google ads data...")
    random_sample_df = create_random_sample()
    if random_sample_df is not None:
        print(f"           -> Random sample created: {len(random_sample_df):,} rows")
    else:
        print("           -> Skipped (raw CSV not found).")

    # ------------------------------------------------------------------
    # Step 2 — Standardize columns from the random sample
    # ------------------------------------------------------------------
    print("\n[Step 2]  Loading & standardizing Google Political Ads data...")
    google_std_df = load_and_standardize_google_ads()
    std_count = len(google_std_df) if google_std_df is not None else "N/A"
    print(f"          -> Standardized records: {std_count}")

    # ------------------------------------------------------------------
    # Step 3 — Normalize sponsor names (lowercase, strip suffixes, etc.)
    # ------------------------------------------------------------------
    print("\n[Step 3]  Cleaning sponsor names...")
    google_cleaned_df = clean_google_sponsors()
    cln_count = len(google_cleaned_df) if google_cleaned_df is not None else "N/A"
    print(f"          -> Cleaned records: {cln_count}")

    # ------------------------------------------------------------------
    # Step 4 — Fuzzy-group similar sponsor names (Union-Find)
    # ------------------------------------------------------------------
    print("\n[Step 4]  Grouping similar sponsor names (fuzzy matching)...")
    google_grouped_df = group_similar_sponsors()
    grp_count = len(google_grouped_df) if google_grouped_df is not None else "N/A"
    print(f"          -> Grouped records: {grp_count}")

    # ------------------------------------------------------------------
    # Step 5 — Inspect and validate the sponsor groups
    # ------------------------------------------------------------------
    print("\n[Step 5]  Inspecting sponsor group quality...")
    summary_df, review_df = inspect_sponsor_groups()
    if summary_df is not None:
        print(f"          -> Total groups:       {len(summary_df):,}")
        print(f"          -> Groups to review:   {len(review_df):,}")
    else:
        print("          -> Skipped (grouped file missing).")

    # ------------------------------------------------------------------
    # Step 6 — Dataset summary statistics
    # ------------------------------------------------------------------
    print("\n[Step 6]  Generating dataset summary statistics...")
    summary = generate_dataset_summary()
    if summary is not None:
        print(f"          -> Summary saved to dataset_summary.json")
    else:
        print("          -> Skipped (grouped file missing).")

    # ------------------------------------------------------------------
    # Step 7 — Generate visualizations
    # ------------------------------------------------------------------
    print("\n[Step 7]  Generating visualizations...")
    viz_ok = create_visualizations()
    if not viz_ok:
        print("          -> Skipped (grouped file missing).")

    # ------------------------------------------------------------------
    # Step 8A — Standardize Meta Ad Library CSV
    # Skips gracefully if data/raw/meta_ads_raw.csv not present.
    # ------------------------------------------------------------------
    print("\n[Step 8A] Standardizing Meta Ad Library data...")
    meta_std_df = load_and_standardize_meta_ads()
    if meta_std_df is not None:
        print(f"          -> Meta standardized: {len(meta_std_df):,} rows")
    else:
        print("          -> Skipped (place meta_ads_raw.csv in data/raw/ to enable).")

    # ------------------------------------------------------------------
    # Step 8B — Run full pipeline on Meta data
    # Only runs if 8A succeeded (meta_ads_standardized.csv exists).
    # ------------------------------------------------------------------
    print("\n[Step 8B] Running Meta preprocessing pipeline...")
    meta_ok = run_meta_pipeline()
    if not meta_ok:
        print("          -> Skipped (meta_ads_standardized.csv missing).")

    # ------------------------------------------------------------------
    # Step 8C — Cross-platform comparison
    # Only runs if both Google and Meta grouped files exist.
    # ------------------------------------------------------------------
    print("\n[Step 8C] Cross-platform comparison (Google vs Meta)...")
    compare_ok = compare_platforms()
    if not compare_ok:
        print("          -> Skipped (requires both Google and Meta grouped files).")

    # ------------------------------------------------------------------
    # Pipeline Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  Pipeline Summary")
    print("=" * 60)
    print(f"  Placeholder Meta records           : {len(meta_records)}")
    print(f"  Placeholder Google records          : {len(google_records)}")
    print(f"  Standardized Google ads  [Step 2]  : {std_count}")
    print(f"  Cleaned sponsor names    [Step 3]  : {cln_count}")
    print(f"  Fuzzy-grouped ads        [Step 4]  : {grp_count}")
    if summary_df is not None:
        print(f"  Sponsor groups total     [Step 5]  : {len(summary_df):,}")
        print(f"  Groups needing review    [Step 5]  : {len(review_df):,}")
    if summary is not None:
        print(f"  Total ads in summary     [Step 6]  : {summary['total_ads']:,}")
        print(f"  Unique sponsor groups    [Step 6]  : {summary['unique_sponsor_groups']:,}")
    if viz_ok:
        print(f"  Figures saved            [Step 7]  : outputs/figures/ (4 charts)")
    print("=" * 60)


if __name__ == "__main__":
    main()
