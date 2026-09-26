"""
pages/4_📋_Service_Performance.py
Analisis SLA dan performa layanan PKK.
"""

import streamlit as st
import pandas as pd
from modules.analysis import (
    get_national_stats, get_service_distribution,
    get_top_longest_approval, get_sla_compliance_by_port,
    get_sla_trend_monthly,
)
from modules.visualization import (
    plot_service_distribution, plot_approval_histogram,
    plot_top_longest_approval, plot_sla_compliance_bar,
    plot_sla_trend,
)
from modules.theme import render_theme_selector
from modules.database import get_db_status_info
from modules.progress import timed_status
from modules.ui import (
    page_css, render_sidebar_nav, load_session_df, render_data_filters,
)

st.set_page_config(page_title="Service Performance · Inaportnet", page_icon="📋", layout="wide")
render_theme_selector()

page_css()

# ── Sidebar ────────────────────────────────────
render_sidebar_nav()
# Filter + status DB: helper bersama (dulu 4x copy-paste per halaman)
df_sess = load_session_df()
selected_ports, selected_angkutan, _extras = render_data_filters(
    df_sess,
    port_key="perf_port_filter",
    angkutan_key="perf_ang_filter",
    extra_widgets={
        "sla_threshold": lambda: st.slider(
            "⏱️ SLA Threshold (menit)", min_value=5, max_value=120,
            value=30, step=5,
            help="Batas waktu persetujuan yang dianggap memenuhi SLA.",
            key="sla_threshold",
        ),
    },
)
sla_threshold = _extras["sla_threshold"]

df_raw = st.session_state.get("df", pd.DataFrame())
if df_raw.empty:
    st.warning("⚠️ Belum ada data. Silakan ambil atau muat data di halaman **📊 Data Collection**.")
    st.stop()

# Terapkan filter. Boolean masking sudah menghasilkan frame baru, jadi tidak
# perlu .copy() penuh di awal — yang penting df tidak pernah jadi alias
# df_raw kalau tidak ada filter aktif (agar mutasi di hilir tidak bocor ke
# st.session_state["df"]).
df = df_raw
if selected_ports:
    df = df[df["port"].isin(selected_ports)]
if selected_angkutan:
    df = df[df["angkutan"].isin(selected_angkutan)]

if df.empty:
    st.warning("⚠️ Tidak ada data setelah filter.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────
with timed_status(st, "📊 Menghitung statistik & SLA nasional"):
    stats = get_national_stats(df)
    sla_rate = stats.get("sla_rate", 0)
mean_min = stats.get("mean_minutes", 0)
med_min  = stats.get("median_minutes", 0)
p95_min  = stats.get("p95_minutes", 0)

sla_cls  = "kpi-ok" if sla_rate >= 80 else "kpi-warn" if sla_rate >= 50 else "kpi-bad"
mean_cls = "kpi-ok" if mean_min <= 30 else "kpi-warn" if mean_min <= 60 else "kpi-bad"

c1, c2, c3, c4 = st.columns(4)
kpis = [
    (c1, sla_cls,  f"{sla_rate:.1f}%",    "SLA Compliance"),
    (c2, mean_cls, f"{mean_min:.1f} mnt",  "Rata-rata Waktu"),
    (c3, "kpi-neu", f"{med_min:.1f} mnt", "Median Waktu"),
    (c4, "kpi-warn", f"{p95_min:.1f} mnt","Persentil 95"),
]
for col, cls, val, label in kpis:
    with col:
        st.markdown(f"""
        <div class="{cls}">
            <div class="val">{val}</div>
            <div class="label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Distribusi Waktu & Histogram ──────────────────────────────
st.markdown('<div class="section-title">📊 Distribusi Waktu Persetujuan</div>', unsafe_allow_html=True)

col_dist, col_hist = st.columns(2)

with col_dist:
    df_dist = get_service_distribution(df)
    if not df_dist.empty:
        st.plotly_chart(plot_service_distribution(df_dist), width="stretch")

with col_hist:
    if "approval_minutes" in df.columns:
        st.plotly_chart(plot_approval_histogram(df), width="stretch")
    else:
        st.info("Kolom 'approval_minutes' tidak tersedia.")

# ── Top 10 Terlama ───────────────────────────────────────────
st.markdown('<div class="section-title">⏳ Top 10 Pelabuhan — Waktu Persetujuan Terlama</div>', unsafe_allow_html=True)
df_top = get_top_longest_approval(df, n=10)
if not df_top.empty:
    st.plotly_chart(plot_top_longest_approval(df_top), width="stretch")
else:
    st.info("Data tidak tersedia.")

# ── SLA per Pelabuhan ─────────────────────────────────────────
st.markdown(f'<div class="section-title">✅ SLA Compliance per Pelabuhan (threshold: {sla_threshold} menit)</div>', unsafe_allow_html=True)

df_sla = get_sla_compliance_by_port(df, sla_minutes=sla_threshold)
if not df_sla.empty:
    n_show = st.slider("Tampilkan N pelabuhan terburuk", 10, min(50, len(df_sla)), 20, 5, key="sla_n")
    st.plotly_chart(plot_sla_compliance_bar(df_sla, top_n=n_show), width="stretch")

    with st.expander("📋 Tabel Lengkap SLA per Pelabuhan"):
        cols = [c for c in ["port_code", "port", "total", "compliant", "compliance_rate"] if c in df_sla.columns]
        display_sla = df_sla[cols].copy()
        rename_map = {
            "port_code": "Kode",
            "port": "Pelabuhan",
            "total": "Total PKK",
            "compliant": "Dalam SLA",
            "compliance_rate": "Compliance (%)",
        }
        display_sla = display_sla.rename(columns=rename_map)
        sort_col = "Compliance (%)" if "Compliance (%)" in display_sla.columns else display_sla.columns[0]
        st.dataframe(display_sla.sort_values(sort_col, ascending=True), width="stretch")

# ── Tren SLA per Bulan ────────────────────────────────────────
st.markdown(f'<div class="section-title">📈 Tren SLA Compliance per Bulan</div>', unsafe_allow_html=True)
df_trend = get_sla_trend_monthly(df, sla_minutes=sla_threshold)
if not df_trend.empty:
    st.plotly_chart(plot_sla_trend(df_trend), width="stretch")
else:
    st.info("Kolom 'month' tidak tersedia.")
