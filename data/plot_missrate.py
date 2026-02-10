import matplotlib.pyplot as plt
import pandas as pd
import io
import numpy as np
from scipy.stats import gmean

# --- 1. DATA ---
data = """workload,level,hits,misses,total_accesses,hit_rate_pct
dlrm,L2,33898300,1891314,35789614,94.72
pr,L2,18747686,548869,19296555,97.16
cc,L2,40644674,2362263,43006937,94.51
sssp,L2,32020004,976578,32996582,97.04
gc,L2,21976818,9638456,31615274,69.51
tc,L2,3391965,9,3391974,100.0
xs,L2,7353156,23301,7376457,99.68
rnd,L2,35550973,2,35550975,100.0
bfs,L2,32987705,2952215,35939920,91.79
bc,L2,5465161,137431,5602592,97.55
gen,L2,21984789,9638780,31623569,69.52"""

df = pd.read_csv(io.StringIO(data))
df['miss_rate'] = (df['misses'] / df['total_accesses']) * 100

# Calculate Geomean (using epsilon for stability)
gm_val = gmean(df['miss_rate'].replace(0, 1e-6))
df_geo = pd.DataFrame({'workload': ['Geomean'], 'miss_rate': [gm_val]})
df_final = pd.concat([df, df_geo], ignore_index=True)

# --- 2. PLOTTING ---
plt.rcParams.update({'font.size': 16, 'font.family': 'sans-serif'})
fig, ax = plt.subplots(figsize=(9, 4)) # Compact single-column width

# Style settings
colors = ['#4C72B0'] * len(df) + ['#55A868'] # Blue for workloads, Green for Geomean
hatches = ['//'] * len(df) + ['xx']

bars = ax.bar(df_final['workload'], df_final['miss_rate'], 
              color=colors, edgecolor='black', linewidth=1)

for i, bar in enumerate(bars):
    bar.set_hatch(hatches[i])

# Vertical line to separate Geomean
ax.axvline(x=len(df)-0.5, color='black', linestyle='--', linewidth=1)

# Formatting
ax.set_ylabel('L2 Miss Rate (%)', fontsize=18, fontweight='bold')
ax.set_xticklabels(df_final['workload'], rotation=45, ha='right')
ax.set_ylim(0, 40) # Set to 40 to give "gc" and "gen" room
ax.set_axisbelow(True)
ax.grid(axis='y', linestyle=':', alpha=0.6)

# Labels - only for values > 0.1% to avoid clutter
for bar in bars:
    height = bar.get_height()
    if height > 0.1:
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.show()
