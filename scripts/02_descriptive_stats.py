#descriptive statistics
import pandas as pd

#descriptive statistics - approval
approval_stats = pd.DataFrame({
    'NumberOfData': [df_join['approval_minutes'].count()],
    'Minimum': [df_join['approval_minutes'].min()],
    'Q1': [df_join['approval_minutes'].quantile(0.25)],
    'Median': [df_join['approval_minutes'].median()],
    'Mean': [df_join['approval_minutes'].mean()],
    'Q3': [df_join['approval_minutes'].quantile(0.75)],
    'P95' : [df_join['approval_minutes'].quantile(0.95)],
    'Maximum': [df_join['approval_minutes'].max()],
    'StdDev': [df_join['approval_minutes'].std()]
})
approval_stats = approval_stats.round(3)

#print(approval_stats)

approval_0 = df_join[df_join['approval_minutes'] == 0]

import matplotlib.pyplot as plt
from scipy.stats import skew
import numpy as np

P95 = df_join['approval_minutes'].quantile(0.95)
# Data volume
data_approval = df_join['approval_minutes']
data_approvalP95 = df_join[df_join['approval_minutes']<P95]
data_approvalP95 = data_approvalP95['approval_minutes']

meanP95 = data_approvalP95.mean()
medianP95 = data_approvalP95.median()
skewnessP95 = skew(data_approvalP95)

# create figure
fig, axes = plt.subplots(1, 2, figsize=(14,5))

# =====================================================
# Plot 1 : Histogram
# =====================================================
ax = axes[0]

ax.hist(
    data_approvalP95,
    bins=100,
    edgecolor='black'
)

# Mean
ax.axvline(
    meanP95,
    color='red',
    linestyle='--',
    linewidth=2,
    label=f'Mean = {meanP95:.1f}'
)

# Median
ax.axvline(
    medianP95,
    color='blue',
    linestyle='-',
    linewidth=2,
    label=f'Median = {medianP95:.1f}'
)

# Nilai skewness
ax.text(
    0.98,
    0.95,
    f'Skewness = {skewnessP95:.2f}\n'
    f'Percentile-95 = {P95:.2f}',
    transform=ax.transAxes,
    ha='right',
    va='top',
    bbox=dict(facecolor='white', edgecolor='black')
)

ax.set_title('Histogram of approval (<Percentile95)')
ax.set_xlabel('approval (minutes)')
ax.set_ylabel('Frequency')
ax.legend()
ax.grid(alpha=0.3)

# =====================================================
# Plot 2 : Boxplot
# =====================================================
from matplotlib.lines import Line2D

ax = axes[1]

ax.boxplot(
    data_approval,
    vert=True,
    patch_artist=True,
    showmeans=True,
    meanline=True,
    widths=0.4,
    boxprops=dict(facecolor='skyblue', edgecolor='black'),
    whiskerprops=dict(color='black'),
    capprops=dict(color='black'),
    medianprops=dict(color='red', linewidth=2),
    meanprops=dict(color='blue', linewidth=2),
    flierprops=dict(marker='o',
                    markersize=4,
                    markerfacecolor='gray',
                    markeredgecolor='black',
                    alpha=0.6)
)

legend_elements = [
    Line2D([0], [0], color='red', lw=2, label='Mean'),
    Line2D([0], [0], color='blue', lw=2, label='Median')
]

ax.legend(handles=legend_elements, loc='upper right')
ax.set_title('Boxplot of approval (minutes)')
ax.set_xlabel('approval')
ax.set_ylabel('minutes')

plt.tight_layout()
plt.show()

#statistic descriptive - volume

volume_port = (
    df_join
    .groupby(['port_code', 'port'])
    .agg(
        volume=('approval_minutes', 'count')
    )
    .reset_index()
)

volume_stats = pd.DataFrame({
    'NumberOfData': [volume_port['volume'].count()],
    'Minimum': [volume_port['volume'].min()],
    'Q1': [volume_port['volume'].quantile(0.25)],
    'Median': [volume_port['volume'].median()],
    'Q3': [volume_port['volume'].quantile(0.75)],
    'Maximum': [volume_port['volume'].max()],
    'Mean': [volume_port['volume'].mean()],
    'Std Dev': [volume_port['volume'].std()]
})
volume_stats = volume_stats.round(2)

#print(volume_stats)

import matplotlib.pyplot as plt
from scipy.stats import skew
import numpy as np

# Data volume

data = volume_port['volume']
Per95_volume = volume_port['volume'].quantile(0.95)
data95 = volume_port[volume_port['volume']<Per95_volume]
data95 = data95['volume']

print(Per95_volume)

# Statistics
mean95 = data95.mean()
median95 = data95.median()
skewness95 = skew(data95)

# create figure
fig, axes = plt.subplots(1, 2, figsize=(14,5))

# =====================================================
# Plot 1 : Histogram
# =====================================================
ax = axes[0]

ax.hist(
    data95,
    bins=160,
    edgecolor='black'
)

# Mean
ax.axvline(
    mean95,
    color='red',
    linestyle='--',
    linewidth=2,
    label=f'Mean = {mean95:.1f}'
)

# Median
ax.axvline(
    median95,
    color='blue',
    linestyle='-',
    linewidth=2,
    label=f'Median = {median95:.1f}'
)

