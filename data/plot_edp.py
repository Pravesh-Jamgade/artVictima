import math
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# Tab-separated data (editable)
raw_table = """
athena	vb_l1	vb_l2	vb_l3	vb_l2l3	vb_l1l2l3	vikram_ptb
edp	0.7567	0.7337	0.7374	0.7372	0.7416	0.7413	1.3563
speedup	1.1944	1.2158	1.2131	1.2123	1.2090	1.2093	0.870
""".strip()


def parse_table(table_text: str):
    lines = [line.strip() for line in table_text.splitlines() if line.strip()]
    if len(lines) < 3:
        raise ValueError("Expected header, edp row, and speedup row")

    headers = lines[0].split("\t")
    edp_parts = lines[1].split("\t")
    speedup_parts = lines[2].split("\t")

    if edp_parts[0].lower() != "edp":
        raise ValueError("Second row must start with 'edp'")
    if speedup_parts[0].lower() != "speedup":
        raise ValueError("Third row must start with 'speedup'")

    edp_values = [float(x) for x in edp_parts[1:]]
    speedup_values = [float(x) for x in speedup_parts[1:]]

    if not (len(headers) == len(edp_values) == len(speedup_values)):
        raise ValueError("Header and data column counts do not match")

    return headers, edp_values, speedup_values


def percentile(sorted_vals, p):
    if not sorted_vals:
        raise ValueError("Cannot compute percentile of empty list")
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return d0 + d1


def robust_limits(values, pad_frac=0.08, min_pad=0.02):
    sorted_vals = sorted(values)
    if len(sorted_vals) < 4:
        vmin, vmax = min(sorted_vals), max(sorted_vals)
    else:
        q1 = percentile(sorted_vals, 25)
        q3 = percentile(sorted_vals, 75)
        iqr = q3 - q1
        if iqr == 0:
            inliers = sorted_vals
        else:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            inliers = [v for v in values if lower <= v <= upper]
            if not inliers:
                inliers = values
        vmin, vmax = min(inliers), max(inliers)

    pad = max((vmax - vmin) * pad_frac, min_pad)
    return vmin - pad, vmax + pad


labels, edp, speedup = parse_table(raw_table)

# Create Plot
plt.figure(figsize=(10, 6))
ax = plt.gca()

# Jitter and styling to separate overlapping points
jitter = 0.004
offset_pattern = [(-1, 1), (1, 1), (-1, -1), (1, -1), (0, 1.5), (0, -1.5), (1.5, 0), (-1.5, 0)]
markers = ['o', 's', '^', 'D', 'P', 'X', 'v', '*']
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']

# Axis limits based on robust (clustered) data
x_low, x_high = robust_limits(edp)
y_low, y_high = robust_limits(speedup)
ax.set_xlim(x_low, x_high)
ax.set_ylim(y_low, y_high)

plot_edp = []
plot_speedup = []
for i, (e, s) in enumerate(zip(edp, speedup)):
    dx, dy = offset_pattern[i % len(offset_pattern)]
    plot_edp.append(e + dx * jitter)
    plot_speedup.append(s + dy * jitter)

clipped_shown = False
for i, label in enumerate(labels):
    x_raw = plot_edp[i]
    y_raw = plot_speedup[i]
    x = min(max(x_raw, x_low), x_high)
    y = min(max(y_raw, y_low), y_high)
    clipped = (x != x_raw) or (y != y_raw)

    ax.scatter(
        x,
        y,
        color=colors[i % len(colors)],
        marker=markers[i % len(markers)],
        s=120,
        edgecolor='black',
        linewidths=0.6,
        label=label,
        zorder=3,
    )

    if clipped:
        if x_raw < x_low:
            ax.scatter(x_low, y, color='black', marker='<', s=90, zorder=4)
        elif x_raw > x_high:
            ax.scatter(x_high, y, color='black', marker='>', s=90, zorder=4)
        if y_raw < y_low:
            ax.scatter(x, y_low, color='black', marker='v', s=90, zorder=4)
        elif y_raw > y_high:
            ax.scatter(x, y_high, color='black', marker='^', s=90, zorder=4)

        if not clipped_shown:
            ax.scatter([], [], color='black', marker='>', s=90, label='clipped (out of range)')
            clipped_shown = True

# Formatting
plt.title('Performance vs. Energy Efficiency (EDP)')
plt.xlabel('EDP (Lower is Better)')
plt.ylabel('Speedup (Higher is Better)')
plt.grid(True, linestyle='--', alpha=0.6)

# Axis tick spacing
ax.xaxis.set_major_locator(MultipleLocator(0.2))
ax.yaxis.set_major_locator(MultipleLocator(0.2))

# Highlighting the baseline
plt.axvline(x=edp[0], color='red', linestyle=':', label=f'{labels[0]} baseline')
plt.legend(loc='best', fontsize=8, ncol=2)

plt.show()
