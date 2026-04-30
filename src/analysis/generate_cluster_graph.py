import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import os

def generate_cluster_graph():
    print("[cluster_graph] Loading Meta grouped data...")
    df_m = pd.read_csv("data/processed/meta_ads_grouped.csv", low_memory=False)

    # Find canonical sponsors with multiple raw variants
    variants = df_m.groupby('canonical_sponsor_name')['sponsor_name'].unique().reset_index()
    variants['num_variants'] = variants['sponsor_name'].apply(len)
    
    # Sort to find the messiest groups
    variants = variants.sort_values('num_variants', ascending=False)
    
    # Let's pick two illustrative examples from the top that are clearly the same entity 
    # but have lots of typos/variations. (We will pick the top 2).
    examples = variants.head(2)

    plt.figure(figsize=(14, 7))
    
    for i, (_, row) in enumerate(examples.iterrows()):
        canonical = row['canonical_sponsor_name']
        raw_names = row['sponsor_name']
        
        # Limit to max 12 raw names so the graph isn't unreadable
        if len(raw_names) > 12:
            raw_names = raw_names[:12]
            
        G = nx.Graph()
        
        # Add central node
        G.add_node(canonical, type='canonical')
        
        # Add variant nodes and edges
        for name in raw_names:
            # Skip if the raw name matches canonical exactly
            if name != canonical:
                G.add_node(name, type='raw')
                G.add_edge(canonical, name)
                
        # Draw on subplot
        ax = plt.subplot(1, 2, i+1)
        
        # Spring layout works well for star graphs
        pos = nx.spring_layout(G, seed=42, k=0.5)
        
        # Draw the nodes
        canonical_nodes = [node for node, attr in G.nodes(data=True) if attr.get('type') == 'canonical']
        raw_nodes = [node for node, attr in G.nodes(data=True) if attr.get('type') == 'raw']
        
        nx.draw_networkx_nodes(G, pos, nodelist=canonical_nodes, node_color='#1877F2', node_size=3000, alpha=0.9, ax=ax)
        nx.draw_networkx_nodes(G, pos, nodelist=raw_nodes, node_color='#E4E6EB', node_size=1500, edgecolors='#8a8d91', ax=ax)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, width=2, alpha=0.5, edge_color='#8a8d91', ax=ax)
        
        # Draw labels with word wrap for readability
        labels = {}
        for node in G.nodes():
            words = str(node).split()
            # simple text wrap
            wrapped = "\n".join([" ".join(words[j:j+3]) for j in range(0, len(words), 3)])
            labels[node] = wrapped
            
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight='bold', ax=ax)
        
        ax.set_title(f"Cluster: {canonical}", fontsize=14, weight='bold', pad=20)
        ax.axis('off')

    plt.suptitle("Identity Fragmentation on Meta: Multiple Raw Names Merging into One True Identity", fontsize=18, weight='bold', y=1.05)
    
    # Save the output
    os.makedirs("outputs/figures", exist_ok=True)
    plt.tight_layout()
    plt.savefig("outputs/figures/sponsor_cluster_examples.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("\nCluster graph saved to outputs/figures/sponsor_cluster_examples.png")

if __name__ == "__main__":
    generate_cluster_graph()
