#!/usr/bin/env python3
import argparse
import pandas as pd
import matplotlib.pyplot as plt

BUCKETS = [
    "0..1","2..3","4..7","8..15","16..31",
    "32..63","64..127","128..255","256..511","512..1023"
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="Input CSV with columns: level, latency buckets")
    ap.add_argument("--out", default="", help="Output image (png/pdf/svg). If omitted, show window.")
    ap.add_argument("--figsize", default="10,5", help='Figure size "W,H" in inches')
    args = ap.parse_args()

    # Read CSV
    df = pd.read_csv(args.csv)

    # Ensure expected columns exist
    missing = set(["level"] + BUCKETS) - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}")

    # Clean: fill NaNs → 0, ensure ints
    df[BUCKETS] = df[BUCKETS].fillna(0).astype(float)

    # Index by level for legend clarity
    df["level"] = df["level"].astype(int)
    df = df.set_index("level").sort_index()

    # Transpose so X = latency buckets, stacks = levels
    plot_df = df[BUCKETS].T
    plot_df.columns = [f"L{lvl}" for lvl in plot_df.columns]

    W, H = (float(x) for x in args.figsize.split(","))
    ax = plot_df.plot(
        kind="bar",
        stacked=True,
        figsize=(W, H)
    )

    ax.set_xlabel("Latency (cycles)")
    ax.set_ylabel("Count (log scale)")
    # ax.set_yscale("log")
    ax.legend(title="Page-table level", frameon=False, ncol=4)

    plt.xticks(rotation=0)
    plt.tight_layout()

    if args.out:
        plt.savefig(args.out, dpi=300, bbox_inches="tight")
    else:
        plt.show()

if __name__ == "__main__":
    main()
