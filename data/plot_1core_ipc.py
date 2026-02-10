import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np

# 1. Load the data
data = """
benchmark	perfect_tlb	perfect_pwc	potm	victima	vikram
dlrm	1.167017315	1.111800433	1.017728558	1.057522898	1.07237792
pr	1.124136002	1.077532627	0.9976969043	1.045427312	1.049473725
cc	1.169779091	1.122292927	1.017559082	1.050971225	1.084268035
sssp	1.321294532	1.244668375	1.049826172	1.050680833	1.031906573
gc	1.302216932	1.231267136	1.025889463	1.022860936	1.062706023
tc	1.160597247	1.114904137	1.028518998	1.028093003	1.092437692
xs	1.478584632	1.326369905	1.093560948	1.202239145	1.100432974
rnd	3.103851983	2.79827287	1.68509517	2.015975511	2.365210009
bfs	1.16211121	1.107130325	1.013761677	1.054309327	1.068040926
bc	1.642651302	1.505199614	1.047111621	1.037204327	1.086173231
gen	1.301495441	1.230586681	1.02524408	1.022259166	1.062995871
geomean	1.381351846	1.297088783	1.078459908	1.119991912	1.150886669
"""


df = pd.read_csv(io.StringIO(data), sep=r"\s+")
df.set_index("benchmark", inplace=True)

# 2. Compact ISCA/MICRO Style Plotting
fig, ax = plt.subplots(figsize=(16, 5))

# Professional Palette and Hatches
colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B3', '#DD8452']
hatches = ['', '//', '..', 'xx', '\\\\', '--']

df.plot(kind='bar', ax=ax, width=0.8,  edgecolor='black', color=colors, zorder=3)

# Apply patterns to bars
for i, container in enumerate(ax.containers):
    for patch in container:
        patch.set_hatch(hatches[i])

# 3. Text & Label Customization
plt.ylabel("Speedup (Norm. IPC)", fontsize=20, fontweight='bold')
plt.xlabel("") 
plt.xticks(rotation=45, fontsize=18, ha='right') 
plt.yticks(fontsize=18)
plt.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
ax.set_axisbelow(True)

# 4. Legend Configuration
handles, labels = ax.get_legend_handles_labels()
ax.legend(
    handles=handles,
    labels=[l.replace('_', ' ').upper() for l in labels],
    loc='lower center', bbox_to_anchor=(0.5, 1.05), 
    ncol=len(df.columns), fontsize=16, frameon=False,
    columnspacing=1.0, handletextpad=0.3
)

plt.axhline(y=1.0, color='black', linestyle='-', linewidth=2.0, zorder=4)
plt.tight_layout(rect=[0, 0, 1, 0.98])

# 5. TERMINAL COMPARATIVE ANALYSIS
print("\n" + "="*95)
print(f"{'BENCHMARK':<12} | {'VIKRAM':>8} | {'vs BASE':>10} | {'vs POTM':>10} | {'vs VICTIMA':>10} | {'vs P.PWC':>10}")
print("-" * 95)

for bench in df.index:
    v = df.loc[bench, 'vikram']
    # Gain vs Baseline (1.0)
    g_base = (v - 1.0) * 100
    # Gain vs POTM
    g_potm = (v / df.loc[bench, 'potm'] - 1) * 100
    # Gain vs Victima
    g_vict = (v / df.loc[bench, 'victima'] - 1) * 100
    # Gain vs Perfect PWC
    g_ppwc = (v / df.loc[bench, 'perfect_pwc'] - 1) * 100

    # g_tempo = (v / df.loc[bench, 'tempo'] - 1) * 100
    
    print(f"{bench:<12} | {v:>8.3f} | {g_base:>+9.1f}% | {g_potm:>+9.1f}% | {g_vict:>+9.1f}% | ")

print("-" * 95)
# Summary for Geomean
geo_v = df.loc['geomean', 'vikram']
geo_vict = (geo_v / df.loc['geomean', 'victima'] - 1) * 100
print(f"SUMMARY: Vikram improves upon Victima by {geo_vict:.2f}% on average (Geomean).")
print("="*95)

plt.show()
