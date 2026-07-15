#TRAFFFIC ANALYSIS
#total number of PKK service
total_pkk = df_join.shape[0]
print("Total PKK service on national:", total_pkk)

#average traffic per months
traffic_port = (
    df_join.groupby(['KODE','PELABUHAN'])
    .size()
    .reset_index(name='total_pkk')
    .sort_values('total_pkk', ascending=False)
)
traffic_port.head(10)

#national traffic share on each port
traffic_port['share_%'] = (
    traffic_port['total_pkk'] /
    traffic_port['total_pkk'].sum() * 100
)
traffic_port.head(10)

#top 10 port based on traffic volume
traffic_port = traffic_port.sort_values(by='total_pkk', ascending=False)
top10 = traffic_port.head(10).copy()
others = traffic_port.iloc[10:]
others_sum = others['total_pkk'].sum()
other_row = pd.DataFrame({
    'PELABUHAN': ['Other'],
    'total_pkk': [others_sum]
    })

pie_df = pd.concat([top10[['PELABUHAN','total_pkk']], other_row], ignore_index=True)

#plot top 10 busiest port
import matplotlib.pyplot as plt

colors = plt.cm.Paired(range(len(pie_df)))

fig, ax = plt.subplots(figsize=(8,8))

wedges, texts, autotexts = ax.pie(
    pie_df['total_pkk'],
    labels=pie_df['PELABUHAN'],
    autopct='%1.1f%%',
    startangle=140,
    colors=colors,
    pctdistance=0.85,
    explode=[0.05 if i == 0 else 0 for i in range(len(pie_df))] # Memberi sedikit celah pada slice terbesar
)

centre_circle = plt.Circle((0,0),0.70,fc='white', linewidth=1.25)
fig.gca().add_artist(centre_circle)
plt.setp(autotexts, size=10, weight="bold", color="black")
ax.set_title("Top 10 - Port to port Traffic Distribution")
plt.tight_layout()
plt.show()

traffic_port.head(10)

#Quartal trend
trend_qtr = df_join.groupby('quarter').size().reset_index(name='total_service')

# Plot
plt.style.use('seaborn-v0_8-muted')
fig, ax = plt.subplots(figsize=(10, 6))

x_data = trend_qtr['quarter'].astype(str) 
y_data = trend_qtr['total_service']

colors = ['#296B05', '#B59E10', '#96270F', '#EB661A']

bars = ax.bar(
    x_data,
    y_data,
    color=colors,
    edgecolor=None,
    width=0.6
)
for bar in bars:
    yval = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width()/2, 
        yval + (yval * 0.01),
        f'{int(yval):,}', 
        ha='center', 
        va='bottom', 
        fontsize=11, 
        fontweight='bold',
        color='#2d3748'
    )

ax.set_title('Quarterly Submission Trend: PKK Service Volume', pad=25, fontsize=16, fontweight='bold', loc='left')
ax.set_xlabel('Quarter', fontsize=12, labelpad=10)
ax.set_ylabel('Total Service', fontsize=12, labelpad=10)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#cbd5e0')
ax.spines['bottom'].set_color('#cbd5e0')

ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=0.2)

plt.tight_layout()
plt.show()

#traffic monthly
traffic_monthly = (
    df_join.groupby(['year','month'])
    .size()
    .reset_index(name='total_service')
    .sort_values(['year','month'])
)
month_names = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'December'
}

traffic_monthly['month'] = traffic_monthly['month'].map(month_names)
# Plot
import matplotlib.pyplot as plt

# Threshold for the largest 3
top_3_threshold = traffic_monthly['total_service'].nlargest(3).min()

ax = traffic_monthly.plot(
    x='month',
    y='total_service',
    kind='bar',
    color='skyblue',
    edgecolor='black',
    figsize=(10, 6),
    legend=False
)
for p in ax.patches:
    height = p.get_height()
    text_color = 'red' if height >= top_3_threshold else 'black'
    ax.annotate(f'{int(p.get_height())}', 
                (p.get_x() + p.get_width() / 2., p.get_height()), 
                ha='center', va='center', 
                xytext=(0, 9), 
                textcoords='offset points',
                fontsize=10,
                fontweight='bold',
                color=text_color)
plt.title('Submission trend per Months 2025')
plt.xlabel('Month')
plt.ylabel('Total Service')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()

#traffic per day
traffic_day = (
    df_join.groupby('day')
    .size()
    .reset_index(name='total_service')
)

order_day = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

traffic_day['day'] = pd.Categorical(
    traffic_day['day'],
    categories=order_day,
    ordered=True
)

traffic_day = traffic_day.sort_values('day')
traffic_day.head(10)

import matplotlib.pyplot as plt
#the highest service by day
top_1_threshold = traffic_day['total_service'].nlargest(1).min()

# Create Plot
ax = traffic_day.plot(
    x='day', 
    y='total_service', 
    kind='bar', 
    color='skyblue', 
    edgecolor='black', 
    figsize=(10, 6),
    legend=False  # remove legend
)

# Adding label above the graph
for p in ax.patches:
    height = p.get_height()
    text_color = 'red' if height >= top_1_threshold else 'black'
    ax.annotate(f'{int(p.get_height())}', 
                (p.get_x() + p.get_width() / 2., p.get_height()), 
                ha='center', va='center', 
                xytext=(0, 9), 
                textcoords='offset points',
                fontsize=10,
                fontweight='bold',
                color=text_color)

# Complementing the graph attribute
plt.title('Submission trend by Day 2025', fontsize=14, fontweight='bold')
plt.xlabel('Day', fontsize=12)
plt.ylabel('Total Service', fontsize=12)
plt.xticks(rotation=0) # Hari biasanya cukup pendek, jadi rotasi 0 saja agar tegak
plt.grid(axis='y', linestyle='--', alpha=0.5)

# adding height of graph to give more spaces
plt.ylim(0, traffic_day['total_service'].max() * 1.1)

plt.tight_layout()
plt.show()

#traffic by hour
traffic_hour = (
    df_join.groupby('hour')
    .size()
    .reset_index(name='total_service')
    .sort_values('hour')
)

# Creating Plot
ax = traffic_hour.plot(
    x='hour', 
    y='total_service', 
    kind='bar', 
    color='skyblue', 
    edgecolor='black', 
    figsize=(10, 6),
    legend=False  # Menghilangkan legend
)

for i, p in enumerate(ax.patches):
    current_hour = traffic_hour.iloc[i]['hour']
    height = p.get_height()
    
    text_color = 'red' if 8 <= current_hour <= 17 else 'black'
    
    ax.annotate(f'{int(height)}', 
                (p.get_x() + p.get_width() / 2., height), 
                ha='center', va='center', 
                xytext=(0, 9), 
                textcoords='offset points',
                fontsize=9, # Ukuran font sedikit dikecilkan agar tidak tumpang tindih
                fontweight='bold',
                color=text_color)

plt.title('Submission Trend Per Hour (Working Hours Highlighted)', fontsize=14, fontweight='bold')
plt.xlabel('Hour (24h Format)', fontsize=12)
plt.ylabel('Total Service', fontsize=12)
plt.xticks(rotation=0)
plt.grid(axis='y', linestyle='--', alpha=0.5)

plt.ylim(0, traffic_hour['total_service'].max() * 1.15)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.show()
