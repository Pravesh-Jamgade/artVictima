import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
from scipy.stats import gmean

# --- 1. DATA PREPARATION ---
data = """design_workload,level,L1,L2,dram-local,nuca-cache
baseline_dlrm,3,12457246,16687313,1387413,12
baseline_dlrm,4,2189826,12350822,20728525,768
baseline_pr,3,5212751,9070316,73158,0
baseline_pr,4,2702603,5549293,10633617,4
baseline_cc,3,14900195,20378763,1378965,27
baseline_cc,4,2675507,15488556,24288377,43
baseline_sssp,3,4141399,4383487,7818365,113
baseline_sssp,4,4123327,4371368,23858657,105
baseline_gc,3,6827744,14116972,5217541,2810
baseline_gc,4,1549703,11165852,18251653,3689
baseline_tc,3,1090628,1959147,5331,0
baseline_tc,4,176828,447408,2731411,12
baseline_xs,3,1673588,695935,98849,10
baseline_xs,4,346201,3727245,3294724,864
baseline_rnd,3,25439206,7652952,385,4
baseline_rnd,4,215186,17416633,17891271,41
baseline_bfs,3,12527034,16778649,1381470,48
baseline_bfs,4,2188342,12399134,20828102,272
baseline_bc,3,1006687,573323,1360292,377
baseline_bc,4,772413,608496,4118553,266
baseline_gen,3,6957533,13976209,5237259,3450
baseline_gen,4,1553932,11163925,18270438,4298"""

df = pd.read_csv(io.StringIO(data)).fillna(0)
df['Workload'] = df['design_workload'].str.split('_', n=1).str[-1]
cols = ['L1', 'L2', 'dram-local', 'nuca-cache']

# --- 2. GEOMEAN CALCULATION ---
def get_norm_gmean(lvl):
    subset = df[df['level'] == lvl][cols].replace(0, 1e-9)
    gm = gmean(subset, axis=0)
    return (gm / np.sum(gm)) * 100

gm3, gm4 = get_norm_gmean(3), get_norm_gmean(4)

# --- 3. DATAFRAME PROCESSING ---
df_pct = df.copy()
df_pct[cols] = df_pct[cols].div(df_pct[cols].sum(axis=1), axis=0) * 100
df_pct['X'] = df_pct['Workload'] + " (K" + df_pct['level'].astype(str) + ")"
plot_df = df_pct.set_index('X')[cols]

# Append Geomeans
plot_df.loc['Geomean (K3)'] = gm3
plot_df.loc['Geomean (K4)'] = gm4

# --- 4. PLOTTING ---
plt.rcParams.update({'font.size': 18, 'font.family': 'sans-serif'})
fig, ax = plt.subplots(figsize=(18, 6))

colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B3']
hatches = ['', '//', '..', 'xx']

# Plotting
plot_df.plot(kind='bar', stacked=True, ax=ax, width=0.8, edgecolor='black', zorder=3, color=colors)

# Apply Hatches
for i, container in enumerate(ax.containers):
    h = hatches[i % len(hatches)]
    for patch in container:
        patch.set_hatch(h)

# Legend Formatting
handles, labels = ax.get_legend_handles_labels()
ax.legend(
    handles=handles, 
    labels=["L1 Hit", "L2 Hit", "DRAM Hit", "NUCA Hit"],
    loc='lower center', bbox_to_anchor=(0.5, 1.15), 
    ncol=4, fontsize=20, frameon=False
)

# Visual Aesthetics
ax.set_ylabel('Fraction of Hits (%)', fontsize=22, fontweight='bold')
ax.set_xlabel('')
plt.xticks(rotation=45, ha='right', fontsize=16)
plt.yticks(fontsize=18)
plt.ylim(0, 100)
ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

# Add separator for Geomean
ax.axvline(x=len(plot_df)-2.5, color='black', linestyle='-', linewidth=2, alpha=0.8)

plt.tight_layout()
plt.show()

# --- 5. PRINT STATISTICS (FOR CAPTION/RESULTS) ---
print("-" * 60)
print(f"{'Metric':<20} | {'Geomean K3 (%)':<15} | {'Geomean K4 (%)':<15} | {'Delta'}")
print("-" * 60)
for i, col in enumerate(cols):
    delta = gm4[i] - gm3[i]
    print(f"{col:<20} | {gm3[i]:>14.2f}% | {gm4[i]:>14.2f}% | {delta:>+6.2f}%")
print("-" * 60)
