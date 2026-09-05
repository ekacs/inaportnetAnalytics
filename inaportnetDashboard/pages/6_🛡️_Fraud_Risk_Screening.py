"""
pages/6_🛡️_Fraud_Risk_Screening.py
======================================
Halaman Analisis Composite Fraud Risk Screening Index (CFRSI)
Berdasarkan paper riset:
"Toward Data-Driven Anti-Fraud Governance: Anomaly Detection and
Composite Risk Scoring for Port-Level Oversight in Digital Maritime Services"
(Wijaya & Setyawan, 2026)
"""

import streamlit as st
import pandas as pd
import numpy as np
from modules.database import is_connected
from modules.theme import render_theme_selector
from modules.analysis import (
    compute_fraud_risk_analysis,
    get_fraud_national_summary,
)
from modules.visualization import (
    plot_volume_vs_red_flag_percentage,
    plot_red_flag_breakdown,
    plot_cfrsi_port_ranking,
    plot_subindices_breakdown,
    plot_risk_category_distribution,
)

# ──────────────────────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fraud Risk Screening — Inaportnet Analytics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_theme_selector()

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .hero-fraud {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #780206 100%);
        border-radius: 16px;
        padding: 2rem 2rem 1.6rem;
        margin-bottom: 1.5rem;
        color: white;
    }
    .hero-fraud h1 { font-size: 2.2rem; font-weight: 700; margin: 0; }
    .hero-fraud p  { font-size: 1rem; margin: 0.4rem 0 0; opacity: 0.9; }

    .metric-card {
        background: white;
        border: 1px solid #e8ecf0;
        border-radius: 12px;
        padding: 1.1rem 0.8rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .metric-card .val   { font-size: 1.8rem; font-weight: 700; color: #780206; }
    .metric-card .label { font-size: 0.82rem; color: #6c757d; margin-top: 2px; }
    .metric-card .sub   { font-size: 0.75rem; color: #adb5bd; margin-top: 1px; }

    [data-testid="stSidebar"] { background: #0f2d52; }
    [data-testid="stSidebar"] * { color: white !important; }
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
    st.markdown("**Metodologi Riset**")
    st.caption("Paper: Wijaya & Setyawan (2026)")
    st.caption("Kerangka CFRSI 3-Lapis (Rule, Stat, ML)")
    st.markdown("---")
    st.markdown('<p style="font-size:0.75rem; opacity:0.5;">v3.0 · 2026 CFRSI Edition</p>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Hero Header
# ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-fraud">
    <h1>🛡️ Fraud Risk Screening & CFRSI Engine</h1>
    <p>Sistem EWS Deteksi Anomali & Index Risiko Fraud Lintas Pelabuhan (Wijaya & Setyawan, 2026)</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Data Session Handling
# ──────────────────────────────────────────────────────────────
has_data = "df" in st.session_state and not st.session_state["df"].empty

if not has_data:
    st.warning("⚠️ **Belum ada data transaksi di sesi.** Anda dapat memuat data dari halaman Data Collection atau mengklik tombol simulasi data 257 pelabuhan di bawah ini untuk melihat demo analisis CFRSI.")
    
    if st.button("🎲 Generate Benchmark Dataset (257 Pelabuhan)", type="primary"):
        np.random.seed(42)
        n_records = 15000
        ports = [f"IDPRT_{i:03d}" for i in range(1, 258)]
        # Sertakan beberapa pelabuhan bernama dari paper
        known_ports = ["Lahewa", "Samarinda", "Pomako", "Sinabang", "Benete", "Labuhan", "Susoh", "Raha", "Banjarmasin", "Benoa", "Balikpapan", "Banten", "Tanjung Priok", "Tanjung Perak"]
        for idx, k_port in enumerate(known_ports):
            ports[idx] = k_port

        sim_df = pd.DataFrame({
            "port_code": np.random.choice(ports, n_records),
            "approval_minutes": np.random.exponential(scale=32, size=n_records),
            "gt": np.random.randint(500, 35000, size=n_records),
            "hour": np.random.randint(0, 24, size=n_records),
            "day": np.random.choice(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], size=n_records),
            "vessel_name": [f"Kapal_{i}" for i in np.random.randint(1, 600, size=n_records)],
            "submission_time": pd.date_range("2025-01-01", periods=n_records, freq="30min"),
        })
        sim_df["port"] = sim_df["port_code"]
        st.session_state["df"] = sim_df
        st.rerun()

if "df" in st.session_state and not st.session_state["df"].empty:
    df_raw = st.session_state["df"]

    # Jalankan Analisis CFRSI & Deteksi Anomali
    with st.spinner("Mengoperasikan Engine Deteksi Anomali 3-Lapis (Rule-Based, OLS Z-Score, Isolation Forest)..."):
        df_analyzed, cfrsi_df = compute_fraud_risk_analysis(df_raw)

    summary_stats = get_fraud_national_summary(df_analyzed, cfrsi_df)

    # ──────────────────────────────────────────────────────────────
    # KPI Metric Cards
    # ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, f"{summary_stats.get('total_pkk', 0):,}",       "Total PKK Evaluasi",   "Scope 2025"),
        (c2, f"{summary_stats.get('red_flag_pct', 0):.2f}%", "Transaksi Red Flag",   f"{summary_stats.get('red_flag_pkk', 0):,} transaksi"),
        (c3, f"{summary_stats.get('stat_pct', 0):.2f}%",     "Statistical Outliers",  "Modified Z <= -2.5"),
        (c4, f"{summary_stats.get('ml_pct', 0):.2f}%",       "Isolation Forest",     "Contamination 7%"),
        (c5, f"{summary_stats.get('high_risk_ports', 0)}",   "Pelabuhan Risiko Tinggi", "Tinggi & Sangat Tinggi"),
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
    # Interactive Tabs
    # ──────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Composite Risk Index (CFRSI)",
        "🚨 Rule-Based Red Flags",
        "📐 Statistical & ML Anomalies",
        "📜 Anti-Fraud Governance & Risk Tiers"
    ])

    # ── TAB 1: CFRSI RANKING ──────────────────────────────────────
    with tab1:
        st.markdown("### 🏆 Ranking Composite Fraud Risk Screening Index (CFRSI)")
        st.info("💡 **Penjelasan CFRSI:** CFRSI mengintegrasikan sub-indeks Rule-Based, Statistical (OLS Z-score), dan Machine Learning (Isolation Forest) dengan normalisasi Min-Max `[0.10 - 1.00]` dan bobot seimbang (equal weighting). Skor yang tinggi menunjukkan sinyal anomali operasional akumulatif (*red flag*).")

        col_top, col_sub = st.columns([1, 1])
        with col_top:
            top_n = st.slider("Tampilkan Top N Pelabuhan", min_value=5, max_value=30, value=15)
            st.plotly_chart(plot_cfrsi_port_ranking(cfrsi_df, top_n=top_n), use_container_width=True)

        with col_sub:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.plotly_chart(plot_subindices_breakdown(cfrsi_df, top_n=min(10, top_n)), use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📋 Tabel Ringkasan Risiko Fraud per Pelabuhan")
        
        # Filter Risk Tier
        tier_filter = st.multiselect(
            "Filter Kategori Risiko (Fixed Scale):",
            options=["Sangat Tinggi", "Tinggi", "Sedang", "Rendah", "Sangat Rendah"],
            default=["Sangat Tinggi", "Tinggi", "Sedang", "Rendah", "Sangat Rendah"]
        )
        
        filtered_cfrsi = cfrsi_df[cfrsi_df["risk_tier_fixed"].astype(str).isin(tier_filter)]
        
        cols_table = ["port_code", "volume", "total_red_flags", "red_flag_pct", "rule_based_index", "statistical_index", "ml_index", "cfrsi", "risk_tier_fixed"]
        st.dataframe(
            filtered_cfrsi[cols_table].rename(columns={
                "port_code": "Kode Pelabuhan",
                "volume": "Volume PKK",
                "total_red_flags": "Total Red Flags",
                "red_flag_pct": "Red Flag %",
                "rule_based_index": "Rule Index",
                "statistical_index": "Stat Index",
                "ml_index": "ML Index",
                "cfrsi": "Skor CFRSI",
                "risk_tier_fixed": "Tingkat Risiko"
            }),
            use_container_width=True,
            height=350
        )

    # ── TAB 2: RULE-BASED RED FLAGS ──────────────────────────────
    with tab2:
        st.markdown("### 🚨 Analisis Deteksi Anomali Berbasis Aturan (Rule-Based)")
        st.markdown("Menilai transaksi yang melanggar 5 aturan operasional/regulasi (*PM 93/2013*, *PM 8/2022*, & *PP 61/2009*).")

        c_pie, c_scat = st.columns([1, 1])
        with c_pie:
            st.plotly_chart(plot_red_flag_breakdown(df_analyzed), use_container_width=True)
        with c_scat:
            st.plotly_chart(plot_volume_vs_red_flag_percentage(cfrsi_df), use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🔍 Detil 5 Kriteria Red Flag & Dasar Justifikasi Regulasi")
        
        rf_expander = st.expander("📌 Klik untuk melihat perincian 5 aturan Red Flag & referensi hukum", expanded=True)
        with rf_expander:
            st.markdown("""
            1. **Quick Approval (< 10 detik):** Berdasarkan PM 93/2013, petugas harus memverifikasi beberapa dokumen keselamatan dan kelaiklautan. Persetujuan kilat memicu risiko tidak dilakukannya verifikasi memadai (*rubber-stamping*).
            2. **Long Duration (> 8 jam):** Durasi persetujuan melebihi standar jam kerja normal (8 jam) menciptakan celah potensi permintaan imbalan/bribes untuk mempercepat persetujuan.
            3. **Low Oversight (00.00 – 04.00):** Pengajuan/persetujuan di luar jam operasional standar dengan tingkat pengawasan minim sering dimanfaatkan untuk menghindari atensi supervisor.
            4. **GT Manipulation:** Modifikasi data Gross Tonnage (GT) kapal secara abnormal atau mendadak mengindikasikan potensi markdown dimensi untuk menghindari tarif PNBP.
            5. **Same Vessel in 2 Ports (< 2 jam):** Pergerakan kapal yang sama terdaftar disetujui di 2 pelabuhan berbeda dalam jeda < 2 jam tidak realistis secara geografis/kecepatan layar (PP 61/2009).
            """)

    # ── TAB 3: STATISTICAL & ML ANOMALIES ─────────────────────────
    with tab3:
        st.markdown("### 📐 Analisis Outlier Statistik & Machine Learning")
        
        st_col1, st_col2 = st.columns(2)
        with st_col1:
            st.markdown("#### 1. Model Regresi OLS & Modified Z-Score")
            st.latex(r"T_i = \beta_0 + \beta_1 V + \beta_2 GT + \beta_3 D + \beta_4 H")
            st.latex(r"Z_i = 0.6745 \frac{r_i - \bar{r}}{\text{MAD}} \le -2.5")
            st.write(f"• **Jumlah Outlier Residual ($Z \le -2.5$):** {summary_stats.get('stat_pkk', 0):,} transaksi ({summary_stats.get('stat_pct', 0):.}%)")
            st.caption("Menyoroti deviasi residual negatif yang ekstrem (persetujuan abnormal yang jauh lebih cepat dibanding ekspektasi kondisi operasional).")

        with st_col2:
            st.markdown("#### 2. Isolation Forest (Unsupervised ML)")
            st.write("• **Estimators:** 100 trees | **Max Samples:** 256")
            st.write("• **Contamination:** 0.07 (7% target anomali)")
            st.write("• **Features:** Log Approval Duration, Log GT, Log Port Volume, Hour")
            st.write(f"• **Jumlah Anomali Multidimensi Terisolasi:** {summary_stats.get('ml_pkk', 0):,} transaksi ({summary_stats.get('ml_pct', 0):.}%)")
            st.caption("Mendeteksi pola kombinasi fitur non-linear kompleks yang tidak terjangkau oleh aturan manual.")

    # ── TAB 4: GOVERNANCE & RISK TIERS ───────────────────────────
    with tab4:
        st.markdown("### 📜 Tata Kelola Anti-Fraud & Klasifikasi Risiko")

        st.plotly_chart(plot_risk_category_distribution(cfrsi_df), use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🏛️ Penerapan 4 Pilar Strategi Anti-Fraud (OJK 2024 / Kemenhub)")
        
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.markdown("""
            <div style="background:#eaf2f8; padding:1rem; border-radius:10px; border-left:4px solid #2980b9;">
                <h4 style="color:#1a4a7a; margin-top:0;">1. Pencegahan</h4>
                <p style="font-size:0.85rem;">Standardisasi verifikasi dokumen digital & pembatasan akses sistem persetujuan otomatis di luar jam kerja.</p>
            </div>
            """, unsafe_allow_html=True)
        with g2:
            st.markdown("""
            <div style="background:#fef9e7; padding:1rem; border-radius:10px; border-left:4px solid #f39c12;">
                <h4 style="color:#7e5109; margin-top:0;">2. Deteksi</h4>
                <p style="font-size:0.85rem;">Monitoring skor CFRSI real-time sebagai Early Warning System (EWS) untuk alokasi audit berbasis risiko.</p>
            </div>
            """, unsafe_allow_html=True)
        with g3:
            st.markdown("""
            <div style="background:#fdedec; padding:1rem; border-radius:10px; border-left:4px solid #e74c3c;">
                <h4 style="color:#780206; margin-top:0;">3. Investigasi</h4>
                <p style="font-size:0.85rem;">Eskalasi pelabuhan kategori Risiko Tinggi ke Inspektorat Jenderal untuk verifikasi lapangan & penindakan.</p>
            </div>
            """, unsafe_allow_html=True)
        with g4:
            st.markdown("""
            <div style="background:#eafaf1; padding:1rem; border-radius:10px; border-left:4px solid #27ae60;">
                <h4 style="color:#196f3d; margin-top:0;">4. Evaluasi</h4>
                <p style="font-size:0.85rem;">Umpan balik audit untuk re-kalibrasi threshold model & penanganan false-positive berulang.</p>
            </div>
            """, unsafe_allow_html=True)
