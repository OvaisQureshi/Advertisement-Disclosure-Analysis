import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def generate_metrics_infographic():
    fig, ax = plt.subplots(figsize=(13, 7), facecolor='#1A202C')
    ax.axis('off')
    
    plt.text(0.5, 0.9, "The Copy-Paste Ring: Proof of Hidden Aliases on Meta", 
             ha='center', va='center', color='white', fontsize=22, weight='bold')
    plt.text(0.5, 0.83, "(Based on exact 100% character-for-character text matching in our 50,000 ad sample)", 
             ha='center', va='center', color='#A0AEC0', fontsize=12, style='italic')

    metrics = [
        # 61 / 16363 unique long paragraphs
        {"value": "61", "sub": "(0.4% of unique text)", "label": "Identical\nParagraphs\nFound", "color": "#E53E3E"},
        
        # 80 / 6724 total sponsors
        {"value": "80", "sub": "(1.2% of all sponsors)", "label": "Different Sponsors\nCaught Sharing", "color": "#D69E2E"},
        
        {"value": "8", "sub": "(Sponsors sharing 1 text)", "label": "Most Aliases\nFor One Paragraph", "color": "#38A169"},
        
        # 1079 / 50000 total ads
        {"value": "1,079", "sub": "(2.2% of all ads)", "label": "Total Ads Using\nShared Text", "color": "#3182CE"}
    ]
    
    x_positions = [0.15, 0.38, 0.62, 0.85]
    
    for i, m in enumerate(metrics):
        rect = patches.FancyBboxPatch(
            (x_positions[i] - 0.1, 0.38), 0.2, 0.35,
            boxstyle="round,pad=0.03", edgecolor=m['color'], facecolor='#2D3748', lw=3
        )
        ax.add_patch(rect)
        
        plt.text(x_positions[i], 0.62, m['value'], ha='center', va='center', 
                 color=m['color'], fontsize=36, weight='bold')
                 
        plt.text(x_positions[i], 0.55, m['sub'], ha='center', va='center', 
                 color='#A0AEC0', fontsize=11, weight='bold')
        
        plt.text(x_positions[i], 0.46, m['label'], ha='center', va='center', 
                 color='white', fontsize=14, weight='bold')

    g_note_title = "WHAT ABOUT GOOGLE?"
    g_note_text = ("Unlike Meta, Google completely hides the plaintext of their ads in the transparency database,\n"
                   "preventing researchers from ever scanning for these coordinated copy-paste networks.")
    
    note_box = patches.FancyBboxPatch(
        (0.1, 0.08), 0.8, 0.18,
        boxstyle="round,pad=0.03", edgecolor='#718096', facecolor='#2D3748', lw=2
    )
    ax.add_patch(note_box)
    
    plt.text(0.5, 0.2, g_note_title, ha='center', va='center', color='#FFFFFF', fontsize=14, weight='bold')
    plt.text(0.5, 0.13, g_note_text, ha='center', va='center', color='#E2E8F0', fontsize=12, linespacing=1.5)

    os.makedirs("outputs/figures", exist_ok=True)
    plt.tight_layout()
    plt.savefig("outputs/figures/alias_frequency_metrics.png", dpi=300, bbox_inches='tight', facecolor='#1A202C')
    plt.close()
    
    print("Saved infographic to outputs/figures/alias_frequency_metrics.png")

if __name__ == "__main__":
    generate_metrics_infographic()
