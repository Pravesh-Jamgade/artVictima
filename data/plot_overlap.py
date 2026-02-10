import pandas as pd
import matplotlib.pyplot as plt
import io
from scipy.stats import gmean

# 1. Data Prep
data = """
benchmark	overlap_samples	overlap_latency
dlrm	0.5724	0.7456
pr	0.7651	0.8464
cc	0.432	0.6453
sssp	0.4552	0.6335
gc	0.7061	0.857
tc	0.8426	0.9441
xs	0.5205	0.7497
rnd	0.033	0.1973
bfs	0.5688	0.7439
bc	0.5192	0.6711
gen	0.706	0.857
"""
df = pd.read_csv(io.StringIO(data), sep=r"\s+")
df.set_index("benchmark", inplace=True)

# Append Geomean
df.loc['geomean'] = df.apply(gmean)

# 2. Compact Plotting (ISCA/MICRO Style)
# Height set to 4.2 for a very dense, publication-ready look
fig, ax = plt.subplots(figsize=(14, 4.2))

# Professional Palette and Hatches
colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B3', '#DD8452']
hatches = ['', '//', '..', 'xx', '\\\\', '--']


# Plotting - removing hatches, using solid professional colors
df.plot(kind='bar', ax=ax, width=0.8, 
        edgecolor='black', linewidth=0.8, zorder=3, color=colors) 


# 3. ADDING VALUE LABELS & HATCHES
for i, container in enumerate(ax.containers):
    # Set hatch for each bar group
    for patch in container:
        patch.set_hatch(hatches[i])

# 3. Reference Lines & Forced Y-axis Labels
y_ticks = [0, 0.25, 0.5, 0.75, 1.0]
plt.yticks(y_ticks, fontsize=18)
plt.ylim(0, 1.05)

for y_val in y_ticks[1:]:
    plt.axhline(y=y_val, color='black', linestyle='--', linewidth=1.0, alpha=0.3, zorder=1)

# 4. Axis Labels & Ticks
plt.ylabel("Ratio / Rate", fontsize=20, fontweight='bold')
plt.xlabel("", fontsize=1) # Minimal X-label to save vertical space
plt.xticks(rotation=45, ha='right', fontsize=18) 

# 5. Fixed Legend (Capturing colors correctly)
# We use ax.get_legend_handles_labels() to ensure colors match the bars
handles, labels = ax.get_legend_handles_labels()
ax.legend(
    handles=handles,
    labels=["Overlap Success Rate", "Overlap Latency Ratio"],
    loc='upper center',
    bbox_to_anchor=(0.5, 1.22), 
    ncol=2,
    fontsize=18,
    frameon=False,
    columnspacing=1.5
)

# 6. Final Polish
plt.grid(axis='y', linestyle=':', alpha=0.2, zorder=0)
ax.set_axisbelow(True)

print(df)
# Adjust layout to fit the legend at the top
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.show()
