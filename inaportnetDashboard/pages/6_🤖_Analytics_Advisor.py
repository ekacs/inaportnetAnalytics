"""
pages/6_🤖_Analytics_Advisor.py
Fitur AI Policy & Risk Advisor yang terintegrasi untuk evaluasi mendalam pelabuhan spesifik.
"""

import sys
from pathlib import Path

# Ensure inaportnetDashboard directory is in sys.path for Streamlit Cloud
dashboard_dir = str(Path(__file__).resolve().parent.parent)
if dashboard_dir not in sys.path:
    sys.path.insert(0, dashboard_dir)

import streamlit as st
import pandas as pd
import numpy as np
from modules.analysis import (
    compute_port_summary, compute_performance_indices, classify_quadrant,
    AHP_DEFAULT_WEIGHTS, calculate_ahp_matrix_consistency,
    generate_port_specific_ai_insight
)
from modules.database import is_connected, fetch_pkk_records_with_progress, render_sidebar_sync_widget
from modules.theme import render_theme_selector

st.set_page_config(page_title="Analytics Advisor · Inaportnet", page_icon="🤖", layout="wide")
render_theme_selector()
render_sidebar_sync_widget()

# ── Custom CSS Styles ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.advisor-hero {
    background: linear-gradient(135deg, #0f2d52 0%, #1a4a7a 50%, #2471a3 100%);
    color: white;
    border-radius: 16px;
    padding: 1.5rem 1.8rem;
    box-shadow: 0 10px 25px rgba(15,45,82,0.15);
    margin-bottom: 1.5rem;
}
.advisor-hero .title { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.3rem; }
.advisor-hero .subtitle { font-size: 0.9rem; opacity: 0.9; }

