import sys
import os
import csv
import re

# Fixed bucket midpoints (cycles)
BUCKET_MID = {
    "0..1": 0.5,
    "2..3": 2.5,
    "4..7": 5.5,
    "8..15": 11.5,
    "16..31": 23.5,
    "32..63": 47.5,
    "64..127": 95.5,
    "128..255": 191.5,
    "256..511": 383.5,
    "512..1023": 767.5,
    "1024..2047": 1535.5,
}

BUCKETS = list(BUCKET_MID.keys())

def parse_row(tokens):
    """
    tokens: list of strings after 'level'
    returns: dict(bucket -> count), total
    """
    hist = {}
    total = 0
    for b, v in zip(BUCKETS, tokens[:len(BUCKETS)]):
        hist[b] = int(v) if v.strip() else 0
        total += hist[b]

    return hist, total


def avg_latency(hist, total):
    if total == 0:
        return 0.0
    return sum(BUCKET_MID[b] * c for b, c in hist.items()) / total


def process_file(path):
    """
    Returns list of:
      (level, total, avg_latency)
    """
    results = []

    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]

    rows = []

    for line in lines:
        if line.startswith("folder_tag"):
            continue
        tokens = [t.strip() for t in line.split(",")]
        name = tokens[0]
        level = tokens[1]
        hist, total = parse_row(tokens[2:])
        avg = avg_latency(hist, total)
        results.append((name, level, total, avg))

    return results


def main(file_path, out_csv):
    all_results = []
    rows = process_file(file_path)
    for w, lvl, total, avg in rows:
        all_results.append([
           w, lvl, total, round(avg, 3)
        ])

    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "workload", "level", "total_accesses", "avg_latency_cycles"
        ])
        writer.writerows(all_results)


if __name__ == "__main__":
    # Get directory from command line arguments or use current dir if none provided
    main(file_path=sys.argv[1], out_csv="stats_avglatency.csv")
