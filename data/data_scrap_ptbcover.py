#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Optional
import pandas as pd

# Regex patterns remain the same
HEADER_RE = re.compile(r"^proposed_PTB_PDPT_combo,(PTB-MISS_PDPT-MISS),(PTB-MISS_PDPT-HIT),(PTB-HIT_PDPT-MISS),(PTB-HIT_PDPT-HIT)$")
VALUE_RE = re.compile(r"^proposed_PTB_PDPT_combo,(\d+),(\d+),(\d+),(\d+)$")

def path_tag(file_path: Path, root: Path) -> str: 
    try:
        rel_path = file_path.relative_to(root).parent
        return str(rel_path).replace("/", "_") if str(rel_path) != "." else root.name
    except:
        return file_path.parent.name

def main(root_dir="", raw_out_csv="stats_ptbcover.csv"):
    root = Path(root_dir or ".").resolve()
    
    # FIX: Updated pattern to use wildcard for any proposed file
    stats_files = list(root.rglob("proposed*.csv"))
    
    print(f"Searching in {root}. Files found: {len(stats_files)}")

    rows: List[Dict] = []
    
    for f in stats_files:
        tag = path_tag(f, root)
        current_headers = None
        
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                line = line.strip()
                if not line: continue
                
                h_match = HEADER_RE.match(line)
                if h_match:
                    current_headers = h_match.groups()
                    continue
                
                v_match = VALUE_RE.match(line)
                if v_match and current_headers:
                    values = v_match.groups()
                    standard_row = {"folder_tag": tag}
                    for h, v in zip(current_headers, values):
                        standard_row[h] = int(v)
                    rows.append(standard_row)
                    # Reset headers after finding a value pair to ensure clean state per file
                    current_headers = None 

    if not rows:
        print("No data collected.")
        return

    df = pd.DataFrame(rows)
    df.to_csv(raw_out_csv, index=False)
    print(f"Saved {len(df)} rows to {raw_out_csv}")

if __name__ == "__main__":
    # Ensure sys.argv[1] is accessed safely
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir)
