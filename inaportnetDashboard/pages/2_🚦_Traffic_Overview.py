"""
pages/2_🚦_Traffic_Overview.py
Analisis traffic PKK: volume, tren kuartal/bulan/hari/jam.
"""

import streamlit as st
import pandas as pd
from modules.analysis import (
    get_national_stats, get_port_volume,
    get_trend_quarterly, get_trend_monthly,
    get_trend_daily, get_trend_hourly,
)
from modules.visualization import (
    plot_volume_donut, plot_trend_quarterly,
    plot_trend_monthly, plot_trend_daily, plot_trend_hourly,
)
from modules.database import is_connected
from modules.theme import render_theme_selector

st.set_page_config(page_title="Traffic Overview · Inaportnet", page_icon="🚦", layout="wide")
render_theme_selector()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.kpi-card {
    background: linear-gradient(135deg, #1a4a7a, #2471a3);
    color: white;
    border-radius: 14px;
    padding: 1.2rem 1rem;
    text-align: center;
    box-shadow: 0 4px 16px rgba(26,74,122,0.18);
}
.kpi-card .val   { font-size: 2rem; font-weight: 700; }
.kpi-card .label { font-size: 0.82rem; opacity: 0.85; margin-top: 3px; }
.section-title   { font-size: 1.1rem; font-weight: 600; color: #1a4a7a; margin: 1.5rem 0 0.5rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }
.chart-card      { background: white; border-radius: 14px; padding: 1.2rem; border: 1px solid #e8ecf0; box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 1rem; }
footer{visibility:hidden;} #MainMenu{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🚢 Inaportnet Analytics")
    st.markdown("---")
    st.page_link("app.py",                               label="🏠 Beranda")
    st.page_link("pages/1_📊_Data_Collection.py",        label="📊 Data Collection")
    st.page_link("pages/2_🚦_Traffic_Overview.py",       label="🚦 Traffic Overview")
    st.page_link("pages/3_📋_Service_Performance.py",    label="📋 Service Performance")
    st.page_link("pages/4_🗺️_Port_Classification.py",    label="🗺️ Port Classification")
    st.page_link("pages/5_🗄️_Database_Viewer.py",        label="🗄️ Database Viewer")
    st.markdown("---")

    # Filter per pelabuhan
    df_sess = st.session_state.get("df", pd.DataFrame())
    if not df_sess.empty and "port" in df_sess.columns:
        all_ports = sorted(df_sess["port"].dropna().unique().tolist())
        selected_ports = st.multiselect(
            "🏗️ Filter Pelabuhan",
            options=all_ports,
            placeholder="Semua pelabuhan",
            key="traffic_port_filter",
        )
    else:
        selected_ports = []

    # Filter angkutan
    if not df_sess.empty and "angkutan" in df_sess.columns:
        angkutan_options = df_sess["angkutan"].dropna().unique().tolist()
        selected_angkutan = st.multiselect(
            "🚢 Filter Angkutan",
            options=angkutan_options,
            placeholder="Semua",
            key="traffic_ang_filter",
        )
    else:
        selected_angkutan = []

    st.markdown("---")
    db_ok = is_connected()
    if "df" in st.session_state and not st.session_state["df"].empty:
        st.success(f"✅ {len(st.session_state['df']):,} record")

# ── Cek data ──────────────────────────────────────────────────
st.markdown("# 🚦 Traffic Overview")

df_raw = st.session_state.get("df", pd.DataFrame())

if df_raw.empty:
    st.warning("⚠️ Belum ada data. Silakan ambil atau muat data di halaman **📊 Data Collection**.")
    st.stop()

# Terapkan filter
df = df_raw.copy()
if selected_ports:
    df = df[df["port"].isin(selected_ports)]
if selected_angkutan:
    df = df[df["angkutan"].isin(selected_angkutan)]

if df.empty:
    st.warning("⚠️ Tidak ada data setelah filter. Sesuaikan pilihan filter.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────
stats = get_national_stats(df)

c1, c2, c3, c4 = st.columns(4)
kpis = [
    (c1, f"{stats.get('total_pkk', 0):,}",    "Total PKK"),
    (c2, f"{stats.get('active_ports', 0)}",    "Pelabuhan Aktif"),
    (c3, f"{stats.get('mean_minutes', 0):.1f} mnt", "Rata-rata Persetujuan"),
    (c4, f"{stats.get('sla_rate', 0):.1f}%",  "SLA Compliance"),
]
for col, val, label in kpis:
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="val">{val}</div>
            <div class="label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Volume per Pelabuhan ──────────────────────────────────────
st.markdown('<div class="section-title">📍 Distribusi Volume per Pelabuhan</div>', unsafe_allow_html=True)

col_donut, col_table = st.columns([2, 1])

with col_donut:
    df_vol = get_port_volume(df)
    fig_donut = plot_volume_donut(df_vol)
    st.plotly_chart(fig_donut, use_container_width=True)

with col_table:
    st.markdown("**Top 10 Pelabuhan**")
    if not df_vol.empty:
        display_vol = df_vol.head(10)[["port", "volume", "share_pct"]].copy()
        display_vol.columns = ["Pelabuhan", "Volume", "Share (%)"]
        display_vol = display_vol.reset_index(drop=True)
        display_vol.index += 1
        st.dataframe(display_vol, use_container_width=True, height=380)

# ── Tren per Kuartal ─────────────────────────────────────────
st.markdown('<div class="section-title">📆 Tren Volume per Kuartal</div>', unsafe_allow_html=True)
if "quarter" in df.columns:
    df_qtr = get_trend_quarterly(df)
    st.plotly_chart(plot_trend_quarterly(df_qtr), use_container_width=True)
else:
    st.info("Kolom 'quarter' tidak tersedia.")

# ── Tren per Bulan ───────────────────────────────────────────
st.markdown('<div class="section-title">🗓️ Tren Volume per Bulan</div>', unsafe_allow_html=True)
if "month" in df.columns:
    df_mon = get_trend_monthly(df)
    st.plotly_chart(plot_trend_monthly(df_mon), use_container_width=True)
else:
    st.info("Kolom 'month' tidak tersedia.")

# ── Tren per Hari & per Jam ──────────────────────────────────
col_day, col_hour = st.columns(2)

with col_day:
    st.markdown('<div class="section-title">📅 Tren per Hari</div>', unsafe_allow_html=True)
    if "day" in df.columns:
        df_day = get_trend_daily(df)
        st.plotly_chart(plot_trend_daily(df_day), use_container_width=True)
    else:
        st.info("Kolom 'day' tidak tersedia.")

with col_hour:
    st.markdown('<div class="section-title">🕐 Tren per Jam</div>', unsafe_allow_html=True)
    if "hour" in df.columns:
        df_hour = get_trend_hourly(df)
        st.plotly_chart(plot_trend_hourly(df_hour), use_container_width=True)
    else:
        st.info("Kolom 'hour' tidak tersedia.")
