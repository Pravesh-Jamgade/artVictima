#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Optional, Tuple, Iterator

# Note: The scrap_csv_metrics list has been left out as requested.

# Regex specifically for the "ipc = <value>" format
# Catches optional whitespace around the equals sign and captures the numeric value
IPC_RE = re.compile(r"^\s*ipc\s*=\s*(\d+\.\d+)\s*$")

def path_tag(file_path: Path) -> str: 
    """Generates a consistent tag from the parent directory path components."""
    return "_".join(file_path.parent.parts)

# Helper function (kept for general utility if needed later)
def parse_csv_line(line: str) -> List[str]:
    """Helper function to parse a line of data/headers into a list of strings."""
    reader = csv.reader([line])
    return next(reader)

def find_files_recursive(root_dir: Path) -> Iterator[Path]:
    """Uses rglob to find all relevant files recursively."""
    yield from root_dir.rglob("proposed.csv")
    # Assuming IPC might also be in a standard simulation output log
    yield from root_dir.rglob("sim.stats") 


def main(root_dir="", out_csv="stats_ipc_only_recursive.csv"):
    if not root_dir:
        root_dir = "."
    
    # This line now safely receives a single string path
    root = Path(root_dir).resolve()
    
    # --- Recursive File Finding ---
    all_files_to_scan = list(find_files_recursive(root))
    print(f"Searching in {root}. Files found: {len(all_files_to_scan)} relevant files.")

    rows: List[Dict] = []
    output_fieldnames = ["folder_tag", "metric_name", "metric_value"]
    
    # --- Processing Loop (Recursive Read Structure) ---
    for f in all_files_to_scan:
        tag = path_tag(f)
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                line = line.strip()

                # Check ONLY for the specific IPC line format using regex
                if ipc_match := IPC_RE.match(line):
                    metric_name = "ipc"
                    metric_value = ipc_match.group(1) # The value captured by the regex group

                    row = {
                        "folder_tag": tag,
                        "metric_name": metric_name,
                        "metric_value": metric_value
                    }
                    rows.append(row)
                
                # Else: ignore the line (e.g., ignore all CSV metrics)


    # --- Write all collected data to a single CSV ---
    print(f"Writing {len(rows)} standardized IPC rows to {out_csv}")

    with open(out_csv, "w", encoding="utf-8", newline='') as out:
        writer = csv.DictWriter(out, fieldnames=output_fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    print("Done.")


if __name__ == "__main__":
    # FIX IS HERE: Use sys.argv[1] to get the specific path string
    if len(sys.argv) > 1:
        input_dir = sys.argv[1] # <--- Correctly grabs the path string
    else:
        input_dir = "." # Default to current directory if no argument provided
    
    main(root_dir=input_dir, out_csv="stats_ipc_only_recursive.csv")
