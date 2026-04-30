import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

def recluster_meta():
    print("Loading raw Meta data...")
    df = pd.read_csv("data/raw/meta_ads_api_raw.csv", low_memory=False)
    
    # 1. Basic Cleaning
    def clean_name(name):
        if pd.isna(name): return "Unknown Sponsor"
        n = str(name).lower()
        n = re.sub(r'[^a-z0-9\s]', '', n)
        n = re.sub(r'\b(inc|llc|pac|committee|for|to|elect|the)\b', '', n)
        n = re.sub(r'\s+', ' ', n).strip()
        return n if n else "Unknown Sponsor"

    df['clean_sponsor_name'] = df['sponsor_name'].apply(clean_name)
    
    # Get unique clean names
    unique_names = df['clean_sponsor_name'].unique()
    print(f"Total unique clean names: {len(unique_names)}")
    
    # 2. Fast TF-IDF Clustering
    print("Vectorizing...")
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
    X = vectorizer.fit_transform(unique_names)
    
    print("Computing cosine similarity...")
    # This is fast for 6700 names (~6700x6700 matrix)
    sim_matrix = cosine_similarity(X)
    
    # Simple connected components for high similarity threshold (0.85)
    print("Clustering...")
    threshold = 0.85
    visited = set()
    clusters = {}
    
    for i in range(len(unique_names)):
        if i in visited: continue
        
        # Find matches
        matches = np.where(sim_matrix[i] > threshold)[0]
        
        # The canonical name for this cluster will be the one with the most ad occurrences
        cluster_names = [unique_names[m] for m in matches]
        # Get actual ad counts for these
        counts = df[df['clean_sponsor_name'].isin(cluster_names)]['clean_sponsor_name'].value_counts()
        canonical = counts.idxmax() if not counts.empty else cluster_names[0]
        
        for m in matches:
            clusters[unique_names[m]] = canonical
            visited.add(m)
            
    # Map back to dataframe
    df['canonical_sponsor_name'] = df['clean_sponsor_name'].map(clusters)
    
    # Fix canonical name capitalization by grabbing the most common raw spelling of the canonical entity
    print("Restoring readable canonical names...")
    canonical_map = {}
    for canon in df['canonical_sponsor_name'].unique():
        # Get raw names that mapped to this canon
        raws = df[df['canonical_sponsor_name'] == canon]['sponsor_name']
        most_common_raw = raws.mode().iloc[0] if not raws.empty else str(canon).title()
        canonical_map[canon] = most_common_raw
        
    df['canonical_sponsor_name'] = df['canonical_sponsor_name'].map(canonical_map)
    
    # Save
    out_path = "data/processed/meta_ads_grouped_fixed.csv"
    df.to_csv(out_path, index=False)
    print(f"Re-clustered data saved to {out_path}")
    
    # Output stats
    print(f"Original Raw Names: {df['sponsor_name'].nunique()}")
    print(f"Cleaned Names: {len(unique_names)}")
    print(f"Clustered Canonical Entities: {df['canonical_sponsor_name'].nunique()}")

if __name__ == "__main__":
    recluster_meta()
