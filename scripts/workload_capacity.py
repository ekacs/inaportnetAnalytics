#workload capacity
import pandas as pd
import numpy as np

# approval times in minutes
df_join['processing_time_minutes'] = (df_join['waktu_respon'] - df_join['waktu_permohonan_real']).dt.total_seconds()/60

daily_workload = (
    df_join.groupby(df_join['waktu_permohonan_real'].dt.date)
    .size()
    .reset_index(name='jumlah_permohonan')
)

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
