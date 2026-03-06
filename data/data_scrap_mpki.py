#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Iterator

# Regex patterns for STLB misses and Instruction counts
# Format: key,value (based on your provided data snippet)
MISSES_RE = re.compile(r"proposed_STLB_miss_walks,(\d+)")
INST_RE = re.compile(r"proposed_STLB_miss_instruction_count,(\d+)")

def path_tag(file_path: Path) -> str: 
    return "_".join(file_path.parent.parts)

def find_files_recursive(root_dir: Path) -> Iterator[Path]:
    yield from root_dir.rglob("proposed*.csv")

def main(root_dir="", out_csv="stlb_mpki_results.csv"):
    root = Path(root_dir or ".").resolve()
    all_files_to_scan = list(find_files_recursive(root))
    
    print(all_files_to_scan)
    rows: List[Dict] = []
    output_fieldnames = ["folder_tag", "misses", "instructions", "stlb_mpki"]
    
    for f in all_files_to_scan:
        tag = path_tag(f)
        misses = None
        insts = None
        
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                line = line.strip()
                
                # Extract Misses
                if m_match := MISSES_RE.search(line):
                    misses = int(m_match.group(1))
                
                # Extract Instructions
                if i_match := INST_RE.search(line):
                    insts = int(i_match.group(1))

        # Calculate MPKI if both metrics were found
        if misses is not None and insts is not None and insts > 0:
            mpki = (misses / insts) * 1000
            rows.append({
                "folder_tag": tag,
                "misses": misses,
                "instructions": insts,
                "stlb_mpki": f"{mpki:.6f}"
            })

    print(f"Writing {len(rows)} MPKI calculations to {out_csv}")
    with open(out_csv, "w", encoding="utf-8", newline='') as out:
        writer = csv.DictWriter(out, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Also print a summary to console for quick checking
    for r in rows:
        print(f"[{r['folder_tag']}] MPKI: {r['stlb_mpki']}")

if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir)
