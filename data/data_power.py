#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Iterator

# --- Regex Pattern ---
# Matches: component name, then captures numeric values for Watts and Joules
# Example input: "l2 3.95 W 2.19 J 22.33%" -> captures ("l2", "3.95", "2.19")
STATS_RE = re.compile(r"^(l2|nuca|dram)\s+([\d.]+)\s+W\s+([\d.]+)\s+J")

def path_tag(file_path: Path) -> str: 
    return "_".join(file_path.parent.parts)

def find_files_recursive(root_dir: Path) -> Iterator[Path]:
    yield from root_dir.rglob("sim.stdout")

def main(root_dir="", out_csv="power_energy_numeric.csv"):
    root = Path(root_dir or ".").resolve()
    all_files_to_scan = list(find_files_recursive(root))
    
    results = {}

    for f in all_files_to_scan:
        tag = path_tag(f)
        if tag not in results:
            results[tag] = {"folder_tag": tag}

        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                line = line.strip()
                if match := STATS_RE.search(line):
                    comp = match.group(1).lower()
                    watts = match.group(2) # Numeric value only
                    joules = match.group(3) # Numeric value only
                    
                    results[tag][f"{comp}_watts"] = watts
                    results[tag][f"{comp}_joules"] = joules

    # Column headers (clean labels without units)
    output_fieldnames = [
        "folder_tag", 
        "l2_watts", "l2_joules", 
        "nuca_watts", "nuca_joules", 
        "dram_watts", "dram_joules"
    ]

    rows = list(results.values())
    with open(out_csv, "w", encoding="utf-8", newline='') as out:
        writer = csv.DictWriter(out, fieldnames=output_fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Done. Numeric data saved to {out_csv}")

if __name__ == "__main__":
    # Correctly handle input path from command line
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir)
