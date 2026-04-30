"""
fetch_meta_api.py
-----------------
Step 8A (v2): Fetch Meta political ads via the Ad Library API.

This replaces the CSV-based approach with true per-ad data matching
Google's ad-creative-level schema exactly.

How it works:
    - Calls the Meta Ad Library API (ads_archive endpoint)
    - Fetches US political and issue ads in pages of 100
    - Collects TARGET_ADS records with the same fields as Google
    - Saves raw JSON responses + a standardized CSV ready for the pipeline

Output:
    data/raw/meta_ads_api_raw.csv         (raw API fields)
    data/processed/meta_ads_standardized.csv  (same schema as Google)

Usage:
    # Pass token as argument
    python src/data_collection/fetch_meta_api.py --token YOUR_ACCESS_TOKEN

    # Or set environment variable first
    set META_ACCESS_TOKEN=YOUR_ACCESS_TOKEN
    python src/data_collection/fetch_meta_api.py

IMPORTANT:
    Never commit your access token to git.
    Add data/raw/meta_ads_api_raw.csv to .gitignore (already there).
"""

import argparse
import os
import sys
import time
import pandas as pd
import requests
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
API_VERSION  = "v22.0"
BASE_URL     = f"https://graph.facebook.com/{API_VERSION}/ads_archive"
TARGET_ADS   = 50_000      # match Google sample size exactly
PAGE_SIZE    = 100         # max the API allows per request
SLEEP_SEC    = 0.4         # polite delay between requests
RETRY_WAIT   = 65          # seconds to wait after HTTP 429
MAX_RETRIES  = 5
SAVE_EVERY   = 2_000       # checkpoint save every N ads

# Time-stratified sampling: split 2018-Q2 → 2026-Q2 into quarters.
# Each quarter gets an equal share of the target (same idea as Google's
# 5%-per-chunk approach — ensures the sample is representative over time,
# not just the most recent or most indexed ads).
SAMPLE_START = "2018-05-07"   # Meta Ad Library earliest allowed date
SAMPLE_END   = "2026-04-26"   # today

RAW_OUT_PATH = Path("data/raw/meta_ads_api_raw.csv")
STD_OUT_PATH = Path("data/processed/meta_ads_standardized.csv")

FIELDS = ",".join([
    "id",
    "page_name",
    "ad_creative_bodies",
    "ad_delivery_start_time",
    "ad_delivery_stop_time",
    "spend",
    "impressions",
    "currency",
])


def _build_quarters(start: str, end: str) -> list[tuple[str, str]]:
    """
    Build a list of (window_start, window_end) quarterly date strings
    covering the full date range. Each quarter becomes one stratum.
    """
    from datetime import date, timedelta

    quarters = []
    current  = date.fromisoformat(start)
    finish   = date.fromisoformat(end)

    while current < finish:
        # Advance by ~91 days (one quarter)
        next_q = date(
            current.year + (current.month + 2) // 12,
            (current.month + 2) % 12 + 1,
            1,
        )
        window_end = min(next_q - timedelta(days=1), finish)
        quarters.append((current.isoformat(), window_end.isoformat()))
        current = next_q

    return quarters




# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------

def _progress(collected: int, target: int, page: int, start_t: float) -> None:
    """Print live progress bar with ETA."""
    pct    = collected / target
    filled = int(40 * pct)
    bar    = "\u2588" * filled + "\u2591" * (40 - filled)
    elapsed = time.time() - start_t
    eta     = (elapsed / pct - elapsed) if pct > 0 else 0
    eta_str = f"{int(eta // 60)}m {int(eta % 60)}s" if eta > 60 else f"{int(eta)}s"
    sys.stdout.write(
        f"\r  [{bar}] {pct*100:5.1f}%  "
        f"{collected:,}/{target:,} ads  "
        f"page {page:,}  ETA {eta_str}   "
    )
    sys.stdout.flush()


