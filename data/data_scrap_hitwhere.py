#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Optional, Set
import pandas as pd # Import pandas for aggregation

# Regex patterns (same as before)
HITWHERE_LINE_RE = re.compile(r"^proposed_PSC_L\d+_miss_hitwhere.*$")
METRIC_LEVEL_RE = re.compile(r"^proposed_PSC_L(\d+)_miss_hitwhere$")

def path_tag(file_path: Path) -> str: 
    return "_".join(file_path.parent.parts)

def parse_csv_line(line: str) -> List[str]:
    reader = csv.reader([line])
    return next(reader)

def main(root_dir="", raw_out_csv="stats_hitwhere_dynamic.csv", summary_out_csv="stats_hitwhere_summary.csv"):
    if not root_dir:
        root_dir = "."
    
    root = Path(root_dir).resolve()
    stats_files: List[Path] = list(root.rglob("proposed.csv"))
    print(f"Searching in {root}. Files found: {len(stats_files)}")

    rows: List[Dict] = []
    all_unique_headers: Set[str] = set()
    
    # --- Pass 1: Collect Data from all files into a list of dictionaries ---
    for f in stats_files:
        tag = path_tag(f)
        with f.open("r", encoding="utf-8", errors="ignore") as fp:
            current_headers: Optional[List[str]] = None
            current_level: Optional[str] = None
            
            for line in fp:
                line = line.strip()
                if HITWHERE_LINE_RE.match(line):
                    line_parts = parse_csv_line(line)
                    
                    # Heuristic check for header line definition
                    is_header_def = len(line_parts) > 1 and not line_parts[1].isdigit()

                    if is_header_def:
                        current_headers = line_parts
                        m = METRIC_LEVEL_RE.match(current_headers[0]) # Fix applied here
                        if m:
                            current_level = m.group(1)
                            all_unique_headers.update(current_headers[1:])
            
                    elif current_headers and current_level:
                        value_data = line_parts
                        if len(current_headers) != len(value_data):
                            print(f"Warning: Length mismatch in {f.name} (L{current_level}). Skipping line.")
                            continue

                        standard_row: Dict[str, str] = {"folder_tag": tag, "level": current_level}
                        labels = current_headers[1:]
                        values = value_data[1:]
                        
                        for label, value in zip(labels, values):
                            standard_row[label] = value
                        rows.append(standard_row)
                        
                        current_headers = None
                        current_level = None

    # --- Pass 2: Write raw data to a single CSV ---
    if not rows:
        print("No data rows collected. Exiting.")
        return

    output_fieldnames = ["folder_tag", "level"] + sorted(list(all_unique_headers))
    print(f"Writing {len(rows)} raw standardized rows to {raw_out_csv}")
    with open(raw_out_csv, "w", encoding="utf-8", newline='') as out:
        writer = csv.DictWriter(out, fieldnames=output_fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    # --- Pass 3: Calculate and write Averages/Totals using Pandas ---
    df = pd.DataFrame(rows)
    
    # Identify the columns that contain numeric values (the metrics we want to average)
    metric_columns = sorted(list(all_unique_headers))

    # Convert metric columns from string to numeric (errors='coerce' turns non-numbers into NaN)
    for col in metric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Calculate Application-wise and Level-wise averages and totals
    summary_df = df.groupby(['level'])[metric_columns].agg(['sum', 'mean'])

    # Flatten the multi-level column index for a cleaner CSV output
    summary_df.columns = ['{}_{}'.format(col[0], col[1]) for col in summary_df.columns]
    summary_df = summary_df.reset_index() # Makes folder_tag and level normal columns again

    print(f"Writing summary statistics to {summary_out_csv}")
    summary_df.to_csv(summary_out_csv, index=False)
    
    print("Done with all processing.")


if __name__ == "__main__":
    # Ensure only the path string is passed, not the entire sys.argv list
    if len(sys.argv) > 1:
        input_dir = sys.argv[1] 
    else:
        input_dir = "." 
        
    main(root_dir=input_dir)
