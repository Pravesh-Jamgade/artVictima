import pandas as pd
import matplotlib.pyplot as plt
import io

# Data setup
data = """
Workload,PTB-MISS_PDPT-MISS,PTB-MISS_PDPT-HIT,PTB-HIT_PDPT-MISS,PTB-HIT_PDPT-HIT
dlrm,19,0,34350273,1441558
pr,18,0,16994916,2301638
cc,18,0,36077187,7065207
sssp,763639,223,18255056,13896388
gc,4570576,10149,24430753,2623111
tc,9,0,1183286,2208679
xs,11,0,2172203,5204241
rnd,2,0,0,35550382
bfs,19,0,34503701,1441598
bc,94400,32,2334501,3173652
gen,4570673,10137,24431000,2622267
"""

df = pd.read_csv(io.StringIO(data), sep=',')

# 1. Map column names and set index
level_map = {
    'PTB-MISS_PDPT-MISS': 'PTB-Miss, PDPT-Miss', 
    'PTB-MISS_PDPT-HIT': 'PTB-Miss, PDPT-Hit', 
    'PTB-HIT_PDPT-MISS': 'PTB-Hit, PDPT-Miss', 
    'PTB-HIT_PDPT-HIT': 'PTB-Hit, PDPT-Hit'
}
df = df.rename(columns=level_map)
df.set_index('Workload', inplace=True)

# 2. Calculate Mean and append
avg_row = df.mean().to_frame().T
avg_row.index = ['mean']
df = pd.concat([df, avg_row])

# 3. Normalize to 100%
df_percent = df.div(df.sum(axis=1), axis=0) * 100

# 4. Plotting - ISCA/MICRO Style (Compact and High-Viz)
fig, ax = plt.subplots(figsize=(14, 5))

# Professional Palette and Hatches
colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B3', '#DD8452']
hatches = ['', '//', '..', 'xx', '\\\\', '--']


# Plot bars
df_percent.plot(kind='bar', stacked=True, ax=ax, width=0.75, edgecolor='black', zorder=3, color=colors)

# 5. Apply Hatches to bars
for i, patch_group in enumerate(ax.containers):
    hatch = hatches[i]
    for patch in patch_group:
        patch.set_hatch(hatch)

# 6. High-Visibility Formatting
plt.ylabel('Coverage (%)', fontsize=18, fontweight='bold')
plt.xlabel('', fontsize=1) # Minimal X-label space
plt.xticks(rotation=45, ha='right', fontsize=16)
plt.yticks(fontsize=16)

# Position Legend ABOVE the chart with hatch patterns visible
handles, labels = ax.get_legend_handles_labels()
ax.legend(
    handles=handles,
    labels=labels,
    loc='lower center', 
    bbox_to_anchor=(0.5, 1.12), 
    ncol=2,             # 2x2 grid for readability
    fontsize=14, 
    frameon=False,
    columnspacing=1.5
)

# Visual polish
plt.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
ax.set_axisbelow(True)

plt.tight_layout(rect=[0, 0, 1, 0.95]) 
plt.show()
