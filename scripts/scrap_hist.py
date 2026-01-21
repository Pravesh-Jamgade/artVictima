#!/usr/bin/env python3
import csv
import re
from pathlib import Path
import sys
from typing import List, Dict, Optional, Tuple

# Regex to check if a line is a header definition line
HEADER_LINE_RE = re.compile(r"^proposed_PSC_L2_miss_latency_cycles(?:,\[\d+\.\.\d+\])+$")

# Regex to check if a line is a data line (starts with a folder path)
DATA_LINE_RE = re.compile(r"^proposed_PSC_L2_miss_latency_cycles(?:,\d+)*$")
LEVEL_RE = re.compile(r"^proposed_PSC_L(\d+)_miss_latency_cycles$")

# The unified, desired final output header collection
TARGET_HEADERS = [
    "folder_tag", "level", "0..1", "2..3", "4..7", "8..15", "16..31",
    "32..63", "64..127", "128..255", "256..511", "512..1023", "1024..2047"
]

def path_tag(file_path: Path) -> str: 
    return "_".join(file_path.parent.parts)

# Helper function to parse a line of data/headers into a list of non-empty strings
def parse_csv_line(line: str) -> List[str]:
    # Use the csv module's reader for robust parsing of commas and empty fields
    reader = csv.reader([line])
    return next(reader)


def main(root_dir="", out_csv="stats_histLatency.csv"):
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
            
            from_header_level_number = -1
            from_value_level_number = -1
            for line in fp:
                line = line.strip()

                if HEADER_LINE_RE.match(line):
                    # This is a header definition line. Store it.
                    current_header_data = parse_csv_line(line)
                    m = LEVEL_RE.match(current_header_data[0])  
                    if m:
                        from_header_level_number = m.group(1)

                if DATA_LINE_RE.match(line):
                    # This is a value row line. Process it.
                    if not current_header_data:
                        print(f"Warning: Data line found in {f.name} without a preceding header line.")
                        continue
                    
                    m = LEVEL_RE.match(current_header_data[0])  
                    if m:
                        from_value_level_number = m.group(1)
                    
                    value_data = parse_csv_line(line)

                    # Ensure headers and values match in length for processing
                    if len(current_header_data) != len(value_data) or (from_header_level_number != from_value_level_number):
                        print(f"Warning: Header/Value mismatch in {f.name}. Skipping line.")
                        continue

                    # Extract the fixed metadata (folder_tag, level)
                    folder_tag = tag#value_data[0]
                    level = from_header_level_number

                    # Create a standard dictionary that matches our TARGET_HEADERS format
                    standard_row = {header: "" for header in TARGET_HEADERS}
                    standard_row["folder_tag"] = folder_tag
                    standard_row["level"] = level

                    # Iterate through the input file's specific columns
                    # Start from index 2 to skip the metadata columns in the input
                    for i in range(1, len(value_data)):
                        input_bin_name_raw = current_header_data[i]
                        input_value = value_data[i]

                        # Clean up the bin name (remove brackets if present, though csv.reader might handle this)
                        input_bin_name = input_bin_name_raw.strip('[]')

                        # If a value exists for this bin in the input line, map it to the standard header
                        if input_value and input_bin_name in TARGET_HEADERS:
                            standard_row[input_bin_name] = input_value
                    
                    rows.append(standard_row)
                    # The header might change for the next block, so we clear it
                    current_header_data = None


    # --- Pass 2: Write all collected data to a single CSV ---
    print(f"Writing {len(rows)} standardized rows to {out_csv}")

    with open(out_csv, "w", encoding="utf-8", newline='') as out:
        writer = csv.DictWriter(out, fieldnames=TARGET_HEADERS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    print("Done.")


if __name__ == "__main__":
    # Get directory from command line arguments or use current dir if none provided
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir, out_csv="stats_histLatency.csv")
