#!/usr/bin/env python3
import csv
import re
import sys
from pathlib import Path
from statistics import geometric_mean
from collections import defaultdict

# --- Regex Patterns ---
# Captures power for specific components: cache, dram, and total
COMP_STDOUT_RE = re.compile(r"^(cache|dram|total)\s+([\d.]+)\s+W")

# Performance metrics from sim.stats
FREQ_RE = re.compile(r"corefreq\s*=\s*([\d.]+)")
CYC_RE  = re.compile(r"performance_model\.cycle_count\s*=\s*([\d.]+)")
IPC_RE  = re.compile(r"ipc\s*=\s*([\d.]+)")

def main(root_dir="", out_csv="system_metrics_summary.csv"):
    root = Path(root_dir or ".").resolve()
    skip_list = {"gen", "gc", "sssp"}
    target_comps = ["cache", "dram", "total"]
    
    experiment_groups = defaultdict(list)

    # --- STEP 1: COLLECTION ---
    for stdout_path in root.rglob("sim.stdout"):
        folder = stdout_path.parent
        if any(skip in folder.name.lower() for skip in skip_list):
            continue

        relative_path = folder.relative_to(root)
        exp_root = relative_path.parts[0] if relative_path.parts else "root"

        stats_path = folder / "sim.stats"
        record = {
            "folder_tag": "_".join(folder.parts[-2:]),
            "ipc": 0.0, "freq": 0.0, "cycles": 0.0,
            **{f"{c}_w": 0.0 for c in target_comps}
        }

        # Parse Power (sim.stdout)
        with stdout_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if match := COMP_STDOUT_RE.search(line.strip()):
                    comp_name = match.group(1)
                    record[f"{comp_name}_w"] = float(match.group(2))

        # Parse Stats (sim.stats)
        if stats_path.exists():
            content = stats_path.read_text(encoding="utf-8", errors="ignore")
            if m := FREQ_RE.search(content): record["freq"] = float(m.group(1))
            if m := CYC_RE.search(content):  record["cycles"] = float(m.group(1))
            if m := IPC_RE.search(content):  record["ipc"] = float(m.group(1))
        
        # Calculations
        freq = record.get("freq", 0.0)
        cycles = record.get("cycles", 0.0)
        ipc = record.get("ipc", 0.0)
        time_s = (cycles / freq) if freq > 0 else 0.0
        
        for c in target_comps:
            pwr = record.get(f"{c}_w", 0.0)
            record[f"{c}_ppw"] = (ipc / pwr) if pwr > 0 else 0.0
            record[f"{c}_edp"] = pwr * (time_s ** 2)
        
        experiment_groups[exp_root].append(record)

    # --- STEP 2: SUMMARY PRINTING ---
    print(f"\n{'Experiment Root':<30} | {'Total EDP Geomean':<20}")
    print("-" * 55)

    for exp_name, runs in sorted(experiment_groups.items()):
        # Calculate Geomean based on the 'total' component EDP
        total_edps = [r["total_edp"] for r in runs if r["total_edp"] > 0]
        root_geomean = geometric_mean(total_edps) if total_edps else 0.0
        print(f"{exp_name:<30} | {root_geomean:<20.6e}")

    # --- STEP 3: EXPORT ---
    all_flattened = [run for runs in experiment_groups.values() for run in runs]
    
    headers = ["folder_tag", "ipc"]
    for c in target_comps:
        headers.extend([f"{c}_w", f"{c}_ppw", f"{c}_edp"])

    with open(out_csv, "w", encoding="utf-8", newline='') as out:
        writer = csv.DictWriter(out, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_flattened)

if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir=input_dir)
