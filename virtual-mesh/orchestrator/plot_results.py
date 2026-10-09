#!/usr/bin/env python3

import glob
import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_comparison_plot():
    csv_files = glob.glob("TQ_EXPS/TQ_EXP_loss*.csv")
    if not csv_files:
        print("[ERROR] No files found matching 'TQ_EXPS/TQ_EXP_loss*.csv")
        return
    
    plt.figure(figsize=(10,5))

    for file in sorted(csv_files):
        df =pd.read_csv(file)
        #extract the run name for the chart legend
        run_label = os.path.basename(file).replace("TQ_EXP_", "").replace(".csv", "")
        plt.plot(df["time_s"], df["TQ"], label=f"Run: {run_label}")

    plt.title("batman-adv Transmit Quality (TQ) Comparison")
    plt.xlabel("Elapsed Time (seconds)")
    plt.ylabel("Transmit Quality (TQ/255)")
    plt.ylim(0, 270)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="lower left")

    output_img = "TQ_EXPS/TQ_Comparison_Plot.png"
    plt.tight_layout()
    plt.savefig(output_img)
    print(f"[SUCCESS] Plot saved to {output_img}")

if __name__ == "__main__":
    generate_comparison_plot()