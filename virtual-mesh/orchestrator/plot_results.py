#!/usr/bin/env python3
import glob
import os
import re
import matplotlib.pyplot as plt
import pandas as pd

CSV_DIR = "TQ_EXPS"
OUTPUT_PNG = os.path.join(CSV_DIR, "TQ_Comparison_Plot.png")

BASELINE_S = 30
DEGRADE_S = 120
RECOVER_TIME = BASELINE_S + DEGRADE_S


def extract_loss_pct(filename):
    match = re.search(r"loss_(\d+)pct", filename)
    return int(match.group(1)) if match else 999


def main():
    csv_files = glob.glob(os.path.join(CSV_DIR, "tq_loss_*pct.csv"))
    if not csv_files:
        print(f"[ERROR] No CSV files found in {CSV_DIR}/ matching 'tq_loss_*pct.csv'")
        return

    csv_files.sort(key=extract_loss_pct)

    # 4 distinct loss levels -> 4 rows (1 row per test run)
    fig, axes = plt.subplots(
        nrows=len(csv_files),
        ncols=1,
        figsize=(12, 2.6 * len(csv_files)),
        sharex=True,
    )
    if len(csv_files) == 1:
        axes = [axes]

    colors = {10: "#1f77b4", 30: "#2ca02c", 50: "#d62728", 100: "#ff7f0e"}

    for idx, filepath in enumerate(csv_files):
        ax = axes[idx]
        loss_val = extract_loss_pct(filepath)
        df = pd.read_csv(filepath)
        df["TQ"] = pd.to_numeric(df["TQ"], errors="coerce")
        df["outgoing_if"] = df["outgoing_if"].fillna("unknown").astype(str)

        col = colors.get(loss_val, "#333333")

        # Background phase shading
        ax.axvspan(0, BASELINE_S, color="#f0f3f4", alpha=0.7)
        ax.axvspan(BASELINE_S, RECOVER_TIME, color="#fadbd8", alpha=0.35)
        ax.axvspan(RECOVER_TIME, df["time_s"].max(), color="#e8f8f5", alpha=0.7)

        # Plot TQ line
        ax.plot(df["time_s"], df["TQ"], color=col, linewidth=2.2, label=f"TQ ({loss_val}% Loss)")

        # Secondary Y-Axis for Active Egress Interface
        ax_if = ax.twinx()
        if_map = {"veth1-2": 0, "veth1-4": 1}
        # Fallback for unexpected interface names
        for val in df["outgoing_if"].unique():
            if val not in if_map:
                if_map[val] = len(if_map)

        y_if = df["outgoing_if"].map(if_map)
        ax_if.step(
            df["time_s"],
            y_if,
            where="post",
            color="#2c3e50",
            linestyle="--",
            linewidth=1.8,
            alpha=0.85,
            label="Active Route",
        )

        ax_if.set_ylim(-0.3, 1.3)
        ax_if.set_yticks([0, 1])
        ax_if.set_yticklabels(["Path A\n(veth1-2)", "Path B\n(veth1-4)"], fontsize=9, fontweight="bold")
        ax_if.tick_params(axis="y", colors="#2c3e50")

        # Axis scaling
        ax.set_ylim(180, 210)
        ax.set_yticks([185, 195, 205])
        ax.set_ylabel("TQ Metric", fontsize=10, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.6)

        # Title for individual run
        ax.set_title(f"Synthetic Loss Level: {loss_val}% (Fault injected on Link 1 <-> 2)", fontsize=11, fontweight="bold", loc="left", pad=6)

        # Annotations on the top subplot only
        if idx == 0:
            ax.text(BASELINE_S / 2, 207, "Baseline", ha="center", fontsize=9, fontweight="bold", color="#7f8c8d")
            ax.text((BASELINE_S + RECOVER_TIME) / 2, 207, "Fault Injected (Link 1-2)", ha="center", fontsize=9, fontweight="bold", color="#c0392b")
            ax.text((RECOVER_TIME + df["time_s"].max()) / 2, 207, "Recovery Phase", ha="center", fontsize=9, fontweight="bold", color="#16a085")

    axes[-1].set_xlabel("Elapsed Time (seconds)", fontsize=11, fontweight="bold")

    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=300)
    print(f"[SUCCESS] Polished quad-chart visual saved to: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()