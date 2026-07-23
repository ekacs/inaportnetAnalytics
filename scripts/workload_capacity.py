#workload capacity
import pandas as pd
import numpy as np

sub_col  = 'submission' if 'submission' in df_join.columns else 'waktu_permohonan_real'
resp_col = 'response' if 'response' in df_join.columns else 'waktu_respon'

# approval times in minutes
df_join['processing_time_minutes'] = (pd.to_datetime(df_join[resp_col]) - pd.to_datetime(df_join[sub_col])).dt.total_seconds()/60

submission_dates = pd.to_datetime(df_join[sub_col])

daily_workload = (
    df_join.groupby(submission_dates.dt.date)
    .size()
    .reset_index(name='jumlah_permohonan')
    .rename(columns={sub_col: 'waktu_permohonan_real', 'index': 'waktu_permohonan_real'})
)
if 'waktu_permohonan_real' not in daily_workload.columns and len(daily_workload.columns) >= 2:
    daily_workload.columns = ['waktu_permohonan_real', 'jumlah_permohonan']


import matplotlib.pyplot as plt

#top 5 subsimision by date
top_5 = daily_workload.nlargest(5, 'jumlah_permohonan')

plt.figure(figsize=(12, 6))

#Create Plot
plt.plot(daily_workload['waktu_permohonan_real'], daily_workload['jumlah_permohonan'], label='Daily Requests', color='#1f77b4', linewidth=1.5)

for i, row in top_5.iterrows():
    # Ambil tanggal dan format ke string (Contoh: 15 Feb)
    date_label = row['waktu_permohonan_real'].strftime('%d %b') 
    
    plt.annotate(
        f"{date_label}\n({int(row['jumlah_permohonan'])})", # Menampilkan Tanggal dan Angka
        (row['waktu_permohonan_real'], row['jumlah_permohonan']),
        textcoords="offset points", 
        xytext=(0, 15), # Naikkan sedikit agar teks dua baris tidak menabrak titik
        ha='center', 
        fontsize=9, 
        fontweight='bold',
        color='red', 
        arrowprops=dict(arrowstyle='->', color='red', lw=1)
    )

#Complement the attribute
plt.title("Daily Workload (Top 5 Peaks Highlighted)", fontsize=14, fontweight='bold')
plt.xlabel("Date")
plt.ylabel("Number of Requests")
plt.xticks(rotation=45)
plt.grid(True, linestyle='--', alpha=0.6)

#Giving margin
plt.ylim(0, daily_workload['jumlah_permohonan'].max() * 1.2)

plt.tight_layout()
plt.show()
