import pandas as pd
import matplotlib.pyplot as plt
import io
import numpy as np
from scipy.stats import gmean

# --- 1. DATA PREPARATION ---
data = """No_of_cores victima potm vikram perfect_tlb
2-core 1.062943033 0.9123728499 1.483752165 1.915614564
4-core 0.8710040445 0.9222689898 1.152625141 1.429176712
8-core 0.7280235321 0.8950736006 1.167816872 1.541174844"""

df = pd.read_csv(io.StringIO(data), sep=r"\s+")
df.set_index("No_of_cores", inplace=True)

# Calculate Geometric Mean for all designs
df_gm = pd.DataFrame(gmean(df, axis=0).reshape(1, -1), 
                     columns=df.columns, index=["Geomean"])
df_final = pd.concat([df, df_gm])

# --- 2. PLOTTING ---
plt.rcParams.update({'font.size': 18, 'font.family': 'sans-serif'})
fig, ax = plt.subplots(figsize=(14, 6))

colors = ['#4C72B0', '#55A868', '#C44E52', '#8172B3']
hatches = ['', '//', '..', 'xx']

# Plotting with wider bars for clarity
df_final.plot(kind='bar', ax=ax, width=0.82, edgecolor='black', zorder=3, color=colors, legend=False)

# Apply Hatches and Labels
for i, container in enumerate(ax.containers):
    for patch in container:
        patch.set_hatch(hatches[i % len(hatches)])
    ax.bar_label(container, fmt='%.2f', padding=5, fontsize=13, fontweight='bold')

# Formatting
ax.set_ylabel("Speedup (Norm. to Baseline)", fontsize=22, fontweight='bold')
ax.set_xlabel("")
plt.xticks(rotation=0, fontsize=18, fontweight='bold')
plt.yticks(fontsize=18)
plt.ylim(0.5, 2.3) # Headroom for labels

# Visual Aids
plt.axhline(y=1.0, color='black', linestyle='-', linewidth=2, zorder=4) # Baseline ref
plt.axvline(x=len(df)-0.5, color='gray', linestyle='--', linewidth=2) # Geomean separator
plt.grid(axis='y', linestyle=':', alpha=0.6, zorder=0)

# Legend
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles=handles, labels=["VICTIMA", "POTM", "VIKRAM", "PERFECT TLB"],
          loc='lower center', bbox_to_anchor=(0.5, 1.05),
          ncol=4, fontsize=16, frameon=False)

plt.tight_layout()
plt.show()

# --- 3. COMPREHENSIVE TERMINAL STATS ---
print("\n" + "="*80)
print(f"{'CORE COUNT':<15} | {'VIKRAM vs POTM':<18} | {'VIKRAM vs VICTIMA':<18} | {'% OF PERFECT'}")
print("-" * 80)
for idx, row in df_final.iterrows():
    vs_potm = (row['vikram'] / row['potm'] - 1) * 100
    vs_victima = (row['vikram'] / row['victima'] - 1) * 100
    perfect_pct = (row['vikram'] / row['perfect_tlb']) * 100
    print(f"{idx:<15} | {vs_potm:>+16.1f}% | {vs_victima:>+16.1f}% | {perfect_pct:>11.1f}%")
print("="*80)
