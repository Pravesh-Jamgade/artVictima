#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Optional, Set
import pandas as pd

# Regex for L1-L4 hits and misses
HITS_RE = re.compile(r"proposed_PSC_L(\d+)_hits,(\d+)$")
MISS_RE = re.compile(r"proposed_PSC_L(\d+)_misses,(\d+)$")

def path_tag(file_path: Path, root: Path) -> str: 
    """Returns folder path relative to the search root, joined by underscores."""
    try:
        # relative_to strips the absolute path prefix
        rel_path = file_path.relative_to(root).parent
        # If the file is in the root itself, return 'root' or similar
        return str(rel_path).replace("/", "_") if str(rel_path) != "." else "root"
    except Exception:
        return file_path.parent.name

def main(root_dir="", raw_out_csv="stats_hitmiss.csv", summary_out_csv="stats_hitmiss_summary.csv"):
    if not root_dir:
        root_dir = "."
    
    root = Path(root_dir).resolve()
    # CHANGE: Using wildcard * to match proposed.csv, proposed0.csv, etc.
    stats_files: List[Path] = list(root.rglob("proposed*.csv"))
    print(f"Searching in {root}. Files found: {len(stats_files)}")

    rows: List[Dict] = []
    
    for f in stats_files:
        tag = path_tag(f, root)
        # Store hits/misses keyed by level: { '1': {'hits': 100, 'misses': 50} }
        data_by_level: Dict[str, Dict[str, int]] = {}
        
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                line = line.strip()
                if not line: continue
                
                hit_match = HITS_RE.search(line)
                miss_match = MISS_RE.search(line)
                
                if hit_match:
                    lvl, val = hit_match.groups()
                    if lvl not in data_by_level: data_by_level[lvl] = {}
                    data_by_level[lvl]['hits'] = int(val)
                
                elif miss_match:
                    lvl, val = miss_match.groups()
                    if lvl not in data_by_level: data_by_level[lvl] = {}
                    data_by_level[lvl]['misses'] = int(val)

        # Process the collected data for this file
        for lvl, stats in data_by_level.items():
            hits = stats.get('hits', 0)
            misses = stats.get('misses', 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0.0

            rows.append({
                "workload": tag,  # This now contains the relative path tag
                "level": f"L{lvl}",
                "hits": hits,
                "misses": misses,
                "total_accesses": total,
                "hit_rate_pct": round(hit_rate, 2)
            })

    if not rows:
        print("No data rows collected. Exiting.")
        return

    # Write Raw Data
    df = pd.DataFrame(rows)
    df.to_csv(raw_out_csv, index=False)
    print(f"Writing {len(df)} raw rows to {raw_out_csv}")

    # Summary Statistics
    metrics = ["hits", "misses", "total_accesses", "hit_rate_pct"]
    summary_df = df.groupby(['level'])[metrics].agg(['sum', 'mean'])
    
    # Flatten columns: hits_sum, hits_mean, etc.
    summary_df.columns = [f"{col[0]}_{col[1]}" for col in summary_df.columns]
    summary_df = summary_df.reset_index()

    summary_df.to_csv(summary_out_csv, index=False)
    print(f"Writing summary to {summary_out_csv}")
    print("Done.")

if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir)
