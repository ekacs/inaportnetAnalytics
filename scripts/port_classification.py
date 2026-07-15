#PORT CLASSIFICATION
port_metrics = df_join.groupby('PELABUHAN').agg(
    total_request=('nomor_pkk','count'),
    avg_processing_time=('processing_time_minutes','mean')
).reset_index()

port_metrics

workload_threshold = port_metrics['total_request'].median()
capacity_threshold = port_metrics['avg_processing_time'].median()

def classify_port(row):
    if row['total_request'] >= workload_threshold and row['avg_processing_time'] <= capacity_threshold:
        return "High Demand - Efficient"
    
    elif row['total_request'] >= workload_threshold and row['avg_processing_time'] > capacity_threshold:
        return "High Demand - Bottleneck"
    
    elif row['total_request'] < workload_threshold and row['avg_processing_time'] <= capacity_threshold:
        return "Underutilized"
    
    else:
        return "Low Performance"

port_metrics['port_classification'] = port_metrics.apply(classify_port, axis=1)

import matplotlib.pyplot as plt

# define color map
color_map = {
    "Underutilized": "yellow",
    "High Demand - Efficient": "green",
    "High Demand - Bottleneck": "orange",
    "Low Performance": "red"
}

port_metrics['color'] = port_metrics['port_classification'].map(color_map)

plt.figure(figsize=(8,6))

for category, color in color_map.items():
    subset = port_metrics[port_metrics['port_classification'] == category]
    plt.scatter(
        subset['total_request'], 
        subset['avg_processing_time'], 
        c=color, 
        label=category, 
        s=40, #size of point
        edgecolors='black',
        alpha=0.7
    )

#line of threshold
plt.axvline(workload_threshold, color='blue', linestyle='--', alpha=0.5)
plt.axhline(capacity_threshold, color='blue', linestyle='--', alpha=0.5)

low_perf_top3 = (
    port_metrics[port_metrics['port_classification'] == "Low Performance"]
    .nlargest(3, 'avg_processing_time')
)

for i, row in low_perf_top3.iterrows():
    plt.text(
        row['total_request'] + 500,
        row['avg_processing_time'], 
        row['PELABUHAN'],
        fontsize=10,
        fontweight='bold'
    )

# graph attribute
plt.xlabel("Total Request (Workload)", fontsize=12)
plt.ylabel("Average Processing Time (Minutes)", fontsize=12)
plt.title("Port Classification Matrix", fontsize=15, fontweight='bold', pad=20)
plt.legend(title="Port Status", loc='upper right')
plt.grid(True, linestyle=':', alpha=0.6)

# Margin management
plt.xlim(-2000, port_metrics['total_request'].max() * 1.05)
plt.ylim(-10, port_metrics['avg_processing_time'].max() * 1.1)

plt.tight_layout()
plt.show()
