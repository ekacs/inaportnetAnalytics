#QUADRANT ANALYSIS

import numpy as np
import matplotlib.pyplot as plt

# calculate mean and median to consider the treshold
median_volume = Port_performance['volume'].median()
median_index = Port_performance['composite_index'].median()

# median threshold to classify quadrant
conditions = [
    (Port_performance['volume'] >= median_volume) &
    (Port_performance['composite_index'] >= median_index),

    (Port_performance['volume'] < median_volume) &
    (Port_performance['composite_index'] >= median_index),

    (Port_performance['volume'] < median_volume) &
    (Port_performance['composite_index'] < median_index),

    (Port_performance['volume'] >= median_volume) &
    (Port_performance['composite_index'] < median_index)
]

choices = [
    'Benchmark Port',
    'Efficient Port',
    'Developing Port',
    'Congested Port'
]

Port_performance['quadrant_analysis'] = np.select(
    conditions,
    choices,
    default='Unknown'
)

summary_port.head()
import numpy as np
import matplotlib.pyplot as plt

#=========================================================
# Transformasi logaritmic for visualisation
#=========================================================
Port_performance['volume_log'] = np.log10(Port_performance['volume'])

# line using median threshold
median_volume_log = np.log10(median_volume)

#=========================================================
# Warna tiap kuadran
#=========================================================
colors = {
    'Benchmark Port': 'green',
    'Efficient Port': 'blue',
    'Developing Port': 'orange',
    'Congested Port': 'red'
}

#=========================================================
# create Figure
#=========================================================
fig, ax = plt.subplots(figsize=(10,8))

#=========================================================
# Scatter plot based on quadrant analysis (Median)
#=========================================================
for quadrant, color in colors.items():

    subset = Port_performance[
        Port_performance['quadrant_analysis'] == quadrant
    ]

    ax.scatter(
        subset['volume_log'],
        subset['composite_index'],
        s=60,
        color=color,
        alpha=0.8,
        edgecolor='black',
        linewidth=0.4,
        label=quadrant
    )

#=========================================================
# Median line (threshold)
#=========================================================
ax.axvline(
    median_volume_log,
    color='black',
    linestyle='--',
    linewidth=1.5
)

ax.axhline(
    median_index,
    color='black',
    linestyle='--',
    linewidth=1.5
)

#=========================================================
# add quadrant name
#=========================================================
xmin, xmax = ax.get_xlim()
ymin, ymax = ax.get_ylim()

ax.text(
    (median_volume_log + xmax)/2,
    (median_index + ymax)/2,
    'Benchmark Port',
    fontsize=12,
    fontweight='bold',
    ha='center'
)

ax.text(
    (xmin + median_volume_log)/2,
    (median_index + ymax)/2,
    'Efficient Port',
    fontsize=12,
    fontweight='bold',
    ha='center'
)

ax.text(
    (xmin + median_volume_log)/2,
    (ymin + median_index)/2,
    'Developing Port',
    fontsize=12,
    fontweight='bold',
    ha='center'
)

ax.text(
    (median_volume_log + xmax)/2,
    (ymin + median_index)/2,
    'Congested Port',
    fontsize=12,
    fontweight='bold',
    ha='center'
)

#=========================================================
# set x label 
#=========================================================
ticks = [0, 10, 100, 1000, 10000, 100000]
tick_pos = np.log10(np.array(ticks) + 1)

ax.set_xticks(tick_pos)
ax.set_xticklabels([f'{t:,}' for t in ticks])

#=========================================================
# title and label
#=========================================================
ax.set_title(
    'Quadrant Analysis of Port Performance (Median Threshold)',
    fontsize=14,
    fontweight='bold'
)

ax.set_xlabel('Volume (log scale)')
ax.set_ylabel('Composite Index')

ax.grid(alpha=0.3)

plt.tight_layout()
plt.show()
