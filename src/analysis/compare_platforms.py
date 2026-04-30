"""
compare_platforms.py
--------------------
Step 8C of the Political Ad Disclosure Analysis Pipeline.

Compares Google and Meta political ad datasets side-by-side and produces:
  - A terminal comparison table
  - data/processed/cross_platform_summary.json
  - outputs/figures/comparison_*.png  (3 comparison charts)

Requires both pipelines to have been run:
  data/processed/google_ads_grouped.csv
  data/processed/meta_ads_grouped.csv

Usage:
    python src/analysis/compare_platforms.py
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
GOOGLE_PATH   = Path("data/processed/google_ads_grouped.csv")
META_PATH     = Path("data/processed/meta_ads_grouped.csv")
OUTPUT_JSON   = Path("data/processed/cross_platform_summary.json")
FIGURES_DIR   = Path("outputs/figures")

# ---------------------------------------------------------------------------
# SHARED DARK STYLE
# ---------------------------------------------------------------------------
BACKGROUND = "#0f1117"
AXES_BG    = "#1c1f2b"
TEXT       = "#e8eaf0"
BLUE       = "#4f8ef7"    # Google color
PURPLE     = "#a78bfa"    # Meta color
TEAL       = "#34d399"
ORANGE     = "#f59e0b"
GRID       = "#2a2d3a"
DPI        = 180
TITLE_FS   = 14
LABEL_FS   = 11
TICK_FS    = 9


def _style(fig, ax):
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


def _save(fig, name):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [saved] {path}")


def _dollar(x, _):
    return f"${int(x):,}"


def _comma(x, _):
    return f"{int(x):,}"


# ===========================================================================
# COMPUTE METRICS
# ===========================================================================

def _platform_metrics(df: pd.DataFrame, name: str) -> dict:
    """Compute comparable metrics for one platform's grouped DataFrame."""
    valid = df[df["sponsor_group_id"] >= 0]

    spend_lower = pd.to_numeric(df["spend_lower"], errors="coerce")
    spend_upper = pd.to_numeric(df["spend_upper"], errors="coerce")
    avg_spend   = (spend_lower + spend_upper) / 2

    df2 = df.copy()
    df2["start_date"] = pd.to_datetime(df2["start_date"], errors="coerce")
    df2["end_date"]   = pd.to_datetime(df2["end_date"],   errors="coerce")
    duration = (df2["end_date"] - df2["start_date"]).dt.days

    top5 = (valid.groupby("canonical_sponsor_name").size()
            .sort_values(ascending=False).head(5).to_dict())

    return {
        "platform":              name,
        "total_ads":             int(len(df)),
        "unique_raw_sponsors":   int(df["sponsor_name"].nunique()),
        "unique_clean_sponsors": int(df["clean_sponsor_name"].nunique()),
        "unique_sponsor_groups": int(valid["sponsor_group_id"].nunique()),
        "normalization_reduction_pct": round(
            (df["sponsor_name"].nunique() - valid["sponsor_group_id"].nunique())
            / df["sponsor_name"].nunique() * 100, 1),
        "mean_avg_spend":     round(float(avg_spend.mean()), 2) if avg_spend.notna().any() else 0,
        "median_avg_spend":   round(float(avg_spend.median()), 2) if avg_spend.notna().any() else 0,
        "total_estimated_spend": round(float(avg_spend.sum()), 2) if avg_spend.notna().any() else 0,
        "median_campaign_days":  round(float(duration.median()), 1) if duration.notna().any() else None,
        "top5_sponsors_by_count": top5,
        "date_range": {
            "start": str(df2["start_date"].min().date()) if df2["start_date"].notna().any() else "N/A",
            "end":   str(df2["start_date"].max().date()) if df2["start_date"].notna().any() else "N/A",
        },
    }


# ===========================================================================
# CHART 1 — Side-by-side overview metrics bar chart
# ===========================================================================

