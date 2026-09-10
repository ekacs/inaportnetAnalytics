"""
app.py — Halaman Utama Inaportnet Analytics Dashboard
"""

import streamlit as st
from modules.database import is_connected, get_db_status_info
from modules.theme import render_theme_selector

# ──────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Inaportnet Analytics",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_theme_selector()

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

    /* Hide Streamlit default footer and default navigation */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    [data-testid="stSidebarNav"] { display: none !important; }
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
    st.page_link("pages/6_🛡️_Fraud_Risk_Screening.py",          label="🛡️ Fraud Risk Screening")
    st.markdown("---")

    # Status koneksi database
    st.markdown("**Status Database**")
    db_info = get_db_status_info()
    st.markdown(f'<span class="{db_info["badge_class"]}">{db_info["label"]}</span>', unsafe_allow_html=True)

    # Tombol konfigurasi Supabase (jika belum terhubung)
    if db_info["mode"] == "sqlite":
        if st.button("⚙️ Konfigurasi Supabase", use_container_width=True, type="primary"):
            st.session_state["show_supabase_modal"] = True

    # Status data di sesi
    st.markdown("**Data Sesi**")
    from modules.database import get_database_stats

    if "df" in st.session_state and not st.session_state["df"].empty:
        _db_check = get_database_stats()
        if _db_check.get("total_records", 0) == 0:
            st.session_state.pop("df", None)
            st.rerun()

    if "df" in st.session_state and not st.session_state["df"].empty:
        n = len(st.session_state["df"])
        st.markdown(f'<span class="status-ok">✅ {n:,} record dimuat</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-err">❌ Belum ada data</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<p style="font-size:0.75rem; opacity:0.5;">v3.0 · 2026 CFRSI Edition</p>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Hero Header
# ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🚢 Inaportnet Analytics</h1>
    <p>Sistem Analisis Performa & Fraud Risk Screening Index (CFRSI) Layanan PKK — 257+ Pelabuhan Indonesia</p>
    <span class="badge">📅 Tahun 2025</span>
    <span class="badge" style="margin-left:8px">🛡️ CFRSI Anti-Fraud Engine Enabled</span>
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
        (c2, f"{stats.get('active_ports', 0)}",          "Pelabuhan Aktif",      "Dari 257 pelabuhan"),
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
# Navigation cards (clickable)
# ──────────────────────────────────────────────────────────────
st.markdown("### 📌 Navigasi Halaman")

# CSS khusus untuk nav cards yang bisa diklik
st.markdown("""
<style>
/* ── Nav Cards: setiap kolom berisi card + link ── */
div[data-testid="stColumn"] .nav-card-wrap {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.4rem 1rem 0.4rem;
    text-align: center;
    transition: all 0.22s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    cursor: pointer;
}
div[data-testid="stColumn"] .nav-card-wrap:hover {
    border-color: #2471a3;
    box-shadow: 0 6px 20px rgba(36,113,163,0.16);
    transform: translateY(-3px);
}
.nav-card-icon  { font-size: 2.2rem; line-height: 1; }
.nav-card-title { font-weight: 700; color: #1a4a7a; font-size: 0.92rem; margin: 0.5rem 0 0.2rem; }
.nav-card-desc  { color: #6c757d; font-size: 0.76rem; line-height: 1.4; margin-bottom: 0.6rem; }

/* page_link di dalam card: tampak sebagai "Buka" kecil di bawah desc */
div[data-testid="stColumn"] [data-testid="stPageLink"] {
    margin-top: 0 !important;
}
div[data-testid="stColumn"] a[data-testid="stPageLink-NavLink"] {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    background: #eaf3fb !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 4px 0 !important;
    margin: 0 0 0.5rem !important;
    color: #1a4a7a !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-decoration: none !important;
    width: 100% !important;
    transition: background 0.18s !important;
}
div[data-testid="stColumn"] a[data-testid="stPageLink-NavLink"]:hover {
    background: #1a4a7a !important;
    color: white !important;
}
div[data-testid="stColumn"] a[data-testid="stPageLink-NavLink"] p {
    font-size: 0.78rem !important;
    margin: 0 !important;
    color: inherit !important;
}
</style>
""", unsafe_allow_html=True)

nav_pages = [
    {
        "page":  "pages/1_📊_Data_Collection.py",
        "icon":  "📊",
        "title": "Data Collection",
        "desc":  "Scraping, upload data, load dari database, dan ekspor",
    },
    {
        "page":  "pages/2_🚦_Traffic_Overview.py",
        "icon":  "🚦",
        "title": "Traffic Overview",
        "desc":  "Volume, tren per kuartal, bulan, hari, dan jam",
    },
    {
        "page":  "pages/3_📋_Service_Performance.py",
        "icon":  "📋",
        "title": "Service Performance",
        "desc":  "Distribusi waktu approval, SLA compliance, dan tren",
    },
    {
        "page":  "pages/4_🗺️_Port_Classification.py",
        "icon":  "🗺️",
        "title": "Port Classification",
        "desc":  "Analisis kuadran dan ranking composite index",
    },
    {
        "page":  "pages/5_🗄️_Database_Viewer.py",
        "icon":  "🗄️",
        "title": "Database Viewer",
        "desc":  "Inspeksi database live, pencarian, dan unduh CSV/Excel/JSON/SQL",
    },
    {
        "page":  "pages/6_🛡️_Fraud_Risk_Screening.py",
        "icon":  "🛡️",
        "title": "Fraud Risk Screening",
        "desc":  "Skor CFRSI 3-lapis (Rule, Stat, ML) & 5-tier klasifikasi risiko",
    },
]

cols = st.columns(6, gap="small")
for col, nav in zip(cols, nav_pages):
    with col:
        # Visual card content
        st.markdown(f"""
        <div class="nav-card-wrap">
            <div class="nav-card-icon">{nav["icon"]}</div>
            <div class="nav-card-title">{nav["title"]}</div>
            <div class="nav-card-desc">{nav["desc"]}</div>
        </div>
        """, unsafe_allow_html=True)
        # Clickable page_link shown as "→ Buka" button below the card content
        st.page_link(nav["page"], label="→ Buka", use_container_width=True)


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
        "**SLA:** Persetujuan dalam ≤ 30 menit"
    )
    st.warning(
        "⚠️ **Konfigurasi Supabase**\n\n"
        "Untuk menyimpan data ke database cloud, buka halaman **📊 Data Collection** "
        "→ klik **⚙️ Settings** di sidebar → masukkan **Supabase URL** dan **API Key**."
    )

