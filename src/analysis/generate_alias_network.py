import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import textwrap

def generate_alias_graphic():
    fig, ax = plt.subplots(figsize=(14, 7), facecolor='#1E1E1E')
    ax.set_facecolor('#1E1E1E')
    
    ad_text = (
        "Medicare for the Working Class means all W-2 and W-9 employees, "
        "their loved ones, and dependents get access to reliable healthcare coverage."
    )
    wrapped_text = "\n".join(textwrap.wrap(ad_text, width=45))
    
    center_x = 0.5
    center_y = 0.5
    box_width = 0.4
    box_height = 0.35
    
    # Central Ad Text Box
    rect = patches.FancyBboxPatch(
        (center_x - box_width/2, center_y - box_height/2),
        box_width, box_height,
        boxstyle="round,pad=0.05",
        edgecolor='#27AE60', facecolor='#2C3E50', lw=3
    )
    ax.add_patch(rect)
    
    plt.text(
        center_x, center_y,
        f"EXACT MATCHING AD COPY\n{"-"*30}\n\n{wrapped_text}",
        ha='center', va='center', color='white', fontsize=12, fontweight='bold', zorder=10
    )

    # Identical Entity Aliases
    sponsors = [
        {"name": "Carl Setzer For Congress", "date": "Launched: April 9", "spend": "Est. Spend: $99", "loc": (0.15, 0.5)},
        {"name": "Setzer For Congress", "date": "Launched: March 26", "spend": "Est. Spend: $99", "loc": (0.85, 0.5)}
    ]

    for sp in sponsors:
        sp_rect = patches.FancyBboxPatch(
            (sp['loc'][0] - 0.12, sp['loc'][1] - 0.1),
            0.24, 0.2,
            boxstyle="round,pad=0.02",
            edgecolor='#E2B93B', facecolor='#333333', lw=2
        )
        ax.add_patch(sp_rect)
        
        plt.text(
            sp['loc'][0], sp['loc'][1] + 0.05,
            f"DISCLAIMER ALIAS:\n{sp['name']}",
            ha='center', va='center', color='#E2B93B', fontsize=11, fontweight='bold', zorder=10
        )
        plt.text(
            sp['loc'][0], sp['loc'][1] - 0.03,
            f"{sp['date']}",
            ha='center', va='center', color='white', fontsize=10, zorder=10
        )
        plt.text(
            sp['loc'][0], sp['loc'][1] - 0.08,
            f"{sp['spend']}",
            ha='center', va='center', color='#BDBDBD', fontsize=10, fontstyle='italic', zorder=10
        )

        # Connection arrows
        if sp['loc'][0] < center_x: # left side
            x_start = center_x - box_width/2 - 0.05
            x_end = sp['loc'][0] + 0.12
        else: # right side
            x_start = center_x + box_width/2 + 0.05
            x_end = sp['loc'][0] - 0.12
            
        plt.annotate(
            "",
            xy=(x_start, center_y), xycoords='data',
            xytext=(x_end, sp['loc'][1]), textcoords='data',
            arrowprops=dict(arrowstyle="<|-", color="#27AE60", lw=3)
        )

    plt.title("Proving Identity Fragmentation: Multiple Aliases Found Deploying Identical Content", 
              fontsize=16, weight='bold', color='white', pad=20)
    
    plt.figtext(0.5, 0.05, "KEY FINDING: Meta registers these as two entirely distinct sponsors. But by tracking the exact identical ad copy, we prove they are fragments of the same true entity.", 
                ha="center", fontsize=12, weight='bold', color='#EB5757')

    plt.axis('off')
    plt.xlim(0, 1)
    plt.ylim(0, 1)

    os.makedirs("outputs/figures", exist_ok=True)
    plt.tight_layout()
    plt.savefig("outputs/figures/identity_fragmentation_example.png", dpi=300, facecolor='#1E1E1E')
    plt.close()
    
    print("Saved graphic to outputs/figures/identity_fragmentation_example.png")

if __name__ == "__main__":
    generate_alias_graphic()