def _chart_overview(g: dict, m: dict) -> None:
    """Grouped bar chart comparing key counts between platforms."""
    metrics = {
        "Total Ads\n(sample)":         [g["total_ads"],             m["total_ads"]],
        "Unique Raw\nSponsors":         [g["unique_raw_sponsors"],   m["unique_raw_sponsors"]],
        "Unique Sponsor\nGroups":       [g["unique_sponsor_groups"], m["unique_sponsor_groups"]],
    }

    labels  = list(metrics.keys())
    g_vals  = [v[0] for v in metrics.values()]
    m_vals  = [v[1] for v in metrics.values()]
    x       = np.arange(len(labels))
    width   = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    _style(fig, ax)

    bars_g = ax.bar(x - width / 2, g_vals, width, label="Google", color=BLUE,  edgecolor="none")
    bars_m = ax.bar(x + width / 2, m_vals, width, label="Meta",   color=PURPLE, edgecolor="none")

    for bar in list(bars_g) + list(bars_m):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(g_vals + m_vals) * 0.01,
                f"{int(bar.get_height()):,}",
                ha="center", va="bottom", color=TEXT, fontsize=TICK_FS)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=TICK_FS)
    ax.set_ylabel("Count", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Google vs Meta — Dataset Overview\n(Ad Count, Unique Sponsors, Sponsor Groups)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_comma))

    legend = ax.legend(fontsize=TICK_FS, facecolor=AXES_BG,
                       edgecolor=GRID, labelcolor=TEXT)

    fig.tight_layout()
    _save(fig, "comparison_overview.png")


# ===========================================================================
# CHART 2 — Spend comparison
# ===========================================================================

def _chart_spend(g: dict, m: dict) -> None:
    """Grouped bar chart comparing spend metrics."""
    metrics = {
        "Mean Spend\nper Ad":   [g["mean_avg_spend"],   m["mean_avg_spend"]],
        "Median Spend\nper Ad": [g["median_avg_spend"], m["median_avg_spend"]],
    }

    labels = list(metrics.keys())
    g_vals = [v[0] for v in metrics.values()]
    m_vals = [v[1] for v in metrics.values()]
    x      = np.arange(len(labels))
    width  = 0.35

    fig, ax = plt.subplots(figsize=(8, 6))
    _style(fig, ax)

    bars_g = ax.bar(x - width / 2, g_vals, width, label="Google", color=BLUE,  edgecolor="none")
    bars_m = ax.bar(x + width / 2, m_vals, width, label="Meta",   color=PURPLE, edgecolor="none")

    all_vals = g_vals + m_vals
    for bar in list(bars_g) + list(bars_m):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(all_vals) * 0.015,
                f"${int(bar.get_height()):,}",
                ha="center", va="bottom", color=TEXT, fontsize=TICK_FS)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=TICK_FS)
    ax.set_ylabel("USD", fontsize=LABEL_FS, labelpad=10)
    ax.set_title("Google vs Meta — Estimated Spend per Ad\n"
                 "(Mean and Median USD, based on reported ranges)",
                 fontsize=TITLE_FS, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar))
    ax.legend(fontsize=TICK_FS, facecolor=AXES_BG, edgecolor=GRID, labelcolor=TEXT)

    fig.tight_layout()
    _save(fig, "comparison_spend.png")


# ===========================================================================
# CHART 3 — Normalization impact side-by-side
# ===========================================================================

