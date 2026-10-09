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
    
    plt.figure(figsize=(10,5))

    for file in sorted(csv_files):
        df =pd.read_csv(file)
        #extract the run name for the chart legend
        run_label = os.path.basename(file).replace("TQ_EXP_loss", "").replace(".csv", "")
        line, = plt.plot(df["time_s"], df["TQ"], label=f"{run_label}% loss")

        # Marks where loss is applied and unapplied
        on_row = df[df["loss_pct"] > 0].iloc[0]
        off_row = df[(df["time_s"] > on_row["time_s"]) & (df["loss_pct"] == 0)].iloc[0]

        # Filled dot = on & Open = off
        plt.scatter(on_row["time_s"], on_row["TQ"], s = 90, color = line.get_color(), zorder = 3)
        plt.scatter(off_row["time_s"], off_row["TQ"], s = 90, facecolors = "white", edgecolors = line.get_color(), linewidths = 2,zorder = 3)

        # build the key: the three lines plus one entry for each dot type
        handles, labels = plt.gca().get_legend_handles_labels()
        handles.append(Line2D([0], [0], marker = "o", color = "none", markerfacecolor = "black", markeredgecolor = "black", markersize = 9))
        labels.append("Loss applied")
        handles.append(Line2D([0], [0], marker = "o", color = "none", markerfacecolor = "white", markeredgecolor = "black", markeredgewidth = 2, markersize = 9))
        labels.append("Loss cleared")

    plt.title("batman-adv Transmit Quality (TQ) Comparison")
    plt.xlabel("Elapsed Time (seconds)")
    plt.ylabel("Transmit Quality (TQ/255)")
    plt.ylim(0, 270)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(handles, labels, loc="lower left")

    output_img = "TQ_EXPS/TQ_Comparison_Plot.png"
    plt.tight_layout()
    plt.savefig(output_img)
    print(f"[SUCCESS] Plot saved to {output_img}")

if __name__ == "__main__":
    generate_comparison_plot()