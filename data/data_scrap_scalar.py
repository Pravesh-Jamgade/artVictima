#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Optional, Tuple

# # Regex to check if a line is a header definition line
# scrap = [
#     "proposed_STLB_miss_CPI,",
#     "proposed_STLB_miss_avg_stall_cycles,",
#     "proposed_STLB_miss_walks,",
#     "proposed_PSC_miss_rate_pct,",
#     "proposed_PSC_misses,",
#     "proposed_PSC_accesses,",
#     "proposed_PSC_L1_hits,"
#     "proposed_PSC_L1_misses,",
#     "proposed_PSC_L2_hits,",
#     "proposed_PSC_L2_misses,",
#     "proposed_PSC_L3_hits,",
#     "proposed_PSC_L3_misses,",
#     "proposed_PTB_latency_share_pct,0.00"
# ]

scrap = [
    "proposed_STLB_miss_avg_stall_cycles,",
]

def path_tag(file_path: Path) -> str: 
    return "_".join(file_path.parent.parts)

# Helper function to parse a line of data/headers into a list of non-empty strings
def parse_csv_line(line: str) -> List[str]:
    # Use the csv module's reader for robust parsing of commas and empty fields
    reader = csv.reader([line])
    return next(reader)


def main(root_dir="", out_csv="stats_scalar.csv"):
    # If root_dir is empty, default to searching the current directory
    if not root_dir:
        root_dir = "."
    
    # full path using resolve from Path object
    root = Path(root_dir).resolve()
    stats_files: List[Path] = list(root.rglob("proposed.csv"))
    print(f"Searching in {root}. Files found: {len(stats_files)}")

    rows: List[Dict] = []
    
    for f in stats_files:
        tag = path_tag(f)
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            # We must track the most recent header line encountered
            current_header_data: Optional[List[str]] = None
            
            for line in fp:
                line = line.strip()

                if findLineToScrap := next((s for s in scrap if line.startswith(s)), None):
                    # This is a scalar data line. Parse it.
                    parsed_line = parse_csv_line(line)
                    metric_name = parsed_line[0]
                    metric_value = parsed_line[1]

                    row = {
                        "folder_tag": tag,
                        "metric_name": metric_name,
                        "metric_value": metric_value
                    }
                    rows.append(row)

          

    # --- Pass 2: Write all collected data to a single CSV ---
    print(f"Writing {len(rows)} standardized rows to {out_csv}")

    with open(out_csv, "w", encoding="utf-8", newline='') as out:
        writer = csv.DictWriter(out, fieldnames=["folder_tag", "metric_name", "metric_value"], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    print("Done.")


if __name__ == "__main__":
    # Get directory from command line arguments or use current dir if none provided
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir, out_csv="stats_scalar.csv")
