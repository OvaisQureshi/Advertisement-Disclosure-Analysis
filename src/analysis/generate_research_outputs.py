import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def generate_extras():
    print("[research_outputs] Loading grouped data...")
    df_g = pd.read_csv("data/processed/google_ads_grouped.csv", low_memory=False)
    df_m = pd.read_csv("data/processed/meta_ads_grouped.csv", low_memory=False)

    df_g['start_date'] = pd.to_datetime(df_g['start_date'], errors='coerce')
    df_m['start_date'] = pd.to_datetime(df_m['start_date'], errors='coerce')

    # Output directory
    os.makedirs("outputs/figures", exist_ok=True)
    
    google_color = '#EA4335'
    meta_color = '#1877F2'

    # ======================================================================
    # 1. Sponsor concentration analysis
    # ======================================================================
    print("Generating Sponsor Concentration Analysis...")
    
    plt.figure(figsize=(10, 6))
    
    stats_out = []
    
    for platform, data, color in [("Google", df_g, google_color), ("Meta", df_m, meta_color)]:
        # Get ad counts per sponsor sorted descending
        sponsor_counts = data['canonical_sponsor_name'].value_counts().values
        total_ads = sponsor_counts.sum()
        total_sponsors = len(sponsor_counts)
        
        # Cumulative percentages
        cumulative_ads_pct = sponsor_counts.cumsum() / total_ads * 100
        sponsor_percentile = np.arange(1, total_sponsors + 1) / total_sponsors * 100
        
        # Plot up to top 20%
        idx_20 = int(total_sponsors * 0.20)
        plt.plot(sponsor_percentile[:idx_20], cumulative_ads_pct[:idx_20], 
                 label=platform, linewidth=2, color=color)
        
        # Compute specific stats
        top_1_idx = max(0, int(total_sponsors * 0.01) - 1)
        top_5_idx = max(0, int(total_sponsors * 0.05) - 1)
        top_10_idx = max(0, int(total_sponsors * 0.10) - 1)
        
        stats_out.append({
            "Platform": platform,
            "Top 1% Sponsors Control": cumulative_ads_pct[top_1_idx] if top_1_idx >= 0 else 100,
            "Top 5% Sponsors Control": cumulative_ads_pct[top_5_idx] if top_5_idx >= 0 else 100,
            "Top 10% Sponsors Control": cumulative_ads_pct[top_10_idx] if top_10_idx >= 0 else 100
        })

    plt.title("Cumulative Distribution Curve of Ads by Sponsor")
    plt.xlabel("Top % of Sponsors")
    plt.ylabel("Cumulative % of Total Ads")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig("outputs/figures/concentration_curve.png", dpi=300)
    plt.close()

    print("\n--- Concentration Summary Stats ---")
    for stat in stats_out:
        print(f"[{stat['Platform']}] Top 1%: {stat['Top 1% Sponsors Control']:.1f}% | Top 5%: {stat['Top 5% Sponsors Control']:.1f}% | Top 10%: {stat['Top 10% Sponsors Control']:.1f}%")
        
    # ======================================================================
    # 2. Spend distribution comparison
    # ======================================================================
    print("Generating Spend Distribution Comparison...")
    
    df_g['spend_mid'] = (pd.to_numeric(df_g['spend_lower'], errors='coerce') + 
                         pd.to_numeric(df_g['spend_upper'], errors='coerce')) / 2
    df_m['spend_mid'] = (pd.to_numeric(df_m['spend_lower'], errors='coerce') + 
                         pd.to_numeric(df_m['spend_upper'], errors='coerce')) / 2

    # Drop nulls and zero-spend for log scale
    g_spend = df_g['spend_mid'].dropna()
    g_spend = g_spend[g_spend > 0]
    
    m_spend = df_m['spend_mid'].dropna()
    m_spend = m_spend[m_spend > 0]

    plt.figure(figsize=(10, 6))
    
    # We use a log-scaled histogram because political ad spend spans from $1 to $1,000,000+
    bins = np.logspace(np.log10(1), np.log10(max(g_spend.max(), m_spend.max())), 50)
    
    plt.hist(g_spend, bins=bins, alpha=0.5, color=google_color, label='Google', density=True)
    plt.hist(m_spend, bins=bins, alpha=0.5, color=meta_color, label='Meta', density=True)
    
    plt.xscale('log')
    plt.title("Spend Distribution per Ad (Log Scale)")
    plt.xlabel("Estimated Spend ($)")
    plt.ylabel("Density")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig("outputs/figures/spend_distribution_google_vs_meta.png", dpi=300)
    plt.close()

    # ======================================================================
    # 3. Time trends
    # ======================================================================
    print("Generating Time Trends...")
    
    plt.figure(figsize=(14, 6))
    for label, data, color in [("Google", df_g, google_color), ("Meta", df_m, meta_color)]:
        mask = (data['start_date'] >= '2018-05-01') & (data['start_date'] <= '2026-12-31')
        monthly = data.loc[mask].groupby(pd.Grouper(key='start_date', freq='ME')).size()
        plt.plot(monthly.index, monthly.values, label=label, linewidth=2, color=color)

    plt.title("Ad Volume Over Time")
    plt.xlabel("Date")
    plt.ylabel("Monthly Ad Count")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig("outputs/figures/ads_over_time_google_vs_meta.png", dpi=300)
    plt.close()

    # ======================================================================
    # 4. Platform comparison figure (Table as PNG)
    # ======================================================================
    print("Generating Platform Comparison Table Image...")

    table_data = [
        ["Ad-level data", "Yes (Bulk CSV format)", "Yes (Paginated API format)"],
        ["Spend granularity", "Ranges mapping to actual USD", "Strict numeric ranges (e.g. 0-99)"],
        ["Impressions", "Broad strings (e.g. '10k-100k')", "Numeric bounds based ranges"],
        ["Dates", "Available, highly complete", "Available, occasionally truncated"],
        ["Sponsor naming quality", "Highly standardized & regulated", "Extremely messy, highly variant"]
    ]
    
    columns = ["Feature", "Google Transparency Report", "Meta Ad Library"]

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis('off')
    
    table = ax.table(cellText=table_data, colLabels=columns, loc='center', cellLoc='left')
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 2)
    
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            if col == 1:
                cell.set_facecolor(google_color)
            elif col == 2:
                cell.set_facecolor(meta_color)
            else:
                cell.set_facecolor('#333333')
        padding = 0.05
        cell.PAD = padding
        
    plt.title("Platform Transparency Features Comparison", weight='bold', size=16, pad=20)
    plt.tight_layout()
    plt.savefig("outputs/figures/platform_comparison_table.png", dpi=300, bbox_inches='tight')
    plt.close()

    print("\nAll research outputs complete!")

if __name__ == "__main__":
    generate_extras()
