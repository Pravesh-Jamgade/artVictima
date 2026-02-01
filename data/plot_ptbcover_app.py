import pandas as pd
import matplotlib.pyplot as plt
import io

# Data setup
data = """
Workload	PTB-MISS_PDPT-MISS	PTB-MISS_PDPT-HIT	PTB-HIT_PDPT-MISS	PTB-HIT_PDPT-HIT
dlrm	19	0	34360926	1441489
pr	18	0	16994186	2301520
cc	18	0	41042755	2122952
sssp	763653	222	18401537	13909628
gc	4570782	10124	24419022	2622798
tc	9	0	1183285	2208679
xs	11	0	2172201	5204235
rnd	2	0	0	35551229
bfs	19	0	34002093	1441858
bc	94400	32	2334501	3173655
gen	4570762	10136	24426880	2623492
"""

df = pd.read_csv(io.StringIO(data), sep=r'\s+')

# 1. Map column names and set index
level_map = {
    'PTB-MISS_PDPT-MISS': 'PTB Miss PDPT Miss', 
    'PTB-MISS_PDPT-HIT': 'PTB Miss PDPT Hit', 
    'PTB-HIT_PDPT-MISS': 'PTB Hit PDPT Miss', 
    'PTB-HIT_PDPT-HIT': 'PTB Hit PDPT Hit'
}
df = df.rename(columns=level_map)
df.set_index('Workload', inplace=True)

# 2. Calculate Average and append as a new row
avg_row = df.mean().to_frame().T
avg_row.index = ['mean']
df = pd.concat([df, avg_row])

# 3. Normalize to 100%
df_percent = df.div(df.sum(axis=1), axis=0) * 100

# 4. Plotting
ax = df_percent.plot(kind='bar', stacked=True, figsize=(14, 8), width=0.7)

# Position Legend ABOVE the chart
ax.legend(
    loc='lower center', 
    bbox_to_anchor=(0.5, 1.09), 
    ncol=4,             
    fontsize=10, 
    frameon=False       
)

# Customization
plt.ylabel('Fraction of PDPT PSC Misses Resolved by PTB (%)', fontsize=12)
plt.xlabel('Workload', fontsize=12)
plt.xticks(rotation=0)

# 5. Add numbers inside the bars
for c in ax.containers:
    # Logic: Show label only if height > 3% to avoid clutter
    labels = [f'{v.get_height():.1f}%' if v.get_height() > 3 else '' for v in c]
    ax.bar_label(c, labels=labels, label_type='center', fontsize=9, fontweight='bold')

plt.tight_layout(rect=[0, 0, 1, 0.95]) 
plt.show()
