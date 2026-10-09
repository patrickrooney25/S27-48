#!/usr/bin/env python3

import glob
import pandas as pd
import matplotlib.pyplot as plt
import os
from matplotlib.lines import Line2D

def generate_comparison_plot():
    csv_files = glob.glob("TQ_EXPS/TQ_EXP_loss*.csv")
    if not csv_files:
        print("[ERROR] No files found matching 'TQ_EXPS/TQ_EXP_loss*.csv")
        return
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

    for file in sorted(csv_files):
        df = pd.read_csv(file)
        run_label = os.path.basename(file).replace("TQ_EXP_loss", "").replace(".csv", "")
        
        # 1. Plot TQ Metrics
        line, = ax1.plot(df["time_s"], df["TQ"], label=f"{run_label}% loss")

        # 2. Add On/Off Scatter Markers Safely
        on_rows = df[df["loss_pct"] > 0]
        if not on_rows.empty:
            on_row = on_rows.iloc[0]
            ax1.scatter(on_row["time_s"], on_row["TQ"], s=90, color=line.get_color(), zorder=3)
            
            off_rows = df[(df["time_s"] > on_row["time_s"]) & (df["loss_pct"] == 0)]
            if not off_rows.empty:
                off_row = off_rows.iloc[0]
                ax1.scatter(off_row["time_s"], off_row["TQ"], s=90, facecolors="white", edgecolors=line.get_color(), linewidths=2, zorder=3)

        # 3. Plot Interface Rerouting (0 = Direct veth1-2, 1 = Backup veth1-3 via vnode3)
        if "outgoing_if" in df.columns:
            if_numeric = df["outgoing_if"].apply(lambda x: 1 if "1-3" in str(x) else 0)
            ax2.step(df["time_s"], if_numeric, where="mid", alpha=0.8, label=f"{run_label}% Loss")

    # Construct legend handles outside the loop to avoid duplicate entries
    handles, labels = ax1.get_legend_handles_labels()
    handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor="black", markeredgecolor="black", markersize=9))
    labels.append("Loss applied")
    handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor="black", markeredgewidth=2, markersize=9))
    labels.append("Loss cleared")

    # Formatting Top Plot (TQ)
    ax1.set_title("batman-adv Transmit Quality (TQ) & Reroute Comparison")
    ax1.set_ylabel("Transmit Quality (TQ/255)")
    ax1.set_ylim(-10, 270)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(handles, labels, loc="lower left")

    # Formatting Bottom Plot (Interface Switch)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["veth1-2 (Direct)", "veth1-3 (vnode3 Relay)"])
    ax2.set_xlabel("Elapsed Time (seconds)")
    ax2.set_ylabel("Active Interface")
    ax2.grid(True, linestyle=":", alpha=0.6)

    output_img = "TQ_EXPS/TQ_Comparison_Plot.png"
    plt.tight_layout()
    plt.savefig(output_img)
    print(f"[SUCCESS] Plot saved to {output_img}")

if __name__ == "__main__":
    generate_comparison_plot()