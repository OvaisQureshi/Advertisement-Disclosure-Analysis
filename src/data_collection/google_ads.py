"""
google_ads.py
-------------
Placeholder module for fetching political ad data from the
Google Political Ads Transparency Report.
"""

import os
import pandas as pd


def fetch_google_ads() -> list[dict]:
    """
    Fetch political ad records from the Google Political Ads Transparency Report.

    Currently returns a single placeholder record. Replace the `records` list
    with real data from the Google BigQuery public dataset or downloadable CSVs
    when access is configured.

    Returns:
        list[dict]: A list of ad records, each represented as a dictionary.
    """
    # --- Placeholder data (replace with real data source) ---
    records = [
        {
            "platform": "Google",
            "sponsor_name": "America Forward PAC",
            "ad_text": (
                "Protect our values. Support candidates who stand up for "
                "hardworking Americans. Paid for by America Forward PAC."
            ),
        }
    ]
    # --------------------------------------------------------

    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Ensure output directory exists
    output_dir = os.path.join("data", "raw")
    os.makedirs(output_dir, exist_ok=True)

    # Save to CSV
    output_path = os.path.join(output_dir, "google_ads.csv")
    df.to_csv(output_path, index=False)
    print(f"      [google_ads] Saved {len(records)} record(s) to '{output_path}'.")

    return records
