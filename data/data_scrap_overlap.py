#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict
# [Verification] Importing pandas as requested for dataframe handling [Pandas Documentation](https://pandas.pydata.org)
import pandas as pd

OVERLAP_RATE = re.compile(r"^proposed_PTB_overlap_success_rate_pct,([\d.]+)$")
OVERLAP_RATIO = re.compile(r"^proposed_PTB_overlap_ratio_avg,([\d.]+)$")

def path_tag(file_path: Path, root: Path) -> str: 
    try:
        rel_path = file_path.relative_to(root).parent
        return str(rel_path).replace("/", "_") if str(rel_path) != "." else "root"
    except Exception:
        return file_path.parent.name

def main(root_dir="", raw_out_csv="stats_overlap.csv", summary_out_csv="stats_overlap_summary.csv"):
    if not root_dir:
        root_dir = "."
    
    root = Path(root_dir).resolve()
    stats_files: List[Path] = list(root.rglob("proposed*.csv"))
    print(f"Searching in {root}. Files found: {len(stats_files)}")

    rows: List[Dict] = []
    
    for f in stats_files:
        tag = path_tag(f, root)
        # FIX: Initialize the dictionary for this specific file
        file_stats = {'rate': 0.0, 'ratio': 0.0}
        
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            found_count = 0
            for line in fp:
                line = line.strip()
                if not line: continue
                
                rate_match = OVERLAP_RATE.match(line)
                ratio_match = OVERLAP_RATIO.match(line)
                
                if rate_match:
                    # FIX: Update the dictionary, do not re-initialize it
                    file_stats['rate'] = float(rate_match.group(1))/100.0
                    found_count += 1
                
                elif ratio_match:
                    file_stats['ratio'] = float(ratio_match.group(1))
                    found_count += 1
                
                if found_count == 2:
                    print(f"{tag}, {file_stats['rate']}, {file_stats['ratio']}")
                    break

        # FIX: Append only one row per file using the collected stats
        rows.append({
            "workload": tag,
            "overlap_success_rate_pct": file_stats['rate'],
            "overlap_ratio_avg": file_stats['ratio']*100
        })

    if not rows:
        print("No data rows collected. Exiting.")
        return

    df = pd.DataFrame(rows)
    df.to_csv(raw_out_csv, index=False)
    print(f"Writing {len(df)} raw rows to {raw_out_csv}")

    # FIX: Grouping logic - only aggregate the columns that are numbers
    summary_df = df.groupby('workload').agg({
        'overlap_success_rate_pct': ['mean', 'count'],
        'overlap_ratio_avg': ['mean']
    })
    
    summary_df.columns = [f"{col[0]}_{col[1]}" for col in summary_df.columns]
    summary_df = summary_df.reset_index()

    summary_df.to_csv(summary_out_csv, index=False)
    print(f"Writing summary to {summary_out_csv}")
    print("Done.")

if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir)
