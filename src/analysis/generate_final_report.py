import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def generate_report():
    print("[final_report] Loading grouped data...")
    # Load Google and Meta grouped datasets
    df_g = pd.read_csv("data/processed/google_ads_grouped.csv", low_memory=False)
    df_m = pd.read_csv("data/processed/meta_ads_grouped.csv", low_memory=False)

    # Convert start dates to datetime for temporal analysis
    df_g['start_date'] = pd.to_datetime(df_g['start_date'], errors='coerce')
    df_m['start_date'] = pd.to_datetime(df_m['start_date'], errors='coerce')

    # Output directories
    Path("outputs/figures").mkdir(parents=True, exist_ok=True)
    Path("outputs/tables").mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # PART 1: Sponsor ambiguity analysis
    # ---------------------------------------------------------
    print("Generating Part 1: Sponsor Ambiguity...")
    
    # Calculate counts combined for both platforms as a grand total of reduction, 
    # or just show reduction for each platform separately. We'll do a combined overview.
    # Raw sponsor count
    google_raw = df_g['sponsor_name'].nunique(dropna=False)
    google_clean = df_g['clean_sponsor_name'].nunique(dropna=False)
    google_grouped = df_g['canonical_sponsor_name'].nunique(dropna=False)

    meta_raw = df_m['sponsor_name'].nunique(dropna=False)
    meta_clean = df_m['clean_sponsor_name'].nunique(dropna=False)
    meta_grouped = df_m['canonical_sponsor_name'].nunique(dropna=False)

    # Plot sponsor name reduction
    fig, ax = plt.subplots(figsize=(10, 6))
    stages = ['Raw Names', 'Cleaned Names', 'Grouped Names']
    g_counts = [google_raw, google_clean, google_grouped]
    m_counts = [meta_raw, meta_clean, meta_grouped]

    val_g = ax.bar([x - 0.2 for x in range(3)], g_counts, width=0.4, label='Google', color='#EA4335')
    val_m = ax.bar([x + 0.2 for x in range(3)], m_counts, width=0.4, label='Meta', color='#1877F2')

    ax.set_xticks(range(3))
    ax.set_xticklabels(stages)
    ax.set_title("Sponsor Name Dimensionality Reduction")
    ax.set_ylabel("Unique Sponsor Count")
    ax.legend()
    
    # Annotate bars
    for bars in [val_g, val_m]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{int(height):,}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig("outputs/figures/sponsor_name_reduction.png", dpi=300)
    plt.close()

    # Table: top sponsor groups
    # Combine datasets to get global top sponsor groups
    df_all = pd.concat([df_g, df_m], ignore_index=True)
    ambiguity_table = df_all.groupby('canonical_sponsor_name').agg(
        number_of_ads=('ad_id', 'count'),
        number_of_variants=('sponsor_name', 'nunique')
    ).reset_index()
    # Sort by number of variants to show messy names, or by ad count
    ambiguity_table = ambiguity_table.sort_values(by='number_of_variants', ascending=False)
    # Save top 50
    ambiguity_table.head(50).to_csv("outputs/tables/top_sponsor_groups.csv", index=False)

    # ---------------------------------------------------------
    # PART 2: Advertiser concentration
    # ---------------------------------------------------------
    print("Generating Part 2: Advertiser Concentration...")
    
    # Top sponsors Google
    g_top = df_g['canonical_sponsor_name'].value_counts().head(10)
    plt.figure(figsize=(12, 6))
    g_top.plot(kind='bar', color='#EA4335')
    plt.title("Top 10 Sponsors by Ad Count (Google)")
    plt.ylabel("Number of Ads")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig("outputs/figures/top_sponsors_google.png", dpi=300)
    plt.close()

    # Top sponsors Meta
    m_top = df_m['canonical_sponsor_name'].value_counts().head(10)
    plt.figure(figsize=(12, 6))
    m_top.plot(kind='bar', color='#1877F2')
    plt.title("Top 10 Sponsors by Ad Count (Meta)")
    plt.ylabel("Number of Ads")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig("outputs/figures/top_sponsors_meta.png", dpi=300)
    plt.close()

    # Pareto Distribution
    plt.figure(figsize=(10, 6))
    for data, label, color in [(df_g, "Google", "#EA4335"), (df_m, "Meta", "#1877F2")]:
        sponsor_counts = data['canonical_sponsor_name'].value_counts().values
        cumulative_pct = sponsor_counts.cumsum() / sponsor_counts.sum() * 100
        # Plot up to first 500 sponsors to show the curve clearly
        plt.plot(range(1, len(cumulative_pct[:500]) + 1), cumulative_pct[:500], label=label, linewidth=2, color=color)

    plt.title("Cumulative Distribution of Ads (Pareto)")
    plt.xlabel("Sponsor Rank")
    plt.ylabel("Cumulative % of Total Ads")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig("outputs/figures/pareto_distribution.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # PART 3: Cross-platform comparison
    # ---------------------------------------------------------
    print("Generating Part 3: Cross-platform comparison...")
    
    comp_data = []
    for platform, data in [("Google", df_g), ("Meta", df_m)]:
        total_ads = len(data)
        unique_sp = data['canonical_sponsor_name'].nunique()
        avg_ads = total_ads / unique_sp if unique_sp > 0 else 0
        comp_data.append({
            "Platform": platform,
            "total_ads": total_ads,
            "unique_sponsors": unique_sp,
            "avg_ads_per_sponsor": round(avg_ads, 2)
        })
    pd.DataFrame(comp_data).to_csv("outputs/tables/platform_comparison.csv", index=False)

    # ---------------------------------------------------------
    # PART 4: Data completeness
    # ---------------------------------------------------------
    print("Generating Part 4: Data completeness...")

    missing_data = []
    cols = ['ad_text', 'impressions_upper', 'end_date'] # meta handles impressions as upper/lower
    for platform, data in [("Google", df_g), ("Meta", df_m)]:
        for col in cols:
            actual_col = col
            # Google's impressions are sometimes null, Meta's might be empty strings or NaN
            pct_missing = data[actual_col].isna().sum() / len(data) * 100
            missing_data.append({"Platform": platform, "Field": col, "Missing_Pct": pct_missing})
            
    md_df = pd.DataFrame(missing_data).pivot(index='Field', columns='Platform', values='Missing_Pct')
    
    ax = md_df.plot(kind='bar', figsize=(10, 6), color=['#EA4335', '#1877F2'])
    plt.title("Data Completeness Gaps")
    plt.ylabel("% Missing Values")
    plt.xlabel("Field")
    plt.xticks(rotation=0)
    
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', padding=3)

    plt.tight_layout()
    plt.savefig("outputs/figures/missing_data.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # PART 5: Temporal trends
    # ---------------------------------------------------------
    print("Generating Part 5: Temporal trends...")
    
    plt.figure(figsize=(14, 6))
    for data, label, color in [(df_g, "Google", "#EA4335"), (df_m, "Meta", "#1877F2")]:
        # Filter out bad dates, bound between 2018 and 2026
        mask = (data['start_date'] >= '2018-05-01') & (data['start_date'] <= '2026-12-31')
        monthly = data.loc[mask].groupby(pd.Grouper(key='start_date', freq='ME')).size()
        plt.plot(monthly.index, monthly.values, label=label, linewidth=2, color=color)

    plt.title("Ads Over Time (Monthly Counts)")
    plt.xlabel("Date")
    plt.ylabel("Ad Count")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig("outputs/figures/ads_over_time_comparison.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # Final Summary Print
    # ---------------------------------------------------------
    print("\n" + "="*50)
    print("FINAL ANALYSIS SUMMARY")
    print("="*50)
    
    g_reduction = (google_raw - google_grouped) / google_raw * 100 if google_raw else 0
    m_reduction = (meta_raw - meta_grouped) / meta_raw * 100 if meta_raw else 0
    print(f"- Sponsor Reduction % : Google {g_reduction:.1f}% | Meta {m_reduction:.1f}%")
    
    g_top1_share = df_g['canonical_sponsor_name'].value_counts().max() / len(df_g) * 100
    m_top1_share = df_m['canonical_sponsor_name'].value_counts().max() / len(df_m) * 100
    print(f"- Top 1 Sponsor Share %: Google {g_top1_share:.1f}% | Meta {m_top1_share:.1f}%")
    
    print("\nKey Differences Between Platforms:")
    print("1. Data Structure: Meta forces API keyword-biased pagination; Google provides true random bulk access.")
    print("2. Concentration: (See pareto_distribution.png) Check how ad volume centralizes around top players.")
    print("3. Completeness : (See missing_data.png) Platforms enforce different internal rules about end dates and visibility.")
    print("="*50)


if __name__ == "__main__":
    generate_report()
