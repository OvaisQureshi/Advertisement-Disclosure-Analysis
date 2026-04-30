import matplotlib.pyplot as plt
import matplotlib.patches as patches
import networkx as nx
import os
import textwrap

def generate_coordination_graphic():
    # Setup figure
    fig, ax = plt.subplots(figsize=(14, 8), facecolor='#1E1E1E')
    ax.set_facecolor('#1E1E1E')
    
    # Ad Text Data
    ad_text = (
        "It's not about us, it's about the future of progressive politics. "
        "Alexandria, Ayanna, Ilhan, and Rashida have spent their careers paving "
        "the way for the progressive movement in Congress. This election cycle, "
        "our movement is under attack... We have to work together to keep Re[...]"
    )
    wrapped_text = "\n".join(textwrap.wrap(ad_text, width=45))
    
    # Draw central Ad Text box
    box_width = 0.4
    box_height = 0.35
    center_x = 0.5
    center_y = 0.5
    
    rect = patches.FancyBboxPatch(
        (center_x - box_width/2, center_y - box_height/2),
        box_width, box_height,
        boxstyle="round,pad=0.05",
        edgecolor='#F2C94C', facecolor='#333333', lw=3
    )
    ax.add_patch(rect)
    
    plt.text(
        center_x, center_y,
        f"EXACT MATCHING AD COPY\nDeployed Simultaneously\n{"-"*30}\n\n{wrapped_text}",
        ha='center', va='center', color='white', fontsize=12, fontweight='bold',
        zorder=10
    )

    # Sponsors and their deployment details
    sponsors = [
        {"name": "Alexandria Ocasio-Cortez", "date": "Launched: April 3", "spend": "Est. Spend: $3,200", "loc": (0.15, 0.8)},
        {"name": "Ilhan Omar", "date": "Launched: April 3", "spend": "Est. Spend: $1,600", "loc": (0.85, 0.8)},
        {"name": "Ayanna Pressley", "date": "Launched: April 3", "spend": "Est. Spend: $397", "loc": (0.15, 0.2)},
        {"name": "Rashida Tlaib", "date": "Launched: April 3", "spend": "Est. Spend: $198", "loc": (0.85, 0.2)}
    ]

    for sp in sponsors:
        # Draw Sponsor boxes
        sp_rect = patches.FancyBboxPatch(
            (sp['loc'][0] - 0.12, sp['loc'][1] - 0.1),
            0.24, 0.2,
            boxstyle="round,pad=0.02",
            edgecolor='#56CCF2', facecolor='#2B3A4A', lw=2
        )
        ax.add_patch(sp_rect)
        
        # Add Sponsor Text
        plt.text(
            sp['loc'][0], sp['loc'][1] + 0.05,
            f"DISCLAIMER:\n{sp['name']}",
            ha='center', va='center', color='#56CCF2', fontsize=11, fontweight='bold', zorder=10
        )
        plt.text(
            sp['loc'][0], sp['loc'][1] - 0.03,
            f"{sp['date']}",
            ha='center', va='center', color='#FFFFFF', fontsize=10, zorder=10
        )
        plt.text(
            sp['loc'][0], sp['loc'][1] - 0.08,
            f"{sp['spend']}",
            ha='center', va='center', color='#E0E0E0', fontsize=10, fontstyle='italic', zorder=10
        )
        
        # Determine connection points (edge of central box to edge of sponsor box)
        if sp['loc'][0] < center_x: # left side
            x_start = center_x - box_width/2 - 0.05
            x_end = sp['loc'][0] + 0.12
        else: # right side
            x_start = center_x + box_width/2 + 0.05
            x_end = sp['loc'][0] - 0.12
            
        y_start = center_y
        y_end = sp['loc'][1]
        
        # Draw Connecting Arrows
        plt.annotate(
            "",
            xy=(x_start, y_start), xycoords='data',
            xytext=(x_end, y_end), textcoords='data',
            arrowprops=dict(arrowstyle="<|-", color="#F2C94C", lw=3, shrinkA=0, shrinkB=0,
                            connectionstyle=f"angle3,angleA=0,angleB=90")
        )

    plt.title("Forensic Coordination: Exposing Shared Campaigns Across Independent Sponsors via Meta's Ad_Text", 
              fontsize=16, weight='bold', color='white', pad=20)
    
    # Bottom Note
    plt.figtext(0.5, 0.03, "KEY FINDING: Although these are four legally distinct financial entities, the identical copy and synchronized deploy date prove operational coordination.", 
                ha="center", fontsize=12, weight='bold', color='#EB5757')

    # Formatting cleanup
    plt.axis('off')
    plt.xlim(0, 1)
    plt.ylim(0, 1)

    os.makedirs("outputs/figures", exist_ok=True)
    plt.tight_layout()
    plt.savefig("outputs/figures/sponsor_coordination_example.png", dpi=300, facecolor='#1E1E1E')
    plt.close()
    
    print("Saved coordination map to outputs/figures/sponsor_coordination_example.png")

if __name__ == "__main__":
    generate_coordination_graphic()
