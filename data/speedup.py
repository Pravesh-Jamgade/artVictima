#!/usr/bin/env python3
"""
Grouped bar chart:
- x-axis: workload (includes a synthetic 'geomean' category)
- bars: designs
- height: speedup
- reads from CSV with columns: design,workload,speedup

Usage:
  python3 plot_speedup.py results.csv
  python3 plot_speedup.py results.csv --out speedup.png
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gmean # Import geometric mean function

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="Input CSV with columns: design,workload,speedup")
    ap.add_argument("--out", default="", help="Optional output image (png/pdf/svg). If omitted, shows window.")
    ap.add_argument("--sort", default="workload", choices=["workload", "mean_speedup"],
                    help="Sort workloads by name or by mean speedup across designs.")
    ap.add_argument("--figsize", default="12,5", help='Figure size as "W,H" (inches)')
    # Add argument to control whether to calculate and show geomean
    ap.add_argument("--geomean", action="store_true", help="Calculate and display the geometric mean as an extra workload index.")
    args = ap.parse_args()

    # Read + validate
    df = pd.read_csv(args.csv)
    req = {"design", "workload", "speedup"}
    missing = req - set(df.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")

    df = df.copy()
    df["design"] = df["design"].astype(str).str.strip()
    df["workload"] = df["workload"].astype(str).str.strip()
    df["speedup"] = pd.to_numeric(df["speedup"], errors="coerce")
    df = df.dropna(subset=["speedup"])

    # Pivot to wide for grouped bars
    wide = df.pivot_table(index="workload", columns="design", values="speedup", aggfunc="mean")

    # Sort workloads (sort happens on the index, which now includes 'Geomean' if added)
    if args.sort == "mean_speedup":
        # Note: Sorting by mean speedup will place the 'Geomean' row wherever it naturally sorts
        wide = wide.loc[wide.mean(axis=1).sort_values(ascending=False).index]
    else:
        # If sorting by workload name, 'Geomean' might appear alphabetically
        wide = wide.sort_index()
        # You might need extra logic here to force 'Geomean' to the bottom if desired


    # --- Calculate Geometric Mean and add as a new index (row) ---
    if args.geomean:
        # Calculate the geometric mean across all workloads for each design (axis=0)
        # Use gmean from scipy.stats, but ensure data is non-negative (speedups usually are)
        # We wrap in a try-except to handle potential issues if gmean fails (e.g. negative speedups)
        try:
            geomean_series = wide.apply(gmean, axis=0)
            geomean_series.name = "geomean" # Name the new index (row label)
            # Append the geomean as a new row to the DataFrame
            wide = pd.concat([wide, geomean_series.to_frame().T])
        except Exception as e:
            print(f"Warning: Could not calculate geometric mean. Ensure speedup values are positive. Error: {e}")

    
    # Keep a stable design order if you want
    preferred = ["utopia", "potm", "victima", "ptbpd", "geomean"]
    cols = [c for c in preferred if c in wide.columns] + [c for c in wide.columns if c not in preferred]
    wide = wide[cols]

    # Plot
    W, H = (float(x) for x in args.figsize.split(","))
    ax = wide.plot(kind="bar", figsize=(W, H))

    ax.set_xlabel("Workload")
    ax.set_ylabel("Speedup (%)" if wide.values.max() > 2 else "Speedup")
    ax.axhline(1.0, color='red', linestyle='--', linewidth=1) # Baseline should likely be 1.0 for speedup
    ax.axhline(0.0, linewidth=0.5, color='grey') 

    # Make it readable
    plt.xticks(rotation=45, ha='right') # Rotate x-labels to fit 'Geomean' and workloads
    ax.legend(title="Design", ncol=min(4, len(wide.columns)), frameon=False)
    plt.tight_layout()

    if args.out:
        plt.savefig(args.out, dpi=300, bbox_inches="tight")
    else:
        plt.show()

if __name__ == "__main__":
    main()
