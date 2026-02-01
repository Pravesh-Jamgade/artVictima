import pandas as pd
import matplotlib.pyplot as plt
import io

# Data setup
data = """cores	PTB-MISS_PDPT-MISS	PTB-MISS_PDPT-HIT	PTB-HIT_PDPT-MISS	PTB-HIT_PDPT-HIT
1-core	1.049623211	0.0003557705596	39.11014668	59.83987434
2-core	3.443562493	0.007821593474	87.77891779	8.769698125
4-core	3.301256185	0.007461087158	55.29180879	41.39947394
8-core	3.0020832	0.006290585172	50.96830518	46.02332103"""

df = pd.read_csv(io.StringIO(data), sep=r'\s+')

# 1. Map column names
level_map = {
    'cores': 'Number of cores',
    'PTB-MISS_PDPT-MISS': 'PTB miss PDPT miss', 
    'PTB-MISS_PDPT-HIT': 'PTB miss PDPT hit', 
    'PTB-HIT_PDPT-MISS': 'PTB hit PDPT miss', 
    'PTB-HIT_PDPT-HIT': 'PTB hit PDPT hit'
}
df = df.rename(columns=level_map)
df.set_index('Number of cores', inplace=True)

# 2. Plotting
ax = df.plot(kind='bar', stacked=True, figsize=(12, 8), width=0.7)

# 3. Position Legend ABOVE the chart
# loc='lower center' combined with bbox_to_anchor=(0.5, 1.02) centers it top-middle
ax.legend(
    loc='lower center', 
    bbox_to_anchor=(0.5, 1.02), 
    ncol=2,             # Splits legend into 2 columns for better horizontal fit
    fontsize=10, 
    frameon=False       # Optional: removes border for a cleaner look
)

# 4. Customization
plt.ylabel('Fraction of PDPT PSC Misses Resolved by PTB (%)', fontsize=12)
plt.xlabel('Number of cores', fontsize=12)
plt.xticks(rotation=0)

# 5. Add numbers inside the bars
for c in ax.containers:
    labels = [f'{v.get_height():.1f}%' if v.get_height() > 3 else '' for v in c]
    ax.bar_label(c, labels=labels, label_type='center', fontsize=9, fontweight='bold')

# Increase top margin to make room for the legend
plt.tight_layout(rect=[0, 0, 1, 0.95]) 
plt.show()
