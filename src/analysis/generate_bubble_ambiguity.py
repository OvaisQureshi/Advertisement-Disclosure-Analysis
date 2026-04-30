import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_bracket_bubble_chart():
    print("[bubble_chart] Loading grouped data...")
    df_g = pd.read_csv("data/processed/google_ads_grouped.csv", low_memory=False)
    df_m = pd.read_csv("data/processed/meta_ads_grouped.csv", low_memory=False)

    def calc_ambiguity(df):
        ambig = df.groupby('canonical_sponsor_name').agg(
            ad_count=('ad_id', 'count'),
            num_variants=('sponsor_name', 'nunique')
        ).reset_index()
        ambig = ambig[ambig['canonical_sponsor_name'].notna()]
        total_platform_errors = (ambig['num_variants'] - 1).sum()
        return ambig, total_platform_errors

    g_ambig, g_total_errs = calc_ambiguity(df_g)
    m_ambig, m_total_errs = calc_ambiguity(df_m)
    
    g_total_ads = len(df_g)
    g_total_sponsors = len(g_ambig)
    
    m_total_ads = len(df_m)
    m_total_sponsors = len(m_ambig)

    def get_bracket_stats(df_ambig, total_ads, total_sponsors, total_errs, pct):
        # We look at the TOP X% block of sponsors. If 100%, take all.
        n_top = max(1, int(total_sponsors * (pct/100.0))) if pct < 100 else len(df_ambig)
        top_slice = df_ambig.sort_values('ad_count', ascending=False).head(n_top)
        
        ad_share = (top_slice['ad_count'].sum() / total_ads) * 100
        
        tier_errs = (top_slice['num_variants'] - 1).sum()
        err_share = (tier_errs / total_errs) * 100 if total_errs > 0 else 0
        
        return ad_share, err_share

    # The exact brackets the user requested
    brackets = [1, 5, 10, 50, 70, 100]
    
    g_stats = [get_bracket_stats(g_ambig, g_total_ads, g_total_sponsors, g_total_errs, b) for b in brackets]
    m_stats = [get_bracket_stats(m_ambig, m_total_ads, m_total_sponsors, m_total_errs, b) for b in brackets]

    # Increase width to accommodate 6 columns
    plt.figure(figsize=(20, 8), facecolor='#F8F9FA')
    ax = plt.gca()

    size_multiplier = 130  # slightly smaller bubbles so they don't overlap as badly
    
    x_positions = [1, 2, 3, 4, 5, 6]
    
    # Plot Google (Red)
    g_sizes = [stat[0] * size_multiplier for stat in g_stats]
    plt.scatter(x_positions, [7] * len(brackets), s=g_sizes, color='#EA4335', alpha=0.85, edgecolors='white', linewidth=3, label='Google')

    # Plot Meta (Blue)
    m_sizes = [stat[0] * size_multiplier for stat in m_stats]
    plt.scatter(x_positions, [3] * len(brackets), s=m_sizes, color='#1877F2', alpha=0.85, edgecolors='white', linewidth=3, label='Meta')

    for i, _ in enumerate(brackets):
        # ---------------- GOOGLE ----------------
        g_ad_share, g_err_share = g_stats[i]
        plt.annotate(
            f"{g_ad_share:.1f}%\nof ads",
            (x_positions[i], 7),
            ha='center', va='center', color='white', weight='bold', fontsize=12
        )
        plt.annotate(
            f"Accounts for\n{g_err_share:.1f}%\nof spelling errors",
            (x_positions[i], 5.6),
            ha='center', va='top', color='#EA4335', weight='bold', fontsize=11,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9)
        )
        
        # ---------------- META ----------------
        m_ad_share, m_err_share = m_stats[i]
        plt.annotate(
            f"{m_ad_share:.1f}%\nof ads",
            (x_positions[i], 3),
            ha='center', va='center', color='white', weight='bold', fontsize=12
        )
        plt.annotate(
            f"Accounts for\n{m_err_share:.1f}%\nof spelling errors",
            (x_positions[i], 1.6),
            ha='center', va='top', color='#1877F2', weight='bold', fontsize=11,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9)
        )

    plt.title("Ad Centralization vs. Identity Fragmentation (Distribution Across Tiers)", fontsize=22, weight='bold', pad=25)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    plt.yticks([]) 
    
    xtick_labels = [f"Top {b}%" for b in brackets]
    plt.xticks(x_positions, xtick_labels, fontsize=16, weight='bold')
    
    plt.ylim(0, 9)
    plt.xlim(0.3, 6.7)
    
    leg = plt.legend(fontsize=15, loc='upper left', frameon=True, shadow=True)
    for handle in leg.legend_handles:
        handle.set_sizes([300.0])
        
    plt.figtext(0.5, 0.02, "KEY FINDING: Heavyweight spenders (Top 10%) are perfectly clean. Meta's massive transparency variations exist almost entirely past the 50% threshold within the grassroots.", 
                ha="center", fontsize=15, weight='bold', color='#B31B1B')

    os.makedirs("outputs/figures", exist_ok=True)
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig("outputs/figures/ambiguity_bubble_chart_infographic.png", dpi=300)
    plt.close()
    
    print("Saved expanded infographic to outputs/figures/ambiguity_bubble_chart_infographic.png")

if __name__ == "__main__":
    generate_bracket_bubble_chart()