# skewness
ax.text(
    0.98,
    0.95,
    f'Skewness = {skewness95:.2f}\n'
    f'Percentile-95 = {Per95_volume:.2f}',
    transform=ax.transAxes,
    ha='right',
    va='top',
    bbox=dict(facecolor='white', edgecolor='black')
)

ax.set_title('Histogram of Port Volume (Percentile 95)')
ax.set_xlabel('Volume')
ax.set_ylabel('Frequency')
ax.legend()
ax.grid(alpha=0.3)

# =====================================================
# Plot 2 : Boxplot
# =====================================================
from matplotlib.lines import Line2D

ax = axes[1]

ax.boxplot(
    data,
    vert=True,
    patch_artist=True,
    showmeans=True,
    meanline=True,
    widths=0.4,
    boxprops=dict(facecolor='skyblue', edgecolor='black'),
    whiskerprops=dict(color='black'),
    capprops=dict(color='black'),
    medianprops=dict(color='red', linewidth=2),
    meanprops=dict(color='blue', linewidth=2),
    flierprops=dict(marker='o',
                    markersize=4,
                    markerfacecolor='gray',
                    markeredgecolor='black',
                    alpha=0.6)
)

legend_elements = [
    Line2D([0], [0], color='blue', lw=2, label='Median'),
    Line2D([0], [0], color='red', lw=2, label='Mean')
]

ax.legend(handles=legend_elements, loc='upper right')

plt.tight_layout()
plt.show()

#descriptive statistics of port performance index
import pandas as pd
import numpy as np

# port performance summary
summary_port = (
    df_join
    .groupby(['port_code', 'port'])
    .agg(
        volume=('approval_minutes', 'count'),
        sla_compliant=('approval_minutes', lambda x: (x < 31).sum()),
        mean_response_time=('approval_minutes', 'mean'),
        std_response_time=('approval_minutes', 'std'),
        extreme_delay=('approval_minutes', lambda x: (x > 102).sum())
    )
    .reset_index()
)

# calculte derived variables
summary_port['sla_compliance'] = (
    summary_port['sla_compliant'] /
    summary_port['volume']
)

summary_port['coefficient_of_variation'] = (
    summary_port['std_response_time'] /
    summary_port['mean_response_time']
)

summary_port['extreme_delay_index'] = (
    summary_port['extreme_delay'] /
    summary_port['volume']
)

import matplotlib.pyplot as plt
from scipy.stats import skew

# indicator list
index_cols = [
    'sla_compliance',
    'mean_response_time',
    'coefficient_of_variation',
    'extreme_delay_index'
]

# canvas 4 rows x 2 column
fig, axes = plt.subplots(
    nrows=4,
    ncols=2,
    figsize=(14,16)
)

for i, col in enumerate(index_cols):

    data = summary_port[col].dropna()

    # Statistik
    mean = data.mean()
    median = data.median()
    skewness = skew(data)

    # ==================================================
    # Histogram
    # ==================================================
    ax = axes[i,0]

    ax.hist(
        data,
        bins=20,
        edgecolor='black'
    )

    ax.axvline(
        mean,
        linestyle='--',
        linewidth=2,
        color='red',
        label=f'Mean = {mean:.2f}'
    )

    ax.axvline(
        median,
        linestyle='-',
        linewidth=2,
        color='blue',
        label=f'Median = {median:.2f}'
    )

    ax.set_title(f'{col.replace("_"," ").title()} - Histogram')
    ax.set_xlabel(col)
    ax.set_ylabel('Frequency')

    ax.text(
        0.98,
        0.95,
        f'Skewness = {skewness:.3f}',
        transform=ax.transAxes,
        ha='right',
        va='top',
        bbox=dict(facecolor='white', alpha=0.8)
    )

    ax.legend(fontsize=8)

    # ==================================================
    # Boxplot (kolom kanan)
    # ==================================================
    ax = axes[i,1]

    bp = ax.boxplot(
        data,
        vert=True,
        showmeans=True,
        meanline=True,
        patch_artist=True
    )

    ax.set_title(f'{col.replace("_"," ").title()} - Boxplot')
    ax.set_xlabel(col)

    # Membuat legend mean dan median
    from matplotlib.lines import Line2D

    legend_elements = [
        Line2D([0],[0],
               color='orange',
               linewidth=2,
               label='Median'),

        Line2D([0],[0],
               color='green',
               linewidth=2,
               linestyle='--',
               label='Mean')
    ]

    ax.legend(
        handles=legend_elements,
        fontsize=8,
        loc='upper right'
    )

plt.tight_layout()
plt.show()

# descriptive statistics = indicator
from scipy.stats import skew
descriptive_stats = pd.DataFrame({
    'Mean': summary_port[index_cols].mean(),
    'Median': summary_port[index_cols].median(),
    'SD': summary_port[index_cols].std(),
    'Min': summary_port[index_cols].min(),
    'P5': summary_port[index_cols].quantile(0.05),
    'P95': summary_port[index_cols].quantile(0.95),
    'Max': summary_port[index_cols].max(),
    'Skew' : summary_port[index_cols].skew()
})

# Coefficient of Variation (CV = SD / Mean)
descriptive_stats['CV'] = (
    descriptive_stats['SD'] /
    descriptive_stats['Mean']
)

descriptive_stats = descriptive_stats.round(4)
print(descriptive_stats)