.hero-metric-box {
    background: rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    text-align: center;
}
.hero-metric-box .v { font-size: 1.6rem; font-weight: 700; color: #ffffff; }
.hero-metric-box .l { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.85; }

.card-container {
    background: #ffffff;
    border-radius: 14px;
    border: 1px solid #e2e8f0;
    padding: 1.3rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    margin-bottom: 1rem;
}
.card-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f2d52;
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.kpi-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.82rem;
}
.badge-green { background: #d4efdf; color: #1e8449; }
.badge-blue  { background: #d6eaf8; color: #1a5276; }
.badge-yellow{ background: #fdebd0; color: #784212; }
.badge-red   { background: #fadbd8; color: #922b21; }

.math-box {
    background: #f8fafc;
    border-left: 4px solid #2471a3;
    border-radius: 8px;
    padding: 1rem;
    font-family: monospace;
    font-size: 0.9rem;
}

footer{visibility:hidden;} #MainMenu{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar Navigation ────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🚢 Inaportnet Analytics")
    st.markdown("---")
    st.page_link("app.py",                               label="Beranda", icon="🏠")
    st.page_link("pages/1_📊_Data_Collection.py",        label="Data Collection")
    st.page_link("pages/2_🗄️_Database_Viewer.py",        label="Database Viewer")
    st.page_link("pages/3_🚦_Traffic_Overview.py",       label="Traffic Overview")
    st.page_link("pages/4_📋_Service_Performance.py",    label="Service Performance")
    st.page_link("pages/5_🗺️_Port_Classification.py",    label="Port Classification")
    st.page_link("pages/6_🤖_Analytics_Advisor.py",      label="Analytics Advisor")
    st.markdown("---")

    db_ok = is_connected()
    st.markdown("**Status Database**")
    if db_ok:
        st.success("✅ Supabase Terhubung")
    else:
        st.error("❌ Belum Terhubung")

# ── Data Loading & Preparation ────────────────────────────────
df_raw = st.session_state.get("df", pd.DataFrame())

if df_raw.empty:
    st.warning("⚠️ Belum ada data di memori aktif sesi. Silakan muat data dari Supabase di bawah ini atau melalui menu Data Collection.")
    if st.button("🔄 Auto-Load Data dari Supabase", type="primary", key="btn_advisor_autoload"):
        df_loaded = fetch_pkk_records_with_progress(page_size=5000, label="🔄 Memuat data Supabase...")
        if not df_loaded.empty:
            st.session_state["df"] = df_loaded
            st.rerun()
    st.stop()

# Hitung klasifikasi kuadran & indeks AHP
df_summary = compute_port_summary(df_raw)
active_weights = AHP_DEFAULT_WEIGHTS
ahp_metrics = calculate_ahp_matrix_consistency()
df_classified = compute_performance_indices(df_summary, weights=active_weights)
df_classified = classify_quadrant(df_classified)

# ── Header & Port Selector ───────────────────────────────────
st.title("🤖 Analytics Advisor (Policy & Risk)")
st.caption("Analisis Keputusan Kebijakan Operasional Pelabuhan Spesifik berbasis Multi-Criteria Decision Making (AHP) & Predictive Risk Engine.")

port_col = "port" if "port" in df_classified.columns else ("port_code" if "port_code" in df_classified.columns else df_classified.columns[0])
available_ports = sorted(df_classified[port_col].dropna().unique().tolist())

col_sel1, col_sel2 = st.columns([2.5, 1])
with col_sel1:
    selected_port = st.selectbox(
        "🏗️ **Pilih Pelabuhan Spesifik untuk Evaluasi & Pendapat Kebijakan:**",
        options=available_ports,
        index=0 if available_ports else None,
        key="advisor_port_selectbox"
    )

# Generasi Insight AI
port_ai = generate_port_specific_ai_insight(
    df_classified=df_classified,
    selected_port_name=selected_port,
    weights=active_weights,
    ahp_metrics=ahp_metrics
)

if not port_ai:
    st.error("Gagal memuat data evaluasi pelabuhan.")
    st.stop()

# ── Hero Banner Pelabuhan Terpilih ────────────────────────────
quadrant_name = port_ai["quadrant"]
if quadrant_name == "Benchmark Port":
    badge_class = "badge-green"
elif quadrant_name == "Efficient Port":
    badge_class = "badge-blue"
elif quadrant_name == "Developing Port":
    badge_class = "badge-yellow"
else:
    badge_class = "badge-red"

st.markdown(f"""
<div class="advisor-hero">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <div class="title">⚓ Pelabuhan {port_ai['selected_port']}</div>
            <div class="subtitle">Hasil Evaluasi Kinerja Komposit AHP & Diagnosis Kebijakan Strategis</div>
        </div>
        <div>
            <span class="kpi-badge {badge_class}" style="font-size: 0.95rem; padding: 6px 16px;">
                Kuadran: {quadrant_name}
            </span>
        </div>
    </div>
    <hr style="border-color: rgba(255,255,255,0.2); margin: 1rem 0;">
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem;">
        <div class="hero-metric-box">
            <div class="v">#{port_ai['rank_num']}</div>
            <div class="l">Peringkat Nasional</div>
        </div>
        <div class="hero-metric-box">
            <div class="v">{port_ai['composite_score']:.4f}</div>
            <div class="l">Skor Komposit AHP</div>
        </div>
        <div class="hero-metric-box">
            <div class="v">{port_ai['volume']:,}</div>
            <div class="l">Volume PKK</div>
        </div>
        <div class="hero-metric-box">
            <div class="v">{port_ai['sla_rate']:.1f}%</div>
            <div class="l">Kepatuhan SLA (&lt;30 mnt)</div>
        </div>
        <div class="hero-metric-box">
            <div class="v">{port_ai['mean_time']:.1f} mnt</div>
            <div class="l">Rata-rata Waktu Approval</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 5 Tab Evaluasi Utama ──────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 1. Bobot Prioritas AHP",
    "⚖️ 2. Uji Konsistensi (CR vs CI)",
    "💡 3. Implikasi Kebijakan",
    "⚠️ 4. Pernyataan Risiko Masa Depan",
    "🏆 5. Peringkat Pelabuhan Lengkap"
])

# ── TAB 1: BOBOT PRIORITAS AHP ────────────────────────────────
with tab1:
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">📊 1. Hasil Perhitungan Bobot Prioritas AHP & Evaluasi Kriteria</div>', unsafe_allow_html=True)
    
    # Visualisasi Grid Kriteria
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("SLA Compliance (CI)", f"{port_ai['weights']['ci']}%", help="Bobot Prioritas Tertinggi Saaty")
        st.caption(f"Skor Pelabuhan: **{port_ai['scores']['ci']}/100**")
    with c2:
        st.metric("Robustness Index (RI)", f"{port_ai['weights']['ri']}%", help="Ketahanan Terhadap Delay Ekstrem")
        st.caption(f"Skor Pelabuhan: **{port_ai['scores']['ri']}/100**")
    with c3:
        st.metric("Efficiency Index (EI)", f"{port_ai['weights']['ei']}%", help="Efisiensi Kecepatan Approval")
        st.caption(f"Skor Pelabuhan: **{port_ai['scores']['ei']}/100**")
    with c4:
        st.metric("Consistency Index (CsI)", f"{port_ai['weights']['csi']}%", help="Stabilitas Variabilitas Operasional")
        st.caption(f"Skor Pelabuhan: **{port_ai['scores']['csi']}/100**")

    st.markdown("---")
    st.markdown(port_ai["priority_weights_analysis"])
    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 2: UJI KONSISTENSI SAATY ──────────────────────────────
with tab2:
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">⚖️ 2. Simpulan Uji Konsistensi Rasio (CR) vs Consistency Index (CI)</div>', unsafe_allow_html=True)

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric("Eigenvalue Maks (λmax)", f"{port_ai['ahp_metrics']['lambda_max']:.4f}")
    with mc2:
        st.metric("Consistency Index (CI)", f"{port_ai['ahp_metrics']['ci']:.4f}")
    with mc3:
        st.metric("Random Index (RI, n=4)", "0.9000")
    with mc4:
        cr_pct = port_ai['ahp_metrics']['cr'] * 100
        st.metric("Consistency Ratio (CR)", f"{port_ai['ahp_metrics']['cr']:.4f}", f"{cr_pct:.2f}% (Limit <=10%)")

    if port_ai['ahp_metrics']['is_consistent']:
        st.success(f"✅ **Validitas Matematika Terpenuhi**: Nilai $CR = {port_ai['ahp_metrics']['cr']:.4f} \\le 0.10$ ({cr_pct:.2f}%). Matriks perbandingan AHP terbukti **SANGAT KONSISTEN** dan dapat dijadikan dasar kebijakan publik.")
    else:
        st.error("⚠️ Matriks perbandingan perpasangan memerlukan penyesuaian ulang (CR > 10%).")

    st.markdown("---")
    st.markdown(port_ai["consistency_test_summary"])
    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 3: IMPLIKASI KEBIJAKAN OPERASIONAL ────────────────────
with tab3:
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">💡 3. Implikasi Kebijakan Operasional (Kemenhub / Pelindo)</div>', unsafe_allow_html=True)
    
    st.markdown(f"Status Posisi Strategis: <span class='kpi-badge {badge_class}'>{quadrant_name}</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(port_ai["policy_implications"])
    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 4: PERNYATAAN RISIKO MASA DEPAN ───────────────────────
with tab4:
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">⚠️ 4. Pernyataan Risiko & Proyeksi Dampak Masa Depan</div>', unsafe_allow_html=True)

    risk_lvl = port_ai["risk_level"]
    if risk_lvl == "RENDAH":
        st.markdown("<span class='kpi-badge badge-green'>PROFIL RISIKO: RENDAH</span>", unsafe_allow_html=True)
    elif risk_lvl == "SEDANG":
        st.markdown("<span class='kpi-badge badge-yellow'>PROFIL RISIKO: SEDANG</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='kpi-badge badge-red'>PROFIL RISIKO: TINGGI</span>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(port_ai["future_risk_assessment"])
    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 5: TABEL PERINGKAT PELABUHAN LENGKAP ──────────────────
with tab5:
    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">🏆 5. Angka Peringkat Pelabuhan Berdasarkan Kinerja (Terbaik s.d. Terburuk)</div>', unsafe_allow_html=True)
    st.caption(f"Tabel pembanding posisi Pelabuhan **{port_ai['selected_port']}** (Peringkat **#{port_ai['rank_num']}**) terhadap seluruh **{port_ai['total_ports']}** pelabuhan nasional.")

    df_rank_display = port_ai["rankings_table"].copy()

    st.dataframe(
        df_rank_display,
        use_container_width=True,
        height=450,
        column_config={
            "rank": st.column_config.NumberColumn("Peringkat", format="#%d"),
            "port": st.column_config.TextColumn("Nama Pelabuhan"),
            "port_code": st.column_config.TextColumn("Kode"),
            "volume": st.column_config.NumberColumn("Volume PKK", format="%d"),
            "composite_index": st.column_config.NumberColumn("Skor Komposit AHP", format="%.4f"),
            "quadrant": st.column_config.TextColumn("Kuadran Klasifikasi"),
            "sla_compliance_pct": st.column_config.NumberColumn("Kepatuhan SLA (%)", format="%.1f%%"),
            "mean_response_time": st.column_config.NumberColumn("Rata Approval (mnt)", format="%.2f"),
        }
    )
    st.markdown('</div>', unsafe_allow_html=True)