def _chart_normalization(g: dict, m: dict) -> None:
    """
    Side-by-side 3-bar chart showing Raw -> Cleaned -> Grouped for each platform.
    Illustrates how much naming inconsistency exists per platform.
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    fig.patch.set_facecolor(BACKGROUND)
    fig.suptitle("Sponsor Name Normalization Impact: Google vs Meta\n"
                 "(Raw  →  Cleaned  →  Fuzzy Grouped)",
                 color=TEXT, fontsize=TITLE_FS, fontweight="bold", y=1.02)

    for ax, data, color, platform in [
        (axes[0], g, BLUE,   "Google"),
        (axes[1], m, PURPLE, "Meta"),
    ]:
        _style(fig, ax)
        vals   = [data["unique_raw_sponsors"],
                  data["unique_clean_sponsors"],
                  data["unique_sponsor_groups"]]
        labels = ["Raw\nNames", "Cleaned\nNames", "Grouped"]
        bars   = ax.bar(labels, vals, color=color, edgecolor="none", width=0.5)

        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(vals) * 0.015,
                    f"{v:,}", ha="center", va="bottom",
                    color=TEXT, fontsize=TICK_FS, fontweight="bold")

        ax.set_title(platform, color=TEXT, fontsize=LABEL_FS, fontweight="bold")
        ax.set_ylim(0, max(vals) * 1.2)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_comma))
        ax.tick_params(axis="x", length=0)

        # Reduction % annotation
        reduction = data["normalization_reduction_pct"]
        ax.annotate(f"Overall reduction:\n{reduction}%",
                    xy=(0.97, 0.97), xycoords="axes fraction",
                    ha="right", va="top",
                    color=ORANGE, fontsize=TICK_FS,
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor=AXES_BG, edgecolor=GRID))

    fig.tight_layout()
    _save(fig, "comparison_normalization.png")


# ===========================================================================
# TERMINAL COMPARISON TABLE
# ===========================================================================

def _print_comparison(g: dict, m: dict) -> None:
    w = 38
    print("\n" + "=" * 70)
    print("  CROSS-PLATFORM COMPARISON: Google vs Meta")
    print("=" * 70)
    print(f"  {'Metric':<30} {'Google':>17} {'Meta':>17}")
    print("-" * 70)

    def row(label, gv, mv, fmt="{:,}"):
        try:
            gf = fmt.format(gv) if gv is not None else "N/A"
            mf = fmt.format(mv) if mv is not None else "N/A"
        except (ValueError, TypeError):
            gf, mf = str(gv), str(mv)
        print(f"  {label:<30} {gf:>17} {mf:>17}")

    row("Total ads (sample)",         g["total_ads"],             m["total_ads"])
    row("Unique raw sponsor names",   g["unique_raw_sponsors"],   m["unique_raw_sponsors"])
    row("Unique cleaned names",        g["unique_clean_sponsors"], m["unique_clean_sponsors"])
    row("Unique sponsor groups",       g["unique_sponsor_groups"], m["unique_sponsor_groups"])
    row("Normalization reduction %",   g["normalization_reduction_pct"],
                                       m["normalization_reduction_pct"], fmt="{:.1f}%")
    row("Mean spend/ad (USD)",         g["mean_avg_spend"],        m["mean_avg_spend"],  fmt="${:,.2f}")
    row("Median spend/ad (USD)",       g["median_avg_spend"],      m["median_avg_spend"], fmt="${:,.2f}")
    row("Median campaign (days)",      g["median_campaign_days"],  m["median_campaign_days"], fmt="{:.0f}")

    print("-" * 70)
    print(f"\n  Google date range : {g['date_range']['start']} to {g['date_range']['end']}")
    print(f"  Meta   date range : {m['date_range']['start']} to {m['date_range']['end']}")

    print(f"\n  Top 5 Google sponsors (by ad count):")
    for name, cnt in list(g["top5_sponsors_by_count"].items())[:5]:
        print(f"    {cnt:>6,}  {name[:55]}")

    print(f"\n  Top 5 Meta sponsors (by ad count):")
    for name, cnt in list(m["top5_sponsors_by_count"].items())[:5]:
        print(f"    {cnt:>6,}  {name[:55]}")

    print("=" * 70 + "\n")


# ===========================================================================
# MAIN
# ===========================================================================

def compare_platforms() -> bool:
    """
    Load both grouped datasets, compute comparison metrics, print a table,
    save JSON, and generate 3 comparison charts.
    """
    missing = []
    if not GOOGLE_PATH.exists():
        missing.append(str(GOOGLE_PATH))
    if not META_PATH.exists():
        missing.append(str(META_PATH))

    if missing:
        print("\n[compare] ERROR: Missing required files:")
        for f in missing:
            print(f"  {f}")
        if str(META_PATH) in missing:
            print("\n  Run Steps 8A + 8B first:")
            print("    python src/data_collection/load_meta_ads.py")
            print("    python src/data_collection/run_meta_pipeline.py")
        return False

    print("\n[compare] Loading datasets...")
    google_df = pd.read_csv(GOOGLE_PATH, low_memory=False)
    meta_df   = pd.read_csv(META_PATH,   low_memory=False)
    print(f"  Google: {len(google_df):,} rows")
    print(f"  Meta  : {len(meta_df):,} rows")

    print("\n[compare] Computing metrics...")
    g_metrics = _platform_metrics(google_df, "Google")
    m_metrics = _platform_metrics(meta_df,   "Meta")

    # Print and save
    _print_comparison(g_metrics, m_metrics)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump({"Google": g_metrics, "Meta": m_metrics}, f, indent=2)
    print(f"[compare] JSON saved -> {OUTPUT_JSON.resolve()}")

    # Generate charts
    print("\n[compare] Generating comparison charts...")
    print("  [1/3] Overview counts")
    _chart_overview(g_metrics, m_metrics)
    print("  [2/3] Spend comparison")
    _chart_spend(g_metrics, m_metrics)
    print("  [3/3] Normalization impact")
    _chart_normalization(g_metrics, m_metrics)

    print(f"\n[compare] Done. 3 charts saved to {FIGURES_DIR.resolve()}\n")
    return True


if __name__ == "__main__":
    ok = compare_platforms()
    if ok:
        print("Cross-platform comparison complete.")
