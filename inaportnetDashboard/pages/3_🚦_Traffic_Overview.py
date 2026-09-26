"""
pages/3_🚦_Traffic_Overview.py
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
from modules.database import is_connected, get_db_status_info
from modules.theme import render_theme_selector
from modules.ui import (
    page_css, render_sidebar_nav, load_session_df, render_data_filters,
)

st.set_page_config(page_title="Traffic Overview · Inaportnet", page_icon="🚦", layout="wide")
render_theme_selector()

page_css()

# ── Sidebar ────────────────────────────────────
render_sidebar_nav()
# Filter + status DB: helper bersama (dulu 4x copy-paste per halaman)
df_sess = load_session_df()
selected_ports, selected_angkutan, _ = render_data_filters(
    df_sess,
    port_key="traffic_port_filter",
    angkutan_key="traffic_ang_filter",
)

# ── Cek data ──────────────────────────────────────────────────
st.markdown("# 🚦 Traffic Overview")

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
    st.warning("⚠️ Tidak ada data setelah filter. Sesuaikan pilihan filter.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────
from modules.progress import timed_status
with timed_status(st, "📊 Menghitung statistik nasional"):
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
    st.plotly_chart(fig_donut, width="stretch")

with col_table:
    st.markdown("**Top 10 Pelabuhan**")
    if not df_vol.empty:
        display_vol = df_vol.head(10)[["port", "volume", "share_pct"]].copy()
        display_vol.columns = ["Pelabuhan", "Volume", "Share (%)"]
        display_vol = display_vol.reset_index(drop=True)
        display_vol.index += 1
        st.dataframe(display_vol, width="stretch", height=380)

# ── Tren per Kuartal ─────────────────────────────────────────
st.markdown('<div class="section-title">📆 Tren Volume per Kuartal</div>', unsafe_allow_html=True)
if "quarter" in df.columns:
    df_qtr = get_trend_quarterly(df)
    st.plotly_chart(plot_trend_quarterly(df_qtr), width="stretch")
else:
    st.info("Kolom 'quarter' tidak tersedia.")

# ── Tren per Bulan ───────────────────────────────────────────
st.markdown('<div class="section-title">🗓️ Tren Volume per Bulan</div>', unsafe_allow_html=True)
if "month" in df.columns:
    df_mon = get_trend_monthly(df)
    st.plotly_chart(plot_trend_monthly(df_mon), width="stretch")
else:
    st.info("Kolom 'month' tidak tersedia.")

# ── Tren per Hari & per Jam ──────────────────────────────────
col_day, col_hour = st.columns(2)

with col_day:
    st.markdown('<div class="section-title">📅 Tren per Hari</div>', unsafe_allow_html=True)
    if "day" in df.columns:
        df_day = get_trend_daily(df)
        st.plotly_chart(plot_trend_daily(df_day), width="stretch")
    else:
        st.info("Kolom 'day' tidak tersedia.")

with col_hour:
    st.markdown('<div class="section-title">🕐 Tren per Jam</div>', unsafe_allow_html=True)
    if "hour" in df.columns:
        df_hour = get_trend_hourly(df)
        st.plotly_chart(plot_trend_hourly(df_hour), width="stretch")
    else:
        st.info("Kolom 'hour' tidak tersedia.")
