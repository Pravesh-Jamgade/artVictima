#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Iterator

# --- Regex Configuration ---
# Set the number of values you want to capture here
NUM_IPC_VALUES = 16 
pattern_parts = [r"([\d\.]+)"] * NUM_IPC_VALUES
IPC_RE = re.compile(r"ipc\s*=\s*" + r",\s*".join(pattern_parts))

def path_tag(file_path: Path) -> str: 
    return "_".join(file_path.parent.parts)

def find_files_recursive(root_dir: Path) -> Iterator[Path]:
    yield from root_dir.rglob("proposed.csv")
    yield from root_dir.rglob("sim.stats") 

def main(root_dir="", out_csv="stats_ipc_only_recursive.csv"):
    if not root_dir:
        root_dir = "."
    
    root = Path(root_dir).resolve()
    all_files_to_scan = list(find_files_recursive(root))
    print(f"Searching in {root}. Files found: {len(all_files_to_scan)}")

    rows: List[Dict] = []
    
    # 1. Dynamically create headers based on NUM_IPC_VALUES
    ipc_headers = [f"ipc{i+1}" for i in range(NUM_IPC_VALUES)]
    output_fieldnames = ["folder_tag", "metric_name"] + ipc_headers
    
    for f in all_files_to_scan:
        tag = path_tag(f)
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                line = line.strip()

                if ipc_match := IPC_RE.match(line):
                    # 2. Start the row with metadata
                    row = {
                        "folder_tag": tag,
                        "metric_name": "ipc",
                    }
                    
                    # 3. Use a loop to add all captured groups to the row
                    # ipc_match.groups() returns a tuple of all matched numbers
                    for i, value in enumerate(ipc_match.groups()):
                        row[f"ipc{i+1}"] = value
                    
                    rows.append(row)

    print(f"Writing {len(rows)} rows to {out_csv}")

    with open(out_csv, "w", encoding="utf-8", newline='') as out:
        writer = csv.DictWriter(out, fieldnames=output_fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    print("Done.")

if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir)