def _flatten_ad(ad: dict) -> dict:
    """
    Convert one API ad object into a flat dict with our standardized columns.
    Matches the schema used by the Google pipeline.
    """
    spend       = ad.get("spend") or {}
    impressions = ad.get("impressions") or {}
    bodies      = ad.get("ad_creative_bodies") or []

    return {
        "platform":          "Meta",
        "ad_id":             ad.get("id"),
        "sponsor_name":      ad.get("page_name"),
        "ad_text":           (bodies[0][:500] if bodies else ""),
        "start_date":        ad.get("ad_delivery_start_time"),
        "end_date":          ad.get("ad_delivery_stop_time"),
        "spend_lower":       spend.get("lower_bound"),
        "spend_upper":       spend.get("upper_bound"),
        "impressions_lower": impressions.get("lower_bound"),
        "impressions_upper": impressions.get("upper_bound"),
        "currency":          ad.get("currency", "USD"),
        "raw_source":        "meta_ad_library_api",
    }


def fetch_meta_ads(access_token: str) -> pd.DataFrame | None:
    """
    Collect TARGET_ADS political ads via sequential API paging.

    Uses the exact parameter format confirmed working in the Meta Graph
    API Explorer. Date range filtering is intentionally omitted — the
    ads_archive endpoint does not support it reliably and causes server
    errors. The API returns a broad mix of political ads across its
    history, giving adequate coverage for our analysis.
    """
    BASE_PARAMS = {
        "access_token":         access_token,
        "ad_type":              "POLITICAL_AND_ISSUE_ADS",
        "ad_reached_countries": "['US']",   # single-quote format (confirmed working)
        "fields":               FIELDS,
        "limit":                PAGE_SIZE,
        "search_terms":         "election", # broad political term (proven to work)
    }

    print(f"\n[meta_api] Fetching {TARGET_ADS:,} US political ads...")
    print(f"  Endpoint    : {BASE_URL}")
    print(f"  search_terms: 'election'")
    print(f"  ad_type     : POLITICAL_AND_ISSUE_ADS")
    print(f"  countries   : US\n")

    RAW_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STD_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    records      = []
    page_num     = 0
    after_cursor = None
    start_t      = time.time()

    while len(records) < TARGET_ADS:
        params = dict(BASE_PARAMS)
        if after_cursor:
            params["after"] = after_cursor

        response = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(BASE_URL, params=params, timeout=30)

                if response.status_code == 429:
                    print(f"\n  [rate limit] Waiting {RETRY_WAIT}s...")
                    time.sleep(RETRY_WAIT)
                    continue

                if response.status_code == 400:
                    err          = response.json().get("error", {})
                    err_code     = err.get("code")
                    is_transient = err.get("is_transient", False)
                    if is_transient or err_code == 2:
                        wait = 15 if attempt == 1 else RETRY_WAIT
                        print(f"\n  [transient] Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})...")
                        time.sleep(wait)
                        continue
                    print(f"\n  [API 400] {err.get('message')}")
                    print(f"  Code: {err_code}  |  Full: {response.text[:300]}")
                    return _save_and_return(records, start_t)

                response.raise_for_status()
                break

            except requests.Timeout:
                print(f"\n  [timeout] attempt {attempt}/{MAX_RETRIES}")
                time.sleep(5)
            except requests.RequestException as exc:
                print(f"\n  [error] {exc}")
                return _save_and_return(records, start_t)

        if response is None or not response.ok:
            break

        data = response.json()
        ads  = data.get("data", [])
        if not ads:
            print("\n  No more ads available.")
            break

        for ad in ads:
            records.append(_flatten_ad(ad))
            if len(records) >= TARGET_ADS:
                break

        page_num    += 1
        after_cursor = data.get("paging", {}).get("cursors", {}).get("after")

        # Live progress
        pct    = len(records) / TARGET_ADS
        filled = int(40 * pct)
        bar    = "\u2588" * filled + "\u2591" * (40 - filled)
        elapsed = time.time() - start_t
        eta     = (elapsed / pct - elapsed) if pct > 0 else 0
        eta_str = f"{int(eta // 60)}m {int(eta % 60)}s" if eta > 60 else f"{int(eta)}s"
        sys.stdout.write(
            f"\r  [{bar}] {pct*100:5.1f}%  "
            f"{len(records):,}/{TARGET_ADS:,}  page {page_num}  ETA {eta_str}   "
        )
        sys.stdout.flush()

        if len(records) % SAVE_EVERY < PAGE_SIZE:
            _checkpoint(records)

        if not after_cursor or "next" not in data.get("paging", {}):
            print(f"\n\n  Reached end of available data after {page_num} pages.")
            break

        time.sleep(SLEEP_SEC)

    print()
    return _save_and_return(records, start_t)

