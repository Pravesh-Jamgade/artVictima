import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
from scipy.stats import gmean

# --- 1. DATA PREPARATION ---
raw_baseline = """design_workload level L2 L3 DRAM
baseline_dlrm 4 14872993 201 20420450
baseline_pr 4 8181440 25 10704048
baseline_cc 4 18030700 571 24400849
baseline_tc 4 631510 6 2724143
baseline_xs 4 4111298 1046 3256781
baseline_rnd 4 17742147 35439 17747453
baseline_bfs 4 14892138 343 20531507
baseline_bc 4 1370648 519 4128564"""

raw_vikram = """design_workload level L2 L3 DRAM
vikram_dlrm 4 31992926 1344862 2141972
vikram_pr 4 15988235 73281 2824019
vikram_cc 4 38755202 1286307 2361649
vikram_tc 4 2993780 7741 354138
vikram_xs 4 5125738 97406 2145950
vikram_rnd 4 34491583 2642 1029607
vikram_bfs 4 31528912 1346565 2056240
vikram_bc 4 2451968 1338595 1709164"""

cols = ['L2', 'L3', 'DRAM']

def get_processed_df(raw_str, design_name):
    # Be defensive: skip malformed/non-tabular lines (e.g., simulator *ERROR* log lines)
    # instead of failing with a parser traceback.
    df = pd.read_csv(
        io.StringIO(raw_str),
        sep=r'\s+',
        engine='python',
        on_bad_lines='skip'
    )

    required = {'design_workload', *cols}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(
            f"Input for {design_name} is missing required columns: {sorted(missing)}. "
            "Check that the input contains a clean whitespace-separated table with "
            "header: design_workload level L2 L3 DRAM."
        )

    # Ensure we only keep valid rows
    df = df[df['design_workload'].astype(str).str.contains('_', na=False)].copy()
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
    df = df.dropna(subset=cols)

    if df.empty:
        raise ValueError(f"No valid rows found for {design_name} after filtering malformed input lines.")

    df['Workload'] = df['design_workload'].str.split('_').str[-1]
    df[cols] = df[cols].div(df[cols].sum(axis=1), axis=0) * 100
    
    # Geomean Calculation
    subset = df[cols].replace(0, 1e-9)
    gm = gmean(subset, axis=0)
    gm_norm = (gm / np.sum(gm)) * 100
    
    res = df.set_index(['Workload', 'design_workload'])[cols].sort_index()
    res.loc[('Geomean', 'Geomean_' + design_name), :] = gm_norm
    return res

df_b = get_processed_df(raw_baseline, 'Baseline')
df_v = get_processed_df(raw_vikram, 'Vikram')

# Reorder to ensure Geomean is last
final_df = pd.concat([df_b, df_v])
workloads = [w for w in final_df.index.get_level_values(0).unique() if w != 'Geomean'] + ['Geomean']
final_df = final_df.reindex(workloads, level=0)

# --- PRINT SUMMARY ---
print("\n--- GEOMEAN SUMMARY (%) ---")
print(final_df.xs('Geomean', level=0).round(2))

# --- 2. PLOTTING ---
plt.rcParams.update({'font.size': 16})
fig, ax = plt.subplots(figsize=(18, 8))

colors = ['#4C72B0', '#55A868', '#C44E52']
hatches = ['', '//', '..']

final_df.plot(kind='bar', stacked=True, ax=ax, width=0.85, edgecolor='black', color=colors, zorder=3)

# Legend Formatting
handles, labels = ax.get_legend_handles_labels()
new_labels = ["L2 Hit", "L3 Hit", "DRAM Hit"]
leg = ax.legend(handles, new_labels, loc='upper center', bbox_to_anchor=(0.5, 1.12), ncol=3, frameon=False, fontsize=18)

for i, patch in enumerate(leg.get_patches()):
    patch.set_hatch(hatches[i])

for i, container in enumerate(ax.containers):
    for patch in container:
        patch.set_hatch(hatches[i])

# --- X-AXIS LABELING FIX ---
ax.set_xlabel('')
ax.set_xticklabels([])
ax.set_ylabel('Fraction of Hits (%)', fontsize=20, fontweight='bold')
ax.set_ylim(0, 100)

for i, wl in enumerate(workloads):
    pos_center = i * 2 + 0.5
    # Main Workload Label
    ax.text(pos_center, -12, wl.upper(), ha='center', va='top', fontweight='bold', fontsize=14)
    # B/V Sub-labels
    ax.text(i * 2, -3, 'B', ha='center', va='top', fontsize=12, alpha=0.7)
    ax.text(i * 2 + 1, -3, 'V', ha='center', va='top', fontsize=12, alpha=0.7)

    if i < len(workloads) - 1:
        ax.axvline(x=i * 2 + 1.5, color='black', alpha=0.1, lw=1)

# --- RELATIVE IMPROVEMENT CALCULATION ---
gm_summary = final_df.xs('Geomean', level=0)
b_gm = gm_summary.iloc[0] # Baseline Geomean
v_gm = gm_summary.iloc[1] # Vikram Geomean

print("\n--- RELATIVE ANALYSIS (VIKRAM vs BASELINE) ---")
# 1. Fold increase in L2 Hit Rate
l2_improvement = v_gm['L2'] / b_gm['L2']
print(f"L2 Hit Rate Increase: {l2_improvement:.2f}x")

# 2. Reduction in DRAM traffic (Lower is better)
dram_reduction = (b_gm['DRAM'] - v_gm['DRAM']) / b_gm['DRAM'] * 100
print(f"DRAM Traffic Reduction: {dram_reduction:.2f}%")

# 3. L3 Utilization Factor
l3_factor = v_gm['L3'] / b_gm['L3']
print(f"L3 Utilization Increase: {l3_factor:.2f}x")

plt.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
plt.tight_layout()
plt.show()
