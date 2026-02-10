import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io

# --- 1. DATA PREPARATION ---
# Use standard range notation for bins
csv_data = """folder_tag,level,4–7,8–15,16–31,32–63,64–127,128–255,256–511,512–1023
dlrm,L2,1104683,1,665384,39349,34091,46475,1324,7
pr,L2,398959,0,144299,573,2052,1885,440,631
cc,L2,1464738,5,692501,56981,60408,83892,3724,14
sssp,L2,505448,0,298045,30553,36326,99437,6739,30
gc,L2,6852870,1,2300974,180432,112839,188671,2668,1
tc,L2,3,0,0,0,1,3,2,0
xs,L2,1350,0,19994,186,1224,537,10,0
rnd,L2,0,0,0,0,0,0,2,0
bfs,L2,2013807,3,791128,45277,42255,57992,1750,3
bc,L2,70515,0,47775,3607,1020,14331,183,0
gen,L2,6841524,1,2310579,179480,113387,191158,2651,0"""

df = pd.read_csv(io.StringIO(csv_data)).set_index('folder_tag')
bins = ["4–7", "8–15", "16–31", "32–63", "64–127", "128–255", "256–511", "512–1023"]

# Normalize: Rows sum to 100%
df_norm = df[bins].div(df[bins].sum(axis=1), axis=0) * 100
df_norm = df_norm.fillna(0)

# --- 2. PLOTTING ---
plt.rcParams.update({'font.size': 18, 'font.family': 'sans-serif'})
fig, ax = plt.subplots(figsize=(12, 6))

# Use "Blues" or "YlGnBu" for professional look. 
# mask=df_norm.T == 0 hides 0 values if you want them empty
sns.heatmap(df_norm.T, annot=True, fmt=".1f", cmap="Blues", 
            cbar_kws={'label': 'Miss Distribution (%)'}, 
            linewidths=1, linecolor='whitesmoke', ax=ax, 
            annot_kws={"size": 12, "weight": "bold"})

# Formatting for ISCA
ax.set_ylabel('Latency (Cycles)', fontweight='bold', fontsize=20)
ax.set_xlabel('Workload', fontweight='bold', fontsize=20)

# Professional Ticks
plt.xticks(rotation=45, ha='right', fontsize=16)
plt.yticks(rotation=0, fontsize=16)

plt.tight_layout()
# plt.savefig("latency_heatmap.pdf", format="pdf", bbox_inches="tight") # For paper
plt.show()