# ---------------------------------------------------------------------------
# SAVE HELPERS
# ---------------------------------------------------------------------------


def _checkpoint(records: list) -> None:
    """Save intermediate progress so the run can be inspected if it crashes."""
    df = pd.DataFrame(records)
    df.to_csv(RAW_OUT_PATH, index=False)


def _save_and_return(records: list, start_t: float) -> pd.DataFrame | None:
    """Save raw + standardized outputs and print a summary."""
    if not records:
        print("[meta_api] No records collected.")
        return None

    df = pd.DataFrame(records)

    # ---- Save raw ----
    df.to_csv(RAW_OUT_PATH, index=False)

    # ---- Save standardized (drop Meta-only columns to match Google schema) ----
    std_cols = [
        "platform", "ad_id", "sponsor_name", "ad_text",
        "start_date", "end_date",
        "spend_lower", "spend_upper",
        "impressions_lower", "impressions_upper",
        "raw_source",
    ]
    std_df = df[std_cols].copy()

    # Parse numeric fields (API returns strings for spend/impressions)
    for col in ("spend_lower", "spend_upper", "impressions_lower", "impressions_upper"):
        std_df[col] = pd.to_numeric(std_df[col], errors="coerce")

    std_df.to_csv(STD_OUT_PATH, index=False)

    elapsed = time.time() - start_t
    print(f"\n[meta_api] Done in {int(elapsed // 60)}m {int(elapsed % 60)}s")
    print(f"  Ads collected       : {len(df):,}")
    print(f"  Unique sponsors     : {df['sponsor_name'].nunique():,}")
    print(f"  Raw CSV             : {RAW_OUT_PATH.resolve()}")
    print(f"  Standardized CSV    : {STD_OUT_PATH.resolve()}")
    print(f"\n  Sample of top sponsors:")
    top = df["sponsor_name"].value_counts().head(10)
    for name, count in top.items():
        print(f"    {count:>6,}  {name}")

    print(f"\nNext: python src/data_collection/run_meta_pipeline.py")
    return std_df


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch Meta political ads via Ad Library API"
    )
    parser.add_argument(
        "--token",
        help="Meta user access token (or set META_ACCESS_TOKEN env var)",
        default=None,
    )
    args = parser.parse_args()

    # Resolve token: argument > environment variable
    token = args.token or os.environ.get("META_ACCESS_TOKEN")
    if not token:
        print("\n[meta_api] ERROR: No access token provided.")
        print("  Option 1: python fetch_meta_api.py --token YOUR_TOKEN")
        print("  Option 2: set META_ACCESS_TOKEN=YOUR_TOKEN  (then re-run)")
        sys.exit(1)

    # Quick token validation
    print("[meta_api] Validating access token...")
    test = requests.get(
        f"https://graph.facebook.com/{API_VERSION}/me",
        params={"access_token": token},
        timeout=10,
    )
    if test.status_code != 200:
        err = test.json().get("error", {})
        print(f"  Token invalid: {err.get('message', test.text)}")
        sys.exit(1)
    user = test.json()
    print(f"  Token valid — authenticated as: {user.get('name', user.get('id'))}\n")

    fetch_meta_ads(token)


if __name__ == "__main__":
    main()
