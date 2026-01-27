#!/usr/bin/env python3
import argparse
import pandas as pd
import matplotlib.pyplot as plt

# Workload,L1,L2,LLC,DRAM
# bc,615474.8333,416884.6667,226,1370328.375
# bfs,5194133.5,9885084.5,143.6666667,5534541.375
# cc,6665992.833,12282227,74.25,6443404.25
# dlrm,5561199.5,10045118.33,54.83333333,5519815.125
# gc,5096506.333,9344031.667,3345.75,5875083.25
# gen,3846553.25,9315314.333,3279,5866040
# pr,2757773.833,4927703,2.5,2683529
# rnd,12811301.5,12551884.5,26.75,4472322.5
# sssp,2925434.5,3063919.833,115.25,7943783.25
# tc,431512,972264.8,12,684247.25
# xs,677468.8333,1475864.667,448.25,850514.25


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="CSV with columns: Workload,L1,L2,LLC,DRAM")
    ap.add_argument("--out", default="", help="Output image (png/pdf/svg). If omitted, show window.")
    ap.add_argument("--logy", action="store_true", help="Use log-scale Y axis")
    ap.add_argument("--figsize", default="12,5", help='Figure size "W,H" in inches')
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df.set_index("Workload")
    cols = ["L1", "L2", "LLC", "DRAM"]
    df = df[cols]

    # Scale to millions for readable ticks
    df_plot = df / 1e6

    W, H = (float(x) for x in args.figsize.split(","))
    ax = df_plot.plot(kind="bar", stacked=True, figsize=(W, H))

    ax.set_xlabel("Workload")
    ax.set_ylabel("Hit counts (millions)")
    ax.legend(title="", frameon=False, ncol=4)

    if args.logy:
        ax.set_yscale("log")
        ax.set_ylabel("Hit counts (millions, log scale)")

    plt.xticks(rotation=0)
    plt.tight_layout()

    if args.out:
        plt.savefig(args.out, dpi=300, bbox_inches="tight")
    else:
        plt.show()

if __name__ == "__main__":
    main()
