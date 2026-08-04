"""
pages/5_🗺️_Port_Classification.py
Analisis kuadran dan ranking composite performance index pelabuhan berbasis Analytical Hierarchy Process (AHP).
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
import io
import os
from modules.analysis import (
    compute_port_summary, compute_performance_indices, classify_quadrant,
    AHP_DEFAULT_WEIGHTS, EQUAL_WEIGHTS, calculate_ahp_matrix_consistency,
    generate_ai_policy_insights, generate_port_specific_ai_insight
)
from modules.visualization import plot_quadrant_scatter, plot_performance_ranking
from modules.database import is_connected, render_sidebar_sync_widget
from modules.theme import render_theme_selector

st.set_page_config(page_title="Port Classification · Inaportnet", page_icon="🗺️", layout="wide")
render_theme_selector()
render_sidebar_sync_widget()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.section-title { font-size:1.1rem; font-weight:600; color:#1a4a7a; margin:1.5rem 0 0.5rem; border-bottom:2px solid #e2e8f0; padding-bottom:6px; }
.quadrant-pill {
    display:inline-block; border-radius:20px; padding:3px 12px;
    font-size:0.8rem; font-weight:600; margin:2px;
}
.q-benchmark { background:#d4efdf; color:#1e8449; }
.q-efficient { background:#d6eaf8; color:#1a5276; }
.q-developing{ background:#fdebd0; color:#784212; }
.q-congested { background:#fadbd8; color:#922b21; }
.legend-box  { background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:1rem; font-size:0.88rem; }
.ai-card     { background:linear-gradient(135deg, #f0f7ff, #e6f0fa); border-left:4px solid #1a4a7a; border-radius:8px; padding:1rem; margin-bottom:0.8rem; }
footer{visibility:hidden;} #MainMenu{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────
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

    # ── SKEMA PEMBOBOTAN PSPI (AHP vs EQUAL vs CUSTOM) ──
    st.markdown("### 🎯 Skema Pembobotan PSPI")
    weight_scheme = st.radio(
        "Pilih Model Pembobotan Indeks",
        options=[
            "🏆 AHP Scientifically Weighted (simulasi rekayasa pov auditor)",
            "⚖️ Equal Weighting (Klasik 25%)",
            "🎛️ Custom Weights (1% - 100%)",
        ],
        index=0,
        key="class_weight_scheme",
    )

    custom_weights = None
    if "Custom Weights" in weight_scheme:
        st.caption("Atur persentase bobot kriteria (1% - 100%):")
        c_ci  = st.slider("Compliance Index (CI)", 1, 100, 47, key="c_ci")
        c_ri  = st.slider("Robustness Index (RI)", 1, 100, 28, key="c_ri")
        c_ei  = st.slider("Efficiency Index (EI)", 1, 100, 17, key="c_ei")
        c_csi = st.slider("Consistency Index (CsI)", 1, 100, 8, key="c_csi")

        total_custom = c_ci + c_ri + c_ei + c_csi
        if total_custom != 100:
            st.warning(f"⚠️ Total bobot: **{total_custom}%** (akan otomatis dinormalisasi ke 100%).")
        else:
            st.success("✅ Total bobot persis **100%**.")

        custom_weights = {
            "ci": c_ci / 100,
            "ri": c_ri / 100,
            "ei": c_ei / 100,
            "csi": c_csi / 100,
        }

    st.markdown("---")

    df_sess = st.session_state.get("df", pd.DataFrame())

    # Filter angkutan
    if not df_sess.empty and "angkutan" in df_sess.columns:
        angk_opts = df_sess["angkutan"].dropna().unique().tolist()
        selected_angkutan = st.multiselect(
            "🚢 Filter Angkutan", options=angk_opts,
            placeholder="Semua", key="class_ang_filter",
        )
    else:
        selected_angkutan = []

    # Filter kuadran
    selected_quadrants = st.multiselect(
        "🗺️ Filter Kuadran",
        options=["Benchmark Port", "Efficient Port", "Developing Port", "Congested Port"],
        placeholder="Semua kuadran",
        key="class_quad_filter",
    )

    top_n_rank = st.slider("🏅 Top N Ranking", 5, 50, 20, 5, key="class_topn")
    st.markdown("---")
    if not df_sess.empty:
        st.success(f"✅ {len(df_sess):,} record")

# ── Header ────────────────────────────────────────────────────
st.title("🗺️ Port Classification & AHP Performance Index")
st.markdown("Klasifikasi 4 kuadran pelabuhan berbasis **Analytical Hierarchy Process (AHP Saaty 1-9)** dan **Volume PKK**.")

# ── Informasi & Download Tool AHP (Excel Reference) ─────────────
ahp_file_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "papers", "AHP_Analysis_Tool rev.xlsx")),
    os.path.abspath(os.path.join("papers", "AHP_Analysis_Tool rev.xlsx")),
    os.path.abspath(os.path.join("..", "papers", "AHP_Analysis_Tool rev.xlsx")),
]
target_ahp_path = next((p for p in ahp_file_paths if os.path.exists(p)), None)

with st.expander("📄 Informasi & Download Model Kalkulator AHP (Excel Reference)", expanded=False):
    st.markdown(
        "File **`AHP_Analysis_Tool rev.xlsx`** berisi model spreadsheet kalkulasi instrumen **Analytical Hierarchy Process (AHP)** "
        "yang meliputi matriks perbandingan berpasangan (*Pairwise Comparison Matrix*) 4 kriteria utama "
        "(*Compliance Index*, *Robustness Index*, *Efficiency Index*, dan *Consistency Index*), "
        "perhitungan eigenvector bobot indikator (*Scientifically Weighted*), serta pengujian rasio konsistensi "
        "(*Consistency Ratio* / CR = 0.0402 < 0.10) sebagai dasar ilmiah pembobotan indeks performa."
    )
    if target_ahp_path and os.path.exists(target_ahp_path):
        with open(target_ahp_path, "rb") as f:
            st.download_button(
                label="📥 Download AHP_Analysis_Tool rev.xlsx",
                data=f.read(),
                file_name="AHP_Analysis_Tool_rev.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_ahp_tool"
            )

df_raw = st.session_state.get("df", pd.DataFrame())
if df_raw.empty:
    st.warning("⚠️ Belum ada data di sesi ini.")
    if is_connected():
        if st.button("📥 Auto-Load Data dari Supabase", type="primary"):
            from modules.database import fetch_pkk_records_with_progress
            df_loaded = fetch_pkk_records_with_progress(page_size=5000)
            if not df_loaded.empty:
                st.session_state["df"] = df_loaded
                st.rerun()
            else:
                st.error("❌ Supabase masih kosong.")
    else:
        st.info("Silakan muat file data di halaman **📊 Data Collection**.")
    st.stop()

# Terapkan filter angkutan hanya jika ada pilihan (hemat RAM)
if selected_angkutan:
    df = df_raw[df_raw["angkutan"].isin(selected_angkutan)]
else:
    df = df_raw

if df.empty:
    st.warning("⚠️ Tidak ada data setelah filter.")
    st.stop()

# ── Tentukan Bobot Aktif ──
if "AHP" in weight_scheme:
    active_weights = AHP_DEFAULT_WEIGHTS
elif "Equal" in weight_scheme:
    active_weights = EQUAL_WEIGHTS
else:
    active_weights = custom_weights if custom_weights else AHP_DEFAULT_WEIGHTS

# ── Hitung indeks (Model Aktif vs Model Equal) ─────────────────
@st.cache_data(show_spinner="Menghitung Port Service Performance Index (PSPI)...")
def compute_classification_cached(df_hash: pd.DataFrame, weights: dict) -> pd.DataFrame:
    summary = compute_port_summary(df_hash)
    if summary.empty:
        return pd.DataFrame()
    perf    = compute_performance_indices(summary, weights=weights)
    result  = classify_quadrant(perf)
    return result

df_classified = compute_classification_cached(df, active_weights)
df_classified_equal = compute_classification_cached(df, EQUAL_WEIGHTS)

if df_classified.empty:
    st.warning("⚠️ Tidak cukup data untuk menghitung indeks performa.")
    st.stop()

# ── Info Badge AHP & Uji Konsistensi ──────────────────────────
ahp_metrics = calculate_ahp_matrix_consistency()
col_ahp1, col_ahp2, col_ahp3, col_ahp4 = st.columns(4)

with col_ahp1:
    st.metric(
        "🏆 Model Aktif",
        "AHP Saaty" if "AHP" in weight_scheme else ("Equal 25%" if "Equal" in weight_scheme else "Custom"),
        delta=f"CR = {ahp_metrics['cr']:.4f} (Konsisten)" if "AHP" in weight_scheme else "Model Klasik",
    )
with col_ahp2:
    st.metric("📋 Compliance (CI)", f"{active_weights['ci']*100:.2f}%", help="Kepatuhan SLA < 30 menit per PM 8/2022")
with col_ahp3:
    st.metric("🛡️ Robustness (RI)", f"{active_weights['ri']*100:.2f}%", help="Ketahanan terhadap delay > 120 menit")
with col_ahp4:
    st.metric("⚡ Efisiensi & Konsistensi", f"{(active_weights['ei']+active_weights['csi'])*100:.2f}%", help="EI (Response Time) + CsI (Variabilitas)")

st.markdown("<br>", unsafe_allow_html=True)

# Filter per kuadran (opsional)
df_display = df_classified.copy()
if selected_quadrants:
    df_display = df_display[df_display["quadrant"].isin(selected_quadrants)]

# ── Legenda Kuadran ───────────────────────────────────────────
col_leg1, col_leg2, col_leg3, col_leg4 = st.columns(4)
legends = [
    (col_leg1, "q-benchmark", "🟢 Benchmark Port",  "Volume Tinggi · Indeks Tinggi",  "Pelabuhan terbaik — efisien dan sibuk"),
    (col_leg2, "q-efficient", "🔵 Efficient Port",  "Volume Rendah · Indeks Tinggi",  "Pelabuhan kecil namun berkinerja baik"),
    (col_leg3, "q-developing","🟠 Developing Port", "Volume Rendah · Indeks Rendah",  "Perlu peningkatan layanan"),
    (col_leg4, "q-congested", "🔴 Congested Port",  "Volume Tinggi · Indeks Rendah",  "Padat namun layanan belum optimal"),
]
for col, cls, name, sub, desc in legends:
    with col:
        count = len(df_classified[df_classified["quadrant"] == name.split(" ", 1)[1]])
        st.markdown(f"""
        <div class="legend-box">
            <span class="quadrant-pill {cls}">{name}</span><br>
            <small style="color:#6c757d">{sub}</small><br>
            <b style="font-size:1.5rem; color:#1a4a7a">{count}</b>
            <small style="color:#6c757d"> pelabuhan</small><br>
            <small style="color:#9ca3af">{desc}</small>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Scatter Plot Kuadran ──────────────────────────────────────