# ──────────────────────────────────────────────────────────────
# Supabase Connection Modal
# ──────────────────────────────────────────────────────────────
if st.session_state.get("show_supabase_modal", False):
    with st.expander("⚙️ Konfigurasi Koneksi Supabase", expanded=True):
        st.info(
            "Masukkan kredensial Supabase Anda. Dapatkan dari dashboard Supabase → Settings → API."
        )
        col1, col2 = st.columns(2)
        with col1:
            supabase_url = st.text_input(
                "Supabase URL",
                value=st.session_state.get("supabase_url", ""),
                placeholder="https://xxxxx.supabase.co",
            )
        with col2:
            supabase_key = st.text_input(
                "Supabase Anon Key",
                value=st.session_state.get("supabase_key", ""),
                type="password",
                placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            )

        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("🔌 Hubungkan", type="primary", use_container_width=True):
                if not supabase_url or not supabase_key:
                    st.error("❌ URL dan Key harus diisi.")
                else:
                    from modules.database import set_supabase_credentials
                    with st.spinner("Menghubungkan ke Supabase..."):
                        if set_supabase_credentials(supabase_url, supabase_key):
                            st.success("✅ Berhasil terhubung ke Supabase!")
                            st.toast("✅ Supabase terhubung!", icon="✅")
                            st.session_state["show_supabase_modal"] = False
                            st.rerun()
                        else:
                            st.error("❌ Gagal terhubung. Periksa URL dan Key.")
        with col_btn2:
            if st.button("❌ Tutup", use_container_width=True):
                st.session_state["show_supabase_modal"] = False
                st.rerun()
        with col_btn3:
            if st.session_state.get("supabase_connected"):
                if st.button("🔌 Putuskan", use_container_width=True):
                    from modules.database import clear_supabase_credentials
                    clear_supabase_credentials()
                    st.success("✅ Koneksi diputus.")
                    st.toast("🔌 Koneksi diputus.", icon="🔌")
                    st.rerun()

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
