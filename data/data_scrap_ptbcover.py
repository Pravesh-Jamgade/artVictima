#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Optional
import pandas as pd

HEADER_RE = re.compile(r"^proposed_PTB_PDPT_combo,(PTB-MISS_PDPT-MISS),(PTB-MISS_PDPT-HIT),(PTB-HIT_PDPT-MISS),(PTB-HIT_PDPT-HIT)$")
VALUE_RE = re.compile(r"^proposed_PTB_PDPT_combo,(\d+),(\d+),(\d+),(\d+)$")

def path_tag(file_path: Path, root: Path) -> str: 
    try:
        # relative_to strips the root path and keeps the subfolders
        rel_path = file_path.relative_to(root).parent
        return str(rel_path).replace("/", "_") if str(rel_path) != "." else root.name
    except:
        return file_path.parent.name

def main(root_dir="", raw_out_csv="stats_ptbcover.csv"):
    root = Path(root_dir or ".").resolve()
    stats_files = list(root.rglob("proposed0.csv"))
    print(f"Searching in {root}. Files found: {len(stats_files)}")

    rows: List[Dict] = []
    headers_found = None
    
    for f in stats_files:
        tag = path_tag(f, root)
        current_headers = None
        
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                line = line.strip()
                
                h_match = HEADER_RE.match(line)
                if h_match:
                    current_headers = h_match.groups()
                    headers_found = current_headers
                    continue
                
                v_match = VALUE_RE.match(line)
                if v_match and current_headers:
                    values = v_match.groups()
                    standard_row = {"folder_tag": tag}
                    # Merge headers and values into the dict
                    for h, v in zip(current_headers, values):
                        standard_row[h] = int(v)
                    rows.append(standard_row)

    if not rows:
        print("No data collected.")
        return

    df = pd.DataFrame(rows)
    
    # Save the raw CSV
    df.to_csv(raw_out_csv, index=False)
    print(f"Saved {len(df)} rows to {raw_out_csv}")

if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir)