st.markdown('<div class="section-title">📍 Analisis Kuadran — Scatter Plot Interaktif</div>', unsafe_allow_html=True)
st.plotly_chart(plot_quadrant_scatter(df_display), width="stretch")

# ── Ranking Composite Index ───────────────────────────────────
st.markdown('<div class="section-title">🏅 Ranking Composite Performance Index</div>', unsafe_allow_html=True)

col_rank, col_table = st.columns([2, 1])

with col_rank:
    st.plotly_chart(plot_performance_ranking(df_display, top_n=top_n_rank), width="stretch")

with col_table:
    st.markdown(f"**Top {top_n_rank} Pelabuhan**")
    display_cols = ["port", "volume", "composite_index", "quadrant"]
    available_cols = [c for c in display_cols if c in df_display.columns]
    df_rank_tbl = (
        df_display[available_cols]
        .head(top_n_rank)
        .reset_index(drop=True)
    )
    df_rank_tbl.index += 1

    rename_tbl = {
        "port": "Pelabuhan",
        "volume": "Volume",
        "composite_index": "Composite Index",
        "quadrant": "Kuadran",
    }
    df_rank_tbl = df_rank_tbl.rename(columns=rename_tbl)
    st.dataframe(df_rank_tbl, width="stretch", height=450)

