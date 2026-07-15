#service performance
#national statistics on service performance
national_service = {
    "total_permohonan": int(df_join.shape[0]),
    "mean_hours": df_join['approval_hours'].mean(),
    "median_hours": df_join['approval_hours'].median(),
    "p90_hours": df_join['approval_hours'].quantile(0.90),
    "p95_hours": df_join['approval_hours'].quantile(0.95),
    "max_hours": df_join['approval_hours'].max()
}
import pandas as pd

# Mengonversi dictionary menjadi DataFrame
df_national_service = pd.DataFrame(list(national_service.items()), columns=['Metric', 'Value'])

# Menampilkan tabel
df_national_service


service_port = (
    df_join
    .groupby(['KODE','PELABUHAN'])
    .agg(
        total_permohonan=('approval_hours','count'),
        mean_hours=('approval_hours','mean'),
        median_hours=('approval_hours','median'),
        p90_hours=('approval_hours', lambda x: x.quantile(0.90)),
        max_hours=('approval_hours','max')
    )
    .reset_index()
)

service_port = service_port.sort_values(
    'median_hours', ascending=False
)

service_port.head(10)

bins = [0,1,2,6,12,24,999]
labels = ['<1 hour','1-2 hours','2-6 hours','6-12 hours','12-24 hours','>24 hours']

df_join['time_category'] = pd.cut(
    df_join['approval_hours'],
    bins=bins,
    labels=labels
)
distribution_service = df_join['time_category'].value_counts().reset_index()
distribution_service.columns = ['category', 'total_service']

distribution_service['sla_status'] = distribution_service['category'].apply(
    lambda x: 'Within SLA' if x == '<1 hour'
    else 'Over SLA'
)

distribution_service['percentage'] = distribution_service['total_service']/df_join.shape[0]*100

distribution_service
