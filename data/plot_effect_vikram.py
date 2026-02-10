import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
from scipy.stats import gmean

# --- 1. DATA PREPARATION ---
raw_baseline = """design_workload,level,L1,L2,dram-local,nuca-cache
baseline_dlrm,4,2189826,12350822,20728525,768
baseline_pr,4,2702603,5549293,10633617,4
baseline_cc,4,2675507,15488556,24288377,43
baseline_sssp,4,4123327,4371368,23858657,105
baseline_gc,4,1549703,11165852,18251653,3689
baseline_tc,4,176828,447408,2731411,12
baseline_xs,4,346201,3727245,3294724,864
baseline_rnd,4,215186,17416633,17891271,41
baseline_bfs,4,2188342,12399134,20828102,272
baseline_bc,4,772413,608496,4118553,266
baseline_gen,4,1553932,11163925,18270438,4298"""

raw_vikram = """design_workload,level,L1,L2,dram-local,nuca-cache
vikram_both_dlrm,4,13137537,19036258,3101751,1694
vikram_both_pr,4,7313909,8798762,2772662,199
vikram_both_cc,4,15727318,23234895,3569146,1389
vikram_both_sssp,4,8019491,7643060,16605694,434
vikram_both_gc,4,7979371,16501233,6530667,2722
vikram_both_tc,4,1191115,1922419,242101,24
vikram_both_xs,4,1955387,3136741,2276131,768
vikram_both_rnd,4,25228927,9042389,1251376,9
vikram_both_bfs,4,13319781,19017637,3091646,1444
vikram_both_bc,4,1702193,913768,2883485,274
vikram_both_gen,4,8005693,16510387,6496190,2767"""

cols = ['L1', 'L2', 'dram-local', 'nuca-cache']

def get_processed_df(raw_str, design_name):
    df = pd.read_csv(io.StringIO(raw_str)).fillna(0)
    df['Workload'] = df['design_workload'].str.split('_').str[-1]
    df[cols] = df[cols].div(df[cols].sum(axis=1), axis=0) * 100
    subset = df[cols].replace(0, 1e-9)
    gm = gmean(subset, axis=0)
    gm_norm = (gm / np.sum(gm)) * 100
    res = df.set_index(['Workload', 'design_workload'])[cols]
    res.loc[('Geomean', 'Geomean_' + design_name), :] = gm_norm
    return res

df_b = get_processed_df(raw_baseline, 'Baseline')
df_v = get_processed_df(raw_vikram, 'Vikram')
final_df = pd.concat([df_b, df_v]).sort_index()

# --- 2. PLOTTING ---
plt.rcParams.update({'font.size': 20}) # Global font increase
fig, ax = plt.subplots(figsize=(20, 7)) 

# Colors and 6 Hatches
colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B3', '#DD8452']
hatches = ['', '//', '..', 'xx', '\\\\', '--']

final_df.plot(kind='bar', stacked=True, ax=ax, width=0.85, edgecolor='black', zorder=3, color=colors)

# ... (rest of your data processing code) ...

# --- 2. PLOTTING ---
plt.rcParams.update({'font.size': 20}) 
fig, ax = plt.subplots(figsize=(22, 8)) # Increased size for clarity

# Plot
final_df.plot(kind='bar', stacked=True, ax=ax, width=0.85, edgecolor='black', zorder=3, color=colors)

# 1. REMOVE THE INDEX NAMES ('Workload', 'design_workload')
ax.set_xlabel('') 
ax.set_xticklabels([]) 


# Apply patterns
for i, container in enumerate(ax.containers):
    for patch in container:
        patch.set_hatch(hatches[i])

ax.set_xticklabels([]) 

# Add Large Centered Labels
workloads = final_df.index.get_level_values(0).unique()
for i, wl in enumerate(workloads):
    pos = i * 2 + 0.5 
    # Workload names
    ax.text(pos, -8, wl, ha='center', va='top', fontsize=20, fontweight='bold')
    # B/V Indicators
    ax.text(i * 2, -2, 'B', ha='center', va='top', fontsize=16)
    ax.text(i * 2 + 1, -2, 'V', ha='center', va='top', fontsize=16)

# Visual Grouping
for i in range(1, len(workloads)):
    ax.axvline(x=i*2 - 0.5, color='black', linestyle='-', linewidth=1.5, alpha=0.3, zorder=1)

# Large Formatting
ax.set_ylabel('Fraction of Hits (%)', fontsize=22, fontweight='bold')
ax.tick_params(axis='y', labelsize=20)
ax.set_ylim(0, 100)

# Large Legend
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles=handles, labels=["L1 Hit", "L2 Hit", "DRAM Hit", "NUCA Hit"],
          loc='lower center', bbox_to_anchor=(0.5, 1.05), 
          ncol=4, fontsize=20, frameon=False)

plt.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
plt.tight_layout()
plt.show()
