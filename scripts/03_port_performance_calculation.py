#port perfromance calculation

#winsorized normalization
import numpy as np

def winsorized_minmax(series, higher_is_better=True):
    """
    Winsorized Min-Max Normalization menggunakan P5 dan P95.

    Parameters
    ----------
    series : pandas.Series
    higher_is_better : bool
        True  -> nilai besar semakin baik
        False -> nilai kecil semakin baik

    Returns
    -------
    pandas.Series
    """

    p5 = series.quantile(0.05)
    p95 = series.quantile(0.95)

    if higher_is_better:
        index = (series - p5) / (p95 - p5)
    else:
        index = (p95 - series) / (p95 - p5)

    # Winsorization
    index = index.clip(lower=0, upper=1)

    return index

#sla compliance index
summary_port['compliance_index'] = winsorized_minmax(
    summary_port['sla_compliance'],
    higher_is_better=True
)

#mean_response_time
summary_port['efficiency_index'] = winsorized_minmax(
    summary_port['mean_response_time'],
    higher_is_better=False
)

#coefficient of variation
summary_port['consistency_index'] = winsorized_minmax(
    summary_port['coefficient_of_variation'],
    higher_is_better=False
)

#extreme delay
summary_port['robustness_index'] = winsorized_minmax(
    summary_port['extreme_delay'],
    higher_is_better=False
)

summary_port['composite_index'] = 0.25 * (
    summary_port['compliance_index']
    + summary_port['efficiency_index']
    + summary_port['consistency_index']
    + summary_port['robustness_index']
)

Port_performance = summary_port[[
    'port_code', 
    'port', 
    'volume', 
    'compliance_index',
    'efficiency_index',
    'consistency_index',
    'robustness_index',
    'composite_index'
]].sort_values(by='composite_index', ascending=False).reset_index(drop=True)

import matplotlib.pyplot as plt
from scipy.stats import skew

# Data
data = Port_performance['composite_index'].dropna()

# Statistics
mean = data.mean()
median = data.median()
std = data.std()
P95 = data.quantile(0.95)

# Skewness
skewness = skew(data)

# =====================================================
# Histogram Composite Index
# =====================================================
plt.figure(figsize=(8,5))

plt.hist(
    data,
    bins=20,
    edgecolor='black'
)

# Mean
plt.axvline(
    mean,
    color='red',
    linestyle='--',
    linewidth=2,
    label=f'Mean = {mean:.3f}'
)

# Median
plt.axvline(
    median,
    color='blue',
    linestyle='-',
    linewidth=2,
    label=f'Median = {median:.3f}'
)

# Statistics in textbox
info = (
    f"Skewness = {skewness:.3f}"
)

plt.text(
    0.98,
    0.95,
    info,
    transform=plt.gca().transAxes,
    ha='right',
    va='top',
    bbox=dict(facecolor='white', edgecolor='black', alpha=0.8)
)

plt.title('Distribution of Composite Index')
plt.xlabel('Composite Index')
plt.ylabel('Frequency')
plt.xlim(0, 1)

plt.legend()
plt.grid(alpha=0.3)

plt.tight_layout()
plt.show()

#statistics descriptive
performanceIndex_stats = pd.DataFrame({
    'Number of Data': [Port_performance['composite_index'].count()],
    'Minimum': [Port_performance['composite_index'].min()],
    'Q1': [Port_performance['composite_index'].quantile(0.25)],
    'Median': [Port_performance['composite_index'].median()],
    'Mean': [Port_performance['composite_index'].mean()],
    'Q3': [Port_performance['composite_index'].quantile(0.75)],
    'P95' : [Port_performance['composite_index'].quantile(0.95)],
    'Maximum': [Port_performance['composite_index'].max()],
    'Std Dev': [Port_performance['composite_index'].std()]
})
performanceIndex_stats = performanceIndex_stats.round(3)
performanceIndex_stats