# ──────────────────────────────────────────────────────────────
# 🧪 UJI SENSITIVITAS PELABUHAN PILIHAN PENGGUNA
# ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🧪 Uji Sensitivitas Dampak Pembobotan (Equal vs Model Pilihan)</div>', unsafe_allow_html=True)
st.caption("Pilih pelabuhan tertentu untuk menguji dan membandingkan pergeseran skor komposit dan kuadran secara langsung:")

port_col = "port" if "port" in df_classified.columns else ("port_code" if "port_code" in df_classified.columns else df_classified.columns[0])
all_ports_list = df_classified[port_col].dropna().unique().tolist()

default_selected_ports = all_ports_list[:5] if len(all_ports_list) >= 5 else all_ports_list

selected_sensitivity_ports = st.multiselect(
    "Pilih Pelabuhan yang Akan Diuji",
    options=all_ports_list,
    default=default_selected_ports,
    key="sens_ports_selector"
)

if selected_sensitivity_ports:
    merged_sens = df_classified[[port_col, "composite_index", "quadrant"]].merge(
        df_classified_equal[[port_col, "composite_index", "quadrant"]],
        on=port_col,
        suffixes=(" (Model Pilihan)", " (Equal 25%)")
    )
    merged_sens = merged_sens[merged_sens[port_col].isin(selected_sensitivity_ports)].copy()
    merged_sens["Pergeseran Delta"] = round(merged_sens["composite_index (Model Pilihan)"] - merged_sens["composite_index (Equal 25%)"], 4)
    merged_sens["composite_index (Model Pilihan)"] = merged_sens["composite_index (Model Pilihan)"].round(4)
    merged_sens["composite_index (Equal 25%)"] = merged_sens["composite_index (Equal 25%)"].round(4)

    # Reorder columns
    cols_order = [
        port_col, "composite_index (Equal 25%)", "composite_index (Model Pilihan)",
        "Pergeseran Delta", "quadrant (Equal 25%)", "quadrant (Model Pilihan)"
    ]
    st.dataframe(merged_sens[cols_order].reset_index(drop=True), width="stretch")
