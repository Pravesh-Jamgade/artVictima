import pandas as pd
import matplotlib.pyplot as plt
import io

# Load the data

df = pd.read_csv('input.csv', sep=r'\s+', engine='python')

# Pivot the data so we have separate dataframes for each Level
levels = df['level'].unique()

# Create subplots for each cache level
fig, axes = plt.subplots(nrows=len(levels), ncols=1, figsize=(10, 16), sharex=True)

for i, lvl in enumerate(levels):
    subset = df[df['level'] == lvl]
    subset.set_index('workload')[['hits', 'misses']].plot(
        kind='bar', 
        stacked=True, 
        ax=axes[i], 
        color=['#4CAF50', '#F44336'] # Green for Hits, Red for Misses
    )
    axes[i].set_title(f'Cache Statistics: {lvl}', fontsize=14)
    axes[i].set_ylabel('Total Accesses')
    axes[i].grid(axis='y', linestyle='--', alpha=0.7)
    axes[i].legend(["Hits", "Misses"])

plt.xlabel('Workload', fontsize=12)
plt.tight_layout()
plt.show()
