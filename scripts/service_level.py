#SLA risk
import pandas as pd

SLA_HOURS = 1

code_col = 'port_code' if 'port_code' in df_join.columns else 'KODE'
port_col = 'port' if 'port' in df_join.columns else 'PELABUHAN'
sub_col  = 'submission' if 'submission' in df_join.columns else 'waktu_permohonan_real'

compliance_port = (
    df_join
    .groupby([code_col, port_col])
    .agg(
        submission_total=('approval_hours','count'),
        over_sla=('approval_hours', lambda x: (x > SLA_HOURS).sum())
    )
    .reset_index()
)

compliance_port['over_sla_percentage'] = (
    compliance_port['over_sla'] / compliance_port['submission_total'] * 100
)

compliance_port = compliance_port.sort_values(
    'over_sla_percentage',
    ascending=False
)

compliance_port.head(10)

#SLA Trend per Month
df_join['month'] = pd.to_datetime(df_join[sub_col]).dt.to_period('M')

sla_trend = (
    df_join
    .groupby('month')
    .agg(
        total_permohonan=('approval_hours','count'),
        over_sla=('approval_hours', lambda x: (x > SLA_HOURS).sum())
    )
    .reset_index()
)

sla_trend['persen_over_sla'] = (
    sla_trend['over_sla'] / sla_trend['total_permohonan'] * 100
)

sla_trend