else:
    st.info("Pilih minimal satu pelabuhan pada dropdown di atas untuk melihat tabel komparasi sensitivitas.")

# ──────────────────────────────────────────────────────────────
# 💡 ANALISIS SINTESIS AI & IMPLIKASI KEBIJAKAN
# ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🤖 AI Executive Insights & Policy Recommendations</div>', unsafe_allow_html=True)

ai_insights = generate_ai_policy_insights(
    df_perf_current=df_classified,
    df_perf_equal=df_classified_equal,
    weights=active_weights,
    cr_val=ahp_metrics["cr"],
    selected_ports=selected_sensitivity_ports
)

tab_ai1, tab_ai2, tab_ai3, tab_ai4 = st.tabs([
    "📌 1. Bobot Prioritas",
    "📐 2. Uji Konsistensi (CR)",
    "🔬 3. Analisis Sensitivitas",
    "💡 4. Implikasi Kebijakan",
])

with tab_ai1:
    st.markdown('<div class="ai-card">', unsafe_allow_html=True)
    st.markdown("### 📌 Hasil Perhitungan Bobot Prioritas AHP")
    st.markdown(ai_insights["priority_weights"])
    st.markdown('</div>', unsafe_allow_html=True)

with tab_ai2:
    st.markdown('<div class="ai-card">', unsafe_allow_html=True)
    st.markdown("### 📐 Hasil Uji Konsistensi Saaty (Consistency Ratio)")
    st.markdown(ai_insights["consistency_test"])
    st.markdown(r"- **$\lambda_{max}$**: `" + f"{ahp_metrics['lambda_max']:.4f}`")
    st.markdown(f"- **Consistency Index ($CI$)**: `{ahp_metrics['ci']:.4f}`")
    st.markdown(f"- **Consistency Ratio ($CR$)**: `{ahp_metrics['cr']:.4f}` ({ahp_metrics['cr']*100:.2f}%)")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_ai3:
    st.markdown('<div class="ai-card">', unsafe_allow_html=True)
    st.markdown("### 🔬 Analisis Sensitivitas Dampak Skor Komposit")
    st.markdown(ai_insights["sensitivity_analysis"])
    st.markdown('</div>', unsafe_allow_html=True)

with tab_ai4:
    st.markdown('<div class="ai-card">', unsafe_allow_html=True)
    st.markdown("### 💡 Implikasi & Rekomendasi Kebijakan (Kemenhub / Pelindo)")
    st.markdown(ai_insights["policy_implications"])
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tabel Lengkap ─────────────────────────────────────────────
with st.expander("📋 Tabel Lengkap Semua Pelabuhan"):
    all_cols = [
        "port_code","port","volume","sla_compliance","mean_response_time",
        "coefficient_of_variation","extreme_delay_index",
        "compliance_index","efficiency_index","consistency_index",
        "robustness_index","composite_index","quadrant"
    ]
    show_cols = [c for c in all_cols if c in df_display.columns]
    df_full = df_display[show_cols].copy()

    # Format desimal
    float_cols = [c for c in show_cols if df_full[c].dtype == float]
    df_full[float_cols] = df_full[float_cols].round(4)
    st.dataframe(df_full, width="stretch")

# ── Ekspor Klasifikasi ────────────────────────────────────────
st.markdown('<div class="section-title">💾 Ekspor Hasil Klasifikasi</div>', unsafe_allow_html=True)

col_ex1, col_ex2 = st.columns(2)

show_cols_export = [c for c in all_cols if c in df_classified.columns]
df_export = df_classified[show_cols_export].copy()
df_export[[c for c in show_cols_export if df_export[c].dtype == float]] = \
    df_export[[c for c in show_cols_export if df_export[c].dtype == float]].round(4)

with col_ex1:
    csv = df_export.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ Download CSV",
        data=csv,
        file_name="port_classification_ahp_2025.csv",
        mime="text/csv",
        width="stretch",
    )

with col_ex2:
    excel_buf = io.BytesIO()
    df_excel = df_export.copy()
    for col in df_excel.columns:
        if pd.api.types.is_datetime64_any_dtype(df_excel[col]):
            try:
                df_excel[col] = df_excel[col].dt.tz_localize(None)
            except Exception:
                df_excel[col] = df_excel[col].astype(str)

    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df_excel.to_excel(writer, sheet_name="Port Classification AHP", index=False)
    excel_buf.seek(0)
    st.download_button(
        "⬇️ Download Excel",
        data=excel_buf,
        file_name="port_classification_ahp_2025.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

