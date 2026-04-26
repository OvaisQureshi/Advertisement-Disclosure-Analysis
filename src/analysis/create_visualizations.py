"""
create_visualizations.py
------------------------
Step 7 of the Political Ad Disclosure Analysis Pipeline.

Generates 10 publication-ready charts using both the grouped dataset
(for sponsor analysis) and the raw random sample (for geographic,
ad-type, and temporal analysis).

Charts produced:
  1.  top_sponsors_by_ad_count.png       -- top 15 sponsors by ad volume
  2.  top_sponsors_by_spend.png          -- top 15 sponsors by total estimated spend
  3.  spend_distribution.png             -- histogram of avg estimated spend
  4.  monthly_ad_volume.png              -- monthly ad count line chart
  5.  monthly_spend_trend.png            -- monthly total spend line chart
  6.  geographic_distribution.png        -- top 15 countries/regions by ad count
  7.  ad_type_distribution.png           -- breakdown of ad format types
  8.  campaign_duration_distribution.png -- histogram of campaign length in days
  9.  sponsor_cleaning_impact.png        -- before/after normalization bar chart
  10. spend_vs_adcount_scatter.png       -- top 30 sponsors: spend vs volume scatter

Output folder: outputs/figures/
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
GROUPED_PATH     = Path("data/processed/google_ads_grouped.csv")
RAW_SAMPLE_PATH  = Path("data/raw/google_ads_sample_random.csv")
OUTPUT_DIR       = Path("outputs/figures")

# ---------------------------------------------------------------------------
# SHARED STYLE
# ---------------------------------------------------------------------------
BACKGROUND  = "#0f1117"
AXES_BG     = "#1c1f2b"
TEXT        = "#e8eaf0"
BLUE        = "#4f8ef7"
PURPLE      = "#a78bfa"
TEAL        = "#34d399"
ORANGE      = "#f59e0b"
RED         = "#f87171"
PINK        = "#f472b6"
GRID        = "#2a2d3a"
PALETTE     = [BLUE, PURPLE, TEAL, ORANGE, RED, PINK,
               "#60a5fa", "#818cf8", "#6ee7b7", "#fcd34d",
               "#fca5a5", "#f9a8d4", "#67e8f9", "#86efac", "#fdba74"]

TITLE_FS    = 15
LABEL_FS    = 11
TICK_FS     = 9
DPI         = 180


def _style(fig: plt.Figure, ax: plt.Axes) -> None:
    """Apply consistent dark-mode styling to any figure/axes pair."""
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_facecolor(AXES_BG)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.tick_params(colors=TEXT, labelsize=TICK_FS)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)
    ax.set_axisbelow(True)
    ax.grid(True, color=GRID, linewidth=0.6, linestyle="--", alpha=0.7)


def _save(fig: plt.Figure, name: str) -> None:
    """Save figure and close it."""
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [saved] {path}")


def _comma(x, _):
    return f"{int(x):,}"


def _dollar(x, _):
    return f"${int(x):,}"


# ===========================================================================
# CHART 1 — Top Sponsors by Ad Count
# ===========================================================================
def _chart_top_sponsors_count(df: pd.DataFrame) -> None:
    valid = df[df["sponsor_group_id"] >= 0]
    top = (valid.groupby("canonical_sponsor_name").size()
           .reset_index(name="num_ads")
           .sort_values("num_ads", ascending=False)
           .head(15).iloc[::-1])

    fig, ax = plt.subplots(figsize=(12, 7))
    _style(fig, ax)
    bars = ax.barh(top["canonical_sponsor_name"], top["num_ads"],
                   color=BLUE, edgecolor="none", height=0.65)
    for b in bars:
        ax.text(b.get_width() + top["num_ads"].max() * 0.01,
                b.get_y() + b.get_height() / 2,
                f"{int(b.get_width()):,}", va="center", ha="left",
                color=TEXT, fontsize=TICK_FS)

    ax.set_xlabel("Number of Ads", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Top 15 Political Advertisers by Ad Count\n"
                 "(Google Ads Transparency — Random Sample, n=50,000)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, top["num_ads"].max() * 1.15)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_comma))
    fig.tight_layout()
    _save(fig, "top_sponsors_by_ad_count.png")


# ===========================================================================
# CHART 2 — Top Sponsors by Total Estimated Spend
# ===========================================================================
def _chart_top_sponsors_spend(df: pd.DataFrame) -> None:
    d = df[df["sponsor_group_id"] >= 0].copy()
    d["avg_spend"] = (pd.to_numeric(d["spend_lower"], errors="coerce") +
                      pd.to_numeric(d["spend_upper"], errors="coerce")) / 2

    top = (d.groupby("canonical_sponsor_name")["avg_spend"].sum()
           .reset_index(name="total_spend")
           .sort_values("total_spend", ascending=False)
           .head(15).iloc[::-1])

    fig, ax = plt.subplots(figsize=(12, 7))
    _style(fig, ax)
    bars = ax.barh(top["canonical_sponsor_name"], top["total_spend"],
                   color=PURPLE, edgecolor="none", height=0.65)
    for b in bars:
        ax.text(b.get_width() + top["total_spend"].max() * 0.01,
                b.get_y() + b.get_height() / 2,
                f"${int(b.get_width()):,}", va="center", ha="left",
                color=TEXT, fontsize=TICK_FS)

    ax.set_xlabel("Total Estimated Spend (USD)", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Top 15 Political Advertisers by Total Estimated Spend\n"
                 "(Google Ads Transparency — Random Sample, n=50,000)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, top["total_spend"].max() * 1.18)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_dollar))
    fig.tight_layout()
    _save(fig, "top_sponsors_by_spend.png")


# ===========================================================================
# CHART 3 — Spend Distribution (histogram)
# ===========================================================================
def _chart_spend_distribution(df: pd.DataFrame) -> None:
    avg = ((pd.to_numeric(df["spend_lower"], errors="coerce") +
            pd.to_numeric(df["spend_upper"], errors="coerce")) / 2).dropna()
    cutoff = avg.quantile(0.95)
    trimmed = avg[avg <= cutoff]

    fig, ax = plt.subplots(figsize=(10, 6))
    _style(fig, ax)
    ax.hist(trimmed, bins=60, color=PURPLE, edgecolor=BACKGROUND,
            linewidth=0.3, alpha=0.9)
    med = trimmed.median()
    ax.axvline(med, color=ORANGE, linestyle="--", linewidth=1.8,
               label=f"Median  ${med:,.0f}")
    ax.set_xlabel("Avg Estimated Spend per Ad (USD)", fontsize=LABEL_FS, labelpad=10)
    ax.set_ylabel("Number of Ads", fontsize=LABEL_FS, labelpad=10)
    ax.set_title(f"Distribution of Estimated Ad Spend\n"
                 f"(Bottom 95% shown  |  95th pct = ${cutoff:,.0f})",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_dollar))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_comma))
    ax.legend(fontsize=TICK_FS, facecolor=AXES_BG, edgecolor=GRID,
              labelcolor=TEXT)
    fig.tight_layout()
    _save(fig, "spend_distribution.png")


# ===========================================================================
# CHART 4 — Monthly Ad Volume
# ===========================================================================
def _chart_monthly_volume(df: pd.DataFrame) -> None:
    d = df.copy()
    d["start_date"] = pd.to_datetime(d["start_date"], errors="coerce")
    d = d.dropna(subset=["start_date"])
    d["month"] = d["start_date"].dt.to_period("M")
    monthly = (d.groupby("month").size().reset_index(name="num_ads")
               .sort_values("month"))
    monthly["ts"] = monthly["month"].dt.to_timestamp()

    fig, ax = plt.subplots(figsize=(14, 6))
    _style(fig, ax)
    ax.plot(monthly["ts"], monthly["num_ads"], color=TEAL, linewidth=2, zorder=3)
    ax.fill_between(monthly["ts"], monthly["num_ads"], alpha=0.18, color=TEAL)
    ax.scatter(monthly["ts"], monthly["num_ads"], color=TEAL, s=25, zorder=4)

    # Annotate election cycle peaks
    peak_idx = monthly["num_ads"].nlargest(3).index
    for idx in peak_idx:
        row = monthly.loc[idx]
        ax.annotate(f"{row['month']}\n{int(row['num_ads']):,} ads",
                    xy=(row["ts"], row["num_ads"]),
                    xytext=(0, 14), textcoords="offset points",
                    ha="center", fontsize=7.5, color=ORANGE,
                    arrowprops=dict(arrowstyle="-", color=ORANGE, lw=0.8))

    ax.set_xlabel("Month", fontsize=LABEL_FS, labelpad=10)
    ax.set_ylabel("Number of Ads", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Political Ad Volume Over Time\n"
                 "(Google Ads Transparency — Monthly Counts, n=50,000)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=TICK_FS)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_comma))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    fig.tight_layout()
    _save(fig, "monthly_ad_volume.png")


# ===========================================================================
# CHART 5 — Monthly Total Spend Trend
# ===========================================================================
def _chart_monthly_spend(df: pd.DataFrame) -> None:
    d = df.copy()
    d["start_date"] = pd.to_datetime(d["start_date"], errors="coerce")
    d = d.dropna(subset=["start_date"])
    d["avg_spend"] = (pd.to_numeric(d["spend_lower"], errors="coerce") +
                      pd.to_numeric(d["spend_upper"], errors="coerce")) / 2
    d["month"] = d["start_date"].dt.to_period("M")
    monthly = (d.groupby("month")["avg_spend"].sum().reset_index(name="total_spend")
               .sort_values("month"))
    monthly["ts"] = monthly["month"].dt.to_timestamp()

    fig, ax = plt.subplots(figsize=(14, 6))
    _style(fig, ax)
    ax.plot(monthly["ts"], monthly["total_spend"], color=ORANGE, linewidth=2, zorder=3)
    ax.fill_between(monthly["ts"], monthly["total_spend"], alpha=0.18, color=ORANGE)
    ax.scatter(monthly["ts"], monthly["total_spend"], color=ORANGE, s=25, zorder=4)

    ax.set_xlabel("Month", fontsize=LABEL_FS, labelpad=10)
    ax.set_ylabel("Total Estimated Spend (USD)", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Monthly Total Political Ad Spend\n"
                 "(Google Ads Transparency — Estimated USD, n=50,000)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=TICK_FS)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    fig.tight_layout()
    _save(fig, "monthly_spend_trend.png")


# ===========================================================================
# CHART 6 — Geographic Distribution (top 15 countries/regions)
# Uses the raw sample CSV which has the Regions column.
# ===========================================================================
def _chart_geographic(raw_df: pd.DataFrame) -> None:
    if "Regions" not in raw_df.columns:
        print("  [skip] Regions column not found in raw sample.")
        return

    # Each row may contain a comma-separated list of region strings like
    # "United States, California" — extract the first token as the top-level
    # region/country.
    def first_region(val):
        if pd.isna(val):
            return "Unknown"
        # Split on comma, strip whitespace, return first part
        parts = [p.strip() for p in str(val).split(",")]
        return parts[0] if parts else "Unknown"

    regions = raw_df["Regions"].apply(first_region)
    top = (regions.value_counts().head(15).reset_index()
           .rename(columns={"index": "region", "Regions": "count"}))
    top.columns = ["region", "count"]
    top = top.iloc[::-1]   # flip for horizontal bar

    fig, ax = plt.subplots(figsize=(12, 7))
    _style(fig, ax)
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(top))]
    bars = ax.barh(top["region"], top["count"], color=colors,
                   edgecolor="none", height=0.65)
    for b in bars:
        ax.text(b.get_width() + top["count"].max() * 0.01,
                b.get_y() + b.get_height() / 2,
                f"{int(b.get_width()):,}", va="center", ha="left",
                color=TEXT, fontsize=TICK_FS)

    ax.set_xlabel("Number of Ads", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Top 15 Geographic Regions by Ad Count\n"
                 "(Google Ads Transparency — First Region Tag per Ad)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, top["count"].max() * 1.15)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_comma))
    fig.tight_layout()
    _save(fig, "geographic_distribution.png")


# ===========================================================================
# CHART 7 — Ad Type Distribution
# ===========================================================================
def _chart_ad_type(raw_df: pd.DataFrame) -> None:
    col = next((c for c in raw_df.columns
                if c.lower() in ("ad_type", "adtype", "type")), None)
    if col is None:
        print("  [skip] Ad_Type column not found.")
        return

    counts = raw_df[col].fillna("Unknown").value_counts()

    fig, ax = plt.subplots(figsize=(9, 6))
    _style(fig, ax)
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(counts))]
    bars = ax.bar(counts.index, counts.values, color=colors,
                  edgecolor="none", width=0.55)
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2,
                b.get_height() + counts.max() * 0.01,
                f"{int(b.get_height()):,}", ha="center", va="bottom",
                color=TEXT, fontsize=TICK_FS)

    ax.set_ylabel("Number of Ads", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Political Ad Format Distribution\n"
                 "(Google Ads Transparency — Ad Type Breakdown)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=TICK_FS)
    ax.tick_params(axis="x", length=0)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_comma))
    fig.tight_layout()
    _save(fig, "ad_type_distribution.png")


# ===========================================================================
# CHART 8 — Campaign Duration Distribution
# ===========================================================================
def _chart_campaign_duration(df: pd.DataFrame) -> None:
    d = df.copy()
    d["start_date"] = pd.to_datetime(d["start_date"], errors="coerce")
    d["end_date"]   = pd.to_datetime(d["end_date"],   errors="coerce")
    d["duration"]   = (d["end_date"] - d["start_date"]).dt.days
    durations = d["duration"].dropna()
    durations = durations[(durations >= 0) & (durations <= durations.quantile(0.97))]

    fig, ax = plt.subplots(figsize=(10, 6))
    _style(fig, ax)
    ax.hist(durations, bins=60, color=PINK, edgecolor=BACKGROUND,
            linewidth=0.3, alpha=0.9)
    med = durations.median()
    ax.axvline(med, color=ORANGE, linestyle="--", linewidth=1.8,
               label=f"Median  {med:.0f} days")

    ax.set_xlabel("Campaign Duration (Days)", fontsize=LABEL_FS, labelpad=10)
    ax.set_ylabel("Number of Ads", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Political Ad Campaign Duration Distribution\n"
                 "(97th percentile cutoff applied for readability)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_comma))
    ax.legend(fontsize=TICK_FS, facecolor=AXES_BG, edgecolor=GRID,
              labelcolor=TEXT)
    fig.tight_layout()
    _save(fig, "campaign_duration_distribution.png")


# ===========================================================================
# CHART 9 — Sponsor Name Cleaning Impact
# ===========================================================================
def _chart_cleaning_impact(df: pd.DataFrame) -> None:
    raw   = df["sponsor_name"].nunique()
    clean = df["clean_sponsor_name"].nunique()
    grp   = df[df["sponsor_group_id"] >= 0]["sponsor_group_id"].nunique()

    labels = ["Raw\nSponsor Names", "Cleaned\nSponsor Names",
              "Fuzzy-Grouped\nSponsor Groups"]
    values = [raw, clean, grp]
    colors = [BLUE, PURPLE, TEAL]

    fig, ax = plt.subplots(figsize=(8, 6))
    _style(fig, ax)
    bars = ax.bar(labels, values, color=colors, edgecolor="none", width=0.45)

    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + max(values) * 0.012,
                f"{v:,}", ha="center", va="bottom",
                color=TEXT, fontsize=LABEL_FS, fontweight="bold")

    for i in range(len(values) - 1):
        delta = values[i] - values[i + 1]
        pct   = delta / values[i] * 100
        ax.annotate(f"-{delta:,}\n({pct:.1f}%)",
                    xy=((i + i + 1) / 2, max(values[i], values[i + 1]) * 0.55),
                    ha="center", va="center", color=RED, fontsize=TICK_FS)

    ax.set_ylabel("Distinct Identifiers", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Impact of Sponsor Name Normalization\n"
                 "(Raw  →  Cleaned  →  Fuzzy Grouped)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    ax.set_ylim(0, max(values) * 1.18)
    ax.tick_params(axis="x", length=0)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_comma))
    fig.tight_layout()
    _save(fig, "sponsor_cleaning_impact.png")


# ===========================================================================
# CHART 10 — Spend vs Ad Count Scatter (top 40 sponsors)
# ===========================================================================
def _chart_spend_vs_count_scatter(df: pd.DataFrame) -> None:
    d = df[df["sponsor_group_id"] >= 0].copy()
    d["avg_spend"] = (pd.to_numeric(d["spend_lower"], errors="coerce") +
                      pd.to_numeric(d["spend_upper"], errors="coerce")) / 2

    agg = (d.groupby("canonical_sponsor_name")
           .agg(num_ads=("sponsor_group_id", "count"),
                total_spend=("avg_spend", "sum"))
           .reset_index()
           .sort_values("num_ads", ascending=False)
           .head(40))

    fig, ax = plt.subplots(figsize=(11, 8))
    _style(fig, ax)

    sc = ax.scatter(
        agg["num_ads"], agg["total_spend"],
        s=agg["total_spend"] / agg["total_spend"].max() * 600 + 40,
        c=agg["num_ads"], cmap="cool",
        alpha=0.85, edgecolors=BACKGROUND, linewidths=0.5, zorder=3,
    )

    # Label the top 10 by ad count
    for _, row in agg.head(10).iterrows():
        label = row["canonical_sponsor_name"]
        # Truncate long names
        if len(label) > 28:
            label = label[:25] + "..."
        ax.annotate(label,
                    xy=(row["num_ads"], row["total_spend"]),
                    xytext=(6, 4), textcoords="offset points",
                    color=TEXT, fontsize=7, alpha=0.9)

    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label("Ad Count", color=TEXT, fontsize=TICK_FS)
    cbar.ax.yaxis.set_tick_params(color=TEXT)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=TEXT)

    ax.set_xlabel("Number of Ads", fontsize=LABEL_FS, labelpad=10)
    ax.set_ylabel("Total Estimated Spend (USD)", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Ad Count vs. Total Spend — Top 40 Sponsors\n"
                 "(Bubble size ∝ total spend; top 10 labelled)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_comma))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar))
    fig.tight_layout()
    _save(fig, "spend_vs_adcount_scatter.png")


# ===========================================================================
# MAIN
# ===========================================================================
def create_visualizations() -> bool:
    """Generate all 10 charts. Returns True on success."""

    if not GROUPED_PATH.exists():
        print(f"\n[visualizations] ERROR: {GROUPED_PATH} not found. Run Step 4 first.")
        return False

    print("\n[visualizations] Loading datasets...")
    df = pd.read_csv(GROUPED_PATH)
    print(f"  Grouped dataset : {len(df):,} rows")

    # Load raw sample for extra columns (Regions, Ad_Type, etc.)
    raw_df = None
    if RAW_SAMPLE_PATH.exists():
        raw_df = pd.read_csv(RAW_SAMPLE_PATH, low_memory=False)
        print(f"  Raw sample      : {len(raw_df):,} rows  ({raw_df.shape[1]} columns)")
    else:
        print(f"  Raw sample not found — charts needing extra columns will be skipped.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Output folder   : {OUTPUT_DIR.resolve()}\n")
    print("[visualizations] Generating 10 charts...\n")

    print("  [1/10] Top Sponsors by Ad Count")
    _chart_top_sponsors_count(df)

    print("  [2/10] Top Sponsors by Total Spend")
    _chart_top_sponsors_spend(df)

    print("  [3/10] Spend Distribution")
    _chart_spend_distribution(df)

    print("  [4/10] Monthly Ad Volume")
    _chart_monthly_volume(df)

    print("  [5/10] Monthly Spend Trend")
    _chart_monthly_spend(df)

    if raw_df is not None:
        print("  [6/10] Geographic Distribution")
        _chart_geographic(raw_df)

        print("  [7/10] Ad Type Distribution")
        _chart_ad_type(raw_df)
    else:
        print("  [6/10] Geographic Distribution — SKIPPED (no raw sample)")
        print("  [7/10] Ad Type Distribution   — SKIPPED (no raw sample)")

    print("  [8/10] Campaign Duration Distribution")
    _chart_campaign_duration(df)

    print("  [9/10] Sponsor Name Cleaning Impact")
    _chart_cleaning_impact(df)

    print("  [10/10] Spend vs Ad Count Scatter")
    _chart_spend_vs_count_scatter(df)

    print(f"\n[visualizations] All charts saved to {OUTPUT_DIR.resolve()}\n")
    return True


if __name__ == "__main__":
    ok = create_visualizations()
    if ok:
        print("Done. Open outputs/figures/ to view all charts.")
