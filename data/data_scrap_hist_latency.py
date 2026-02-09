#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Optional

# Updated Regex to handle 'core_0_', '_miss_', and level number
# Matches: core_0_proposed_PSC_L2_miss_latency_cycles,[4..7],...
HEADER_LINE_RE = re.compile(r"core_\d+_proposed_PSC_L(\d+)_miss_latency_cycles,(?:\[\d+\.\.\d+\])")

# Desired final output header collection
TARGET_HEADERS = [
    "folder_tag", "level", "0..1", "2..3", "4..7", "8..15", "16..31",
    "32..63", "64..127", "128..255", "256..511", "512..1023", "1024..2047"
]

def path_tag(file_path: Path) -> str: 
    return file_path.parent.name

def parse_csv_line(line: str) -> List[str]:
    reader = csv.reader([line])
    return next(reader)

def main(root_dir=".", out_csv="stats_histLatency.csv"):
    root = Path(root_dir).resolve()
    stats_files = list(root.rglob("proposed*.csv"))
    print(f"Searching in {root}. Files found: {len(stats_files)}")

    rows: List[Dict] = []
    
    for f in stats_files:
        tag = path_tag(f)
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            current_header: Optional[List[str]] = None
            current_level: str = ""

            for line in fp:
                line = line.strip()
                if not line: continue

                header_match = HEADER_LINE_RE.search(line)
                if header_match:
                    current_header = parse_csv_line(line)
                    current_level = f"L{header_match.group(1)}"
                    continue # Next line should be the data

                if current_header:
                    value_data = parse_csv_line(line)
                    
                    # Basic validation: ensure this line isn't another header
                    if "proposed" in value_data[0] and "[" not in line:
                        standard_row = {h: "" for h in TARGET_HEADERS}
                        standard_row["folder_tag"] = tag
                        standard_row["level"] = current_level

                        for i in range(1, len(value_data)):
                            if i < len(current_header):
                                # Convert [4..7] -> 4..7
                                bin_name = current_header[i].strip('[]')
                                if bin_name in TARGET_HEADERS:
                                    standard_row[bin_name] = value_data[i]
                        
                        rows.append(standard_row)
                    
                    current_header = None # Reset to look for next block

    print(f"Writing {len(rows)} rows to {out_csv}")
    with open(out_csv, "w", newline='') as out:
        writer = csv.DictWriter(out, fieldnames=TARGET_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir)
