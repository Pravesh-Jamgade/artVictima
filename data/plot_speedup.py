#!/usr/bin/env python3
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
from scipy.stats import gmean

raw_data = """
ipc	design	workload
0.0586489012	vikram	dlrm
0.07759300972	vikram	pr
0.06443911066	vikram	cc
0.08828038263	vikram	sssp
0.06903980797	vikram	gc
0.279423814	vikram	tc
0.4924251653	vikram	xs
0.7050056023	vikram	rnd
0.05865463553	vikram	bfs
0.3460059548	vikram	bc
0.06906556256	vikram	gen
0.0586347082	victima	dlrm
0.07786850832	victima	pr
0.06336863325	victima	cc
0.08561418564	victima	sssp
0.0647464701	victima	gc
0.2657779247	victima	tc
0.5282917184	victima	xs
0.6083603119	victima	rnd
0.05866397974	victima	bfs
0.3015277088	victima	bc
0.06474612132	victima	gen
0.05575944766	baseline	dlrm
0.07431437562	baseline	pr
0.06108325355	baseline	cc
0.08398528292	baseline	sssp
0.06379210485	baseline	gc
0.2572936543	baseline	tc
0.4647871536	baseline	xs
0.5228420184	baseline	rnd
0.05569089657	baseline	bfs
0.3028640997	baseline	bc
0.06375089071	baseline	gen
0.05638350401	potm	dlrm
0.07430508661	potm	pr
0.06136113287	potm	cc
0.08557897051	potm	sssp
0.06493313271	potm	gc
0.2658778726	potm	tc
0.4805682148	potm	xs
0.5085996274	potm	rnd
0.05640083912	potm	bfs
0.3043051033	potm	bc
0.06492793694	potm	gen
"""

def main():
    ap = argparse.ArgumentParser()
    # Arguments maintained for structure even though using raw_data inside
    ap.add_argument("csv", nargs='?', default=None, help="Input file (not used since raw_data is hardcoded)")
    ap.add_argument("--out", default="", help="Optional output image.")
    ap.add_argument("--sort", default="workload", choices=["workload", "mean_speedup"])
    ap.add_argument("--figsize", default="14,6")
    ap.add_argument("--geomean", action="store_true", default=True) # Enabled by default for research
    args = ap.parse_args()

    # 1. Load and clean
    df = pd.read_csv(io.StringIO(raw_data), sep=r"\s+")
    
    # FIX: Rename 'ipc' to 'speedup' so logic works
    if 'ipc' in df.columns:
        df = df.rename(columns={'ipc': 'speedup'})

    df["design"] = df["design"].astype(str).str.strip()
    df["workload"] = df["workload"].astype(str).str.strip()
    df["speedup"] = pd.to_numeric(df["speedup"], errors="coerce")
    df = df.dropna(subset=["speedup"])

    # 2. Pivot to workload x design
    wide = df.pivot_table(index="workload", columns="design", values="speedup", aggfunc="mean")

    # FIX: Normalize to 'baseline' if baseline exists
    if 'baseline' in wide.columns:
        wide = wide.div(wide['baseline'], axis=0)

    # 3. Sort
    if args.sort == "mean_speedup":
        wide = wide.loc[wide.mean(axis=1).sort_values(ascending=False).index]
    else:
        wide = wide.sort_index()

    # 4. Calculate Geomean
    if args.geomean:
        actual_workloads = wide.index[wide.index.str.lower() != 'geomean']
        geomean_series = wide.loc[actual_workloads].apply(gmean, axis=0)
        geomean_series.name = "geomean"
        wide = wide.drop("geomean", errors="ignore")
        wide = pd.concat([wide, geomean_series.to_frame().T])

    # 5. Column Ordering
    preferred = ["baseline", "ptb", "vikram", "potm", "victima", "utopia"]
    cols = [c for c in preferred if c in wide.columns] + [c for c in wide.columns if c not in preferred]
    wide = wide[cols]

    # --- PLOTTING ---
    W, H = (float(x) for x in args.figsize.split(","))
    ax = wide.plot(kind="bar", figsize=(W, H), width=0.8, zorder=3)

    plt.ylabel("Normalized IPC (Speedup)", fontsize=20, fontweight='bold')
    plt.xlabel("Workload", fontsize=20, fontweight='bold')
    plt.xticks(rotation=45, ha='right', fontsize=16)
    plt.yticks(fontsize=16)
    
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.axhline(1.0, color='black', linestyle='-', linewidth=2.0, zorder=4) 

    ax.legend(
        loc='lower center',
        bbox_to_anchor=(0.5, 1.1),
        ncol=len(wide.columns),
        fontsize=15,
        frameon=False
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    if args.out:
        plt.savefig(args.out, dpi=300, bbox_inches="tight")
    else:
        plt.show()

if __name__ == "__main__":
    main()
