import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import sys

# Load the data
path = sys.argv[1]
df = pd.read_csv(path, sep=r'\s+', engine='python')

# 1. Map and Filter
level_map = {'L1': 'PML4', 'L2': 'PDPT', 'L3': 'PD', 'L4': 'PT'}
df['level'] = df['level'].map(level_map)
df = df[df['level'].isin(['PDPT', 'PD'])]

# 2. Normalize to 100%
df['total'] = df['hits'] + df['misses']
df['hit_pct'] = (df['hits'] / df['total']) * 100
df['miss_pct'] = (df['misses'] / df['total']) * 100

# 3. Calculate Global Overall Average
global_avg = df.groupby('level', observed=True)[['hit_pct', 'miss_pct']].mean().reset_index()
global_avg['workload'] = 'mean'

# 4. Prepare Final DataFrame
plot_df = pd.concat([
    df[['workload', 'level', 'hit_pct', 'miss_pct']].rename(columns={'hit_pct': 'hits', 'miss_pct': 'misses'}),
    global_avg[['workload', 'level', 'hit_pct', 'miss_pct']].rename(columns={'hit_pct': 'hits', 'miss_pct': 'misses'})
])

workload_order = list(df['workload'].unique()) + ['mean']
plot_df['workload'] = pd.Categorical(plot_df['workload'], categories=workload_order, ordered=True)
plot_df['level'] = pd.Categorical(plot_df['level'], categories=['PDPT', 'PD'], ordered=True)
df_final = plot_df.set_index(['workload', 'level']).sort_index()

# 5. Plotting (Default colors used here)
fig, ax = plt.subplots(figsize=(18, 9))

# Plotting without the 'color' argument to use Matplotlib defaults
df_final[['hits', 'misses']].plot(kind='bar', stacked=True, ax=ax, width=0.8)

# 6. Add numbers inside bars
for c in ax.containers:
    labels = [f'{v.get_height():.1f}%' if v.get_height() > 5 else '' for v in c]
    ax.bar_label(c, labels=labels, label_type='center', color='white', fontweight='bold', fontsize=9)

# 7. Nested X-Axis Labels & Separators
ax.set_xticklabels([lvl for wl, lvl in df_final.index], rotation=0)
workloads = df_final.index.get_level_values(0).unique()
level_count = 2

for i, wl in enumerate(workloads):
    pos = (i * level_count) + (level_count - 1) / 2
    ax.annotate(wl, xy=(pos, 0), xycoords='data', xytext=(0, -35), textcoords='offset points',
                ha='center', va='top', fontsize=10, fontweight='bold', 
                color='darkblue' if wl == 'mean' else 'black')
    if i > 0:
        plt.axvline(x=i*level_count - 0.5, color='black', linestyle='-', alpha=0.1)

# 8. Legend Fix: Extract the colors used by Matplotlib automatically
# This ensures the legend always matches the default bars
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, ['Hits', 'Misses'], loc='upper right', frameon=True, fontsize=12)

# Final Styling
ax.set_ylim(0, 100)
ax.set_ylabel("Hit and Miss Percentage (%)", fontsize=12)
ax.set_title("", fontsize=15, pad=20)
ax.set_xlabel("")

plt.tight_layout()
plt.subplots_adjust(bottom=0.2)
plt.show()
