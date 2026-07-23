"""
app.py — Halaman Utama Inaportnet Analytics Dashboard
"""

import streamlit as st
import pandas as pd
from modules.database import is_connected

# ──────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Inaportnet Analytics",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# Custom CSS
# ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Hero header */
    .hero {
        background: linear-gradient(135deg, #0f2d52 0%, #1a4a7a 50%, #2471a3 100%);
        border-radius: 16px;
        padding: 2.5rem 2rem 2rem;
        margin-bottom: 1.5rem;
        color: white;
    }
    .hero h1 { font-size: 2.4rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
    .hero p  { font-size: 1.05rem; margin: 0.4rem 0 0; opacity: 0.85; }
    .hero .badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        border-radius: 20px;
        padding: 3px 14px;
        font-size: 0.8rem;
        margin-top: 0.6rem;
    }

    /* Status pill */
    .status-ok   { background:#d4edda; color:#155724; border-radius:20px; padding:4px 14px; font-size:0.82rem; font-weight:600; }
    .status-warn { background:#fff3cd; color:#856404; border-radius:20px; padding:4px 14px; font-size:0.82rem; font-weight:600; }
    .status-err  { background:#f8d7da; color:#721c24; border-radius:20px; padding:4px 14px; font-size:0.82rem; font-weight:600; }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid #e8ecf0;
        border-radius: 12px;
        padding: 1.2rem 1rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .metric-card .val   { font-size: 2rem; font-weight: 700; color: #1a4a7a; }
    .metric-card .label { font-size: 0.82rem; color: #6c757d; margin-top: 2px; }
    .metric-card .sub   { font-size: 0.75rem; color: #adb5bd; margin-top: 1px; }

    /* Nav cards */
    .nav-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-top: 1rem; }
    .nav-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.4rem 1rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
    }
    .nav-card:hover { border-color: #2471a3; box-shadow: 0 4px 16px rgba(36,113,163,0.15); transform: translateY(-2px); }
    .nav-card .icon  { font-size: 2rem; }
    .nav-card .title { font-weight: 600; color: #1a4a7a; font-size: 0.95rem; margin-top: 0.5rem; }
    .nav-card .desc  { color: #6c757d; font-size: 0.78rem; margin-top: 4px; }

    /* Step card */
    .step-card {
        background: #f8fafc;
        border-left: 4px solid #1a4a7a;
        border-radius: 0 10px 10px 0;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
    }
    .step-card .step-num { color: #1a4a7a; font-weight: 700; font-size: 0.85rem; }
    .step-card .step-txt { color: #374151; font-size: 0.93rem; margin-top: 2px; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #0f2d52; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stMarkdown p { color: rgba(255,255,255,0.7) !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15); }

    /* Hide Streamlit default footer */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🚢 Inaportnet Analytics")
    st.markdown("---")
    st.markdown("**Navigasi**")
    st.page_link("app.py",                                      label="🏠 Beranda")
    st.page_link("pages/1_📊_Data_Collection.py",               label="📊 Data Collection")
    st.page_link("pages/2_🚦_Traffic_Overview.py",              label="🚦 Traffic Overview")
    st.page_link("pages/3_📋_Service_Performance.py",           label="📋 Service Performance")
    st.page_link("pages/4_🗺️_Port_Classification.py",           label="🗺️ Port Classification")
    st.page_link("pages/5_🗄️_Database_Viewer.py",               label="🗄️ Database Viewer")
    st.markdown("---")

    # Status koneksi database
    st.markdown("**Status Database**")
    db_connected = is_connected()
    if db_connected:
        st.markdown('<span class="status-ok">✅ Supabase Terhubung</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-warn">⚠️ Supabase Tidak Terhubung</span>', unsafe_allow_html=True)

    # Status data di sesi
    st.markdown("**Data Sesi**")
    if "df" in st.session_state and not st.session_state["df"].empty:
        n = len(st.session_state["df"])
        st.markdown(f'<span class="status-ok">✅ {n:,} record dimuat</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-err">❌ Belum ada data</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<p style="font-size:0.75rem; opacity:0.5;">v1.0 · 2025</p>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Hero Header
# ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🚢 Inaportnet Analytics</h1>
    <p>Sistem Analisis Performa Layanan PKK — 259 Pelabuhan Indonesia</p>
    <span class="badge">📅 Tahun 2025</span>
    <span class="badge" style="margin-left:8px">🗺️ Kemenhub — Inaportnet</span>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Metric cards (jika data sudah dimuat)
# ──────────────────────────────────────────────────────────────
if "df" in st.session_state and not st.session_state["df"].empty:
    from modules.analysis import get_national_stats
    stats = get_national_stats(st.session_state["df"])

    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, f"{stats.get('total_pkk', 0):,}",          "Total PKK",            "Data tersedia"),
        (c2, f"{stats.get('active_ports', 0)}",          "Pelabuhan Aktif",      "Dari 259 pelabuhan"),
        (c3, f"{stats.get('mean_minutes', 0):.1f} mnt",  "Rata-rata Persetujuan","Waktu approval"),
        (c4, f"{stats.get('median_minutes', 0):.1f} mnt","Median Persetujuan",   "Waktu approval"),
        (c5, f"{stats.get('sla_rate', 0):.1f}%",         "SLA Compliance",       "< 30 menit"),
    ]
    for col, val, label, sub in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="val">{val}</div>
                <div class="label">{label}</div>
                <div class="sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Navigation cards
# ──────────────────────────────────────────────────────────────
st.markdown("### 📌 Navigasi Halaman")
st.markdown("""
<div class="nav-grid" style="grid-template-columns: repeat(5, 1fr);">
    <div class="nav-card">
        <div class="icon">📊</div>
        <div class="title">Data Collection</div>
        <div class="desc">Scraping, upload data, load dari Supabase, dan ekspor</div>
    </div>
    <div class="nav-card">
        <div class="icon">🚦</div>
        <div class="title">Traffic Overview</div>
        <div class="desc">Volume, tren per kuartal, bulan, hari, dan jam</div>
    </div>
    <div class="nav-card">
        <div class="icon">📋</div>
        <div class="title">Service Performance</div>
        <div class="desc">Distribusi waktu approval, SLA compliance, dan tren</div>
    </div>
    <div class="nav-card">
        <div class="icon">🗺️</div>
        <div class="title">Port Classification</div>
        <div class="desc">Analisis kuadran dan ranking composite index</div>
    </div>
    <div class="nav-card">
        <div class="icon">🗄️</div>
        <div class="title">Database Viewer</div>
        <div class="desc">Inspeksi database live, pencarian, dan unduh CSV/Excel/JSON/SQL</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# How to use
# ──────────────────────────────────────────────────────────────
col_how, col_info = st.columns([3, 2])

with col_how:
    st.markdown("### 📖 Cara Penggunaan")
    steps = [
        ("1", "Buka halaman **📊 Data Collection**"),
        ("2", "Pilih pelabuhan, tahun, dan jenis angkutan"),
        ("3", "Klik **Mulai Scraping** atau upload file / load dari Supabase"),
        ("4", "Data otomatis tersimpan ke Supabase dan session"),
        ("5", "Jelajahi analisis di halaman **Traffic**, **SLA**, dan **Klasifikasi**"),
        ("6", "Ekspor hasil analisis ke CSV atau Excel"),
    ]
    for num, txt in steps:
        st.markdown(f"""
        <div class="step-card">
            <div class="step-num">Langkah {num}</div>
            <div class="step-txt">{txt}</div>
        </div>
        """, unsafe_allow_html=True)

with col_info:
    st.markdown("### ℹ️ Tentang Sistem")
    st.info(
        "**Sumber Data:** Portal Monitoring Inaportnet\n\n"
        "https://monitoring-inaportnet.dephub.go.id\n\n"
        "**Layanan:** PKK (Persetujuan Kegiatan Kapal)\n\n"
        "**Cakupan:** 259 pelabuhan di seluruh Indonesia\n\n"
        "**SLA:** Persetujuan dalam ≤ 30 menit"
    )
    st.warning(
        "⚠️ **Konfigurasi Supabase**\n\n"
        "Isi kredensial di `.streamlit/secrets.toml` agar data dapat disimpan ke database."
    )

# ──────────────────────────────────────────────────────────────
# Developer Footer & Buy Coffee Section
# ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="background: linear-gradient(135deg, #0f2d52 0%, #1a4a7a 100%); color: white; padding: 1.5rem 2rem; border-radius: 14px; text-align: center; margin-top: 2.5rem; box-shadow: 0 4px 15px rgba(15, 45, 82, 0.15);">
    <h3 style="margin: 0 0 0.5rem 0; color: #ffffff; font-size: 1.2rem;">🚀 Built for Indonesian Maritime Data Excellence</h3>
    <p style="font-size: 0.95rem; opacity: 0.9; margin-bottom: 0.8rem;">
        Crafted with passion & precision by 
        <a href="https://github.com/ekacs" target="_blank" style="color: #64ffda; text-decoration: none; font-weight: 600;">@ekacs</a> 
        & 
        <a href="https://github.com/rifkiwijaya12" target="_blank" style="color: #64ffda; text-decoration: none; font-weight: 600;">@rifkiw</a>
    </p>
    <p style="font-size: 0.85rem; opacity: 0.8; max-width: 650px; margin: 0 auto 1.2rem auto; line-height: 1.4;">
        Transforming Inaportnet port operational data into actionable strategic insights across 259 ports in Indonesia. 🌊⚓
    </p>
    <div style="display: inline-block; background: rgba(255,255,255,0.12); padding: 0.6rem 1.4rem; border-radius: 30px; font-size: 0.9rem; border: 1px solid rgba(255,255,255,0.2);">
        ☕ <b>Suka dengan platform ini?</b> Traktir kopi untuk kami biar makin semangat berinovasi!
    </div>
</div>
""", unsafe_allow_html=True)
