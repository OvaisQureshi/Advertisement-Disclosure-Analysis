# Political Ad Disclosure Analysis

## Overview

This project builds a pipeline to **collect, clean, combine, and analyze** political advertising transparency data from two major platforms:

- **Meta (Facebook/Instagram)** — via the Meta Ad Library
- **Google** — via the Google Political Ads Transparency Report

## Goals

1. **Collect** raw ad disclosure data from Meta and Google public APIs/datasets.
2. **Preprocess** the data by cleaning, normalizing, and standardizing fields across platforms.
3. **Combine** datasets into a unified format for cross-platform comparison.
4. **Analyze** trends in political advertising — including spend, targeting, sponsors, and messaging.

## Project Structure

```
ad-disclosure-analysis/
├── data/
│   ├── raw/           # Raw data as collected from sources
│   └── processed/     # Cleaned and combined data
├── src/
│   ├── data_collection/
│   │   ├── meta_ads.py      # Meta Ad Library data fetcher
│   │   └── google_ads.py    # Google Ads Transparency data fetcher
│   ├── preprocessing/       # Data cleaning and normalization
│   └── analysis/            # Analysis and visualization scripts
├── notebooks/               # Jupyter notebooks for exploration
├── main.py                  # Pipeline entry point
└── requirements.txt
```

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the pipeline

```bash
python main.py
```

This will fetch ad records from both platforms and save them to:
- `data/raw/meta_ads.csv`
- `data/raw/google_ads.csv`

## Requirements

- Python 3.8+
- See `requirements.txt` for Python package dependencies
