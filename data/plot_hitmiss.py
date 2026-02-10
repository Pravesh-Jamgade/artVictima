import pandas as pd
import matplotlib.pyplot as plt
import sys
from scipy.stats import gmean
import numpy as np

# Load the data
if len(sys.argv) < 2:
    print("Usage: python script.py data.csv")
    sys.exit(1)

path = sys.argv[1]
df = pd.read_csv(path, sep=r',', engine='python')

# 1. Map and Filter
level_map = {'L1': 'PML4', 'L2': 'PDPT', 'L3': 'PD', 'L4': 'PT'}
df['level'] = df['level'].map(level_map)
df = df[df['level'].isin(['PDPT', 'PD'])]

# 2. Normalize to 100%
df['total'] = df['hits'] + df['misses']
df['hit_pct'] = (df['hits'] / df['total']) * 100
df['miss_pct'] = (df['misses'] / df['total']) * 100

# 3. Calculate Global Geometric Mean
# We replace 0 with a negligible value to avoid math errors in gmean
def calculate_normalized_gmean(group):
    # Calculate raw gmean for hits and misses
    gm_vals = gmean(group[['hit_pct', 'miss_pct']].replace(0, 1e-9), axis=0)
    # Re-normalize so the sum is exactly 100%
    return (gm_vals / np.sum(gm_vals)) * 100

# Group by level and apply gmean
global_avg_vals = df.groupby('level', observed=True).apply(calculate_normalized_gmean)
global_avg = pd.DataFrame(global_avg_vals.tolist(), columns=['hit_pct', 'miss_pct'])
global_avg['level'] = global_avg_vals.index
global_avg['workload'] = 'Geomean'

# 4. Prepare Final DataFrame
plot_df = pd.concat([
    df[['workload', 'level', 'hit_pct', 'miss_pct']].rename(columns={'hit_pct': 'hits', 'miss_pct': 'misses'}),
    global_avg[['workload', 'level', 'hit_pct', 'miss_pct']].rename(columns={'hit_pct': 'hits', 'miss_pct': 'misses'})
])

# Ensure Geomean is the last category
workload_order = list(df['workload'].unique()) + ['Geomean']
plot_df['workload'] = pd.Categorical(plot_df['workload'], categories=workload_order, ordered=True)
plot_df['level'] = pd.Categorical(plot_df['level'], categories=['PDPT', 'PD'], ordered=True)
df_final = plot_df.set_index(['workload', 'level']).sort_index()

# 5. ISCA/MICRO Plotting Style
plt.rcParams.update({'font.size': 14})
fig, ax = plt.subplots(figsize=(16, 5))

# Professional Palette
colors = ['#4C72B0', '#DD8452']
df_final[['hits', 'misses']].plot(kind='bar', stacked=True, ax=ax, 
                                  width=0.85, edgecolor='black', zorder=3) #, color=colors

# 6. Add numbers inside bars
for c in ax.containers:
    labels = [f'{v.get_height():.0f}%' if v.get_height() > 10 else '' for v in c]
    ax.bar_label(c, labels=labels, label_type='center', color='white', 
                 fontweight='bold', fontsize=11)

# 7. Nested X-Axis Labels & Separators
ax.set_xticklabels([lvl for wl, lvl in df_final.index], rotation=0, fontsize=12)

workloads = df_final.index.get_level_values(0).unique()
level_count = 2

for i, wl in enumerate(workloads):
    pos = (i * level_count) + (level_count - 1) / 2
    ax.annotate(wl, xy=(pos, 0), xycoords='data', xytext=(0, -25), textcoords='offset points',
                ha='center', va='top', fontsize=14, fontweight='bold', 
                color='darkred' if wl == 'Geomean' else 'black')
    if i > 0:
        ax.axvline(x=i*level_count - 0.5, color='black', linestyle='-', linewidth=1.5, alpha=0.2, zorder=1)

# 8. Legend (Flattened Top)
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, ['Hits', 'Misses'], 
          loc='lower center', bbox_to_anchor=(0.5, 1.05),
          ncol=2, frameon=False, fontsize=16, columnspacing=2)

# Final Styling
ax.set_ylim(0, 100)
ax.set_ylabel("Distribution (%)", fontsize=16, fontweight='bold')
ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
ax.set_axisbelow(True)

plt.tight_layout(rect=[0, 0, 1, 0.98])
plt.subplots_adjust(bottom=0.18)
plt.show()
