"""
pages/3_📋_Service_Performance.py
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
from modules.database import is_connected

st.set_page_config(page_title="Service Performance · Inaportnet", page_icon="📋", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.kpi-ok   { background: linear-gradient(135deg,#1e8449,#27ae60); color:white; border-radius:14px; padding:1.2rem 1rem; text-align:center; box-shadow:0 4px 16px rgba(30,132,73,.18); }
.kpi-warn { background: linear-gradient(135deg,#b7770d,#f39c12); color:white; border-radius:14px; padding:1.2rem 1rem; text-align:center; box-shadow:0 4px 16px rgba(183,119,13,.18); }
.kpi-bad  { background: linear-gradient(135deg,#922b21,#e74c3c); color:white; border-radius:14px; padding:1.2rem 1rem; text-align:center; box-shadow:0 4px 16px rgba(146,43,33,.18); }
.kpi-neu  { background: linear-gradient(135deg,#1a4a7a,#2471a3); color:white; border-radius:14px; padding:1.2rem 1rem; text-align:center; box-shadow:0 4px 16px rgba(26,74,122,.18); }
.val      { font-size:2rem; font-weight:700; }
.label    { font-size:0.82rem; opacity:0.85; margin-top:3px; }
.section-title { font-size:1.1rem; font-weight:600; color:#1a4a7a; margin:1.5rem 0 0.5rem; border-bottom:2px solid #e2e8f0; padding-bottom:6px; }
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
    st.markdown("---")

    df_sess = st.session_state.get("df", pd.DataFrame())

    # Filter pelabuhan
    if not df_sess.empty and "port" in df_sess.columns:
        all_ports = sorted(df_sess["port"].dropna().unique().tolist())
        selected_ports = st.multiselect(
            "🏗️ Filter Pelabuhan", options=all_ports,
            placeholder="Semua pelabuhan", key="sla_port_filter",
        )
    else:
        selected_ports = []

    # Filter angkutan
    if not df_sess.empty and "angkutan" in df_sess.columns:
        angk_opts = df_sess["angkutan"].dropna().unique().tolist()
        selected_angkutan = st.multiselect(
            "🚢 Filter Angkutan", options=angk_opts,
            placeholder="Semua", key="sla_ang_filter",
        )
    else:
        selected_angkutan = []

    # SLA threshold
    sla_threshold = st.slider(
        "⏱️ SLA Threshold (menit)", min_value=5, max_value=120,
        value=30, step=5,
        help="Batas waktu persetujuan yang dianggap memenuhi SLA.",
        key="sla_threshold",
    )
    st.markdown("---")
    if "df" in st.session_state and not st.session_state["df"].empty:
        st.success(f"✅ {len(st.session_state['df']):,} record")

# ── Header ────────────────────────────────────────────────────
st.markdown("# 📋 Service Performance")

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
    st.warning("⚠️ Tidak ada data setelah filter.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────
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
        st.plotly_chart(plot_service_distribution(df_dist), use_container_width=True)

with col_hist:
    if "approval_minutes" in df.columns:
        st.plotly_chart(plot_approval_histogram(df), use_container_width=True)
    else:
        st.info("Kolom 'approval_minutes' tidak tersedia.")

# ── Top 10 Terlama ───────────────────────────────────────────
st.markdown('<div class="section-title">⏳ Top 10 Pelabuhan — Waktu Persetujuan Terlama</div>', unsafe_allow_html=True)
df_top = get_top_longest_approval(df, n=10)
if not df_top.empty:
    st.plotly_chart(plot_top_longest_approval(df_top), use_container_width=True)
else:
    st.info("Data tidak tersedia.")

# ── SLA per Pelabuhan ─────────────────────────────────────────
st.markdown(f'<div class="section-title">✅ SLA Compliance per Pelabuhan (threshold: {sla_threshold} menit)</div>', unsafe_allow_html=True)

df_sla = get_sla_compliance_by_port(df, sla_minutes=sla_threshold)
if not df_sla.empty:
    n_show = st.slider("Tampilkan N pelabuhan terburuk", 10, min(50, len(df_sla)), 20, 5, key="sla_n")
    st.plotly_chart(plot_sla_compliance_bar(df_sla, top_n=n_show), use_container_width=True)

    with st.expander("📋 Tabel Lengkap SLA per Pelabuhan"):
        display_sla = df_sla[["port_code","port","total","compliant","compliance_rate"]].copy()
        display_sla.columns = ["Kode","Pelabuhan","Total PKK","Dalam SLA","Compliance (%)"]
        st.dataframe(display_sla.sort_values("Compliance (%)", ascending=True), use_container_width=True)

# ── Tren SLA per Bulan ────────────────────────────────────────
st.markdown(f'<div class="section-title">📈 Tren SLA Compliance per Bulan</div>', unsafe_allow_html=True)
df_trend = get_sla_trend_monthly(df, sla_minutes=sla_threshold)
if not df_trend.empty:
    st.plotly_chart(plot_sla_trend(df_trend), use_container_width=True)
else:
    st.info("Kolom 'month' tidak tersedia.")
