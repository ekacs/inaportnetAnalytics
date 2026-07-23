"""
pages/4_🗺️_Port_Classification.py
Analisis kuadran dan ranking composite performance index pelabuhan.
"""

import streamlit as st
import pandas as pd
import io
from modules.analysis import (
    compute_port_summary, compute_performance_indices, classify_quadrant,
)
from modules.visualization import plot_quadrant_scatter, plot_performance_ranking
from modules.database import is_connected
from modules.theme import render_theme_selector

st.set_page_config(page_title="Port Classification · Inaportnet", page_icon="🗺️", layout="wide")
render_theme_selector()

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
st.markdown("# 🗺️ Port Classification")
st.markdown("Klasifikasi 4 kuadran berdasarkan **volume PKK** dan **Composite Performance Index**.")

df_raw = st.session_state.get("df", pd.DataFrame())
if df_raw.empty:
    st.warning("⚠️ Belum ada data. Silakan ambil atau muat data di halaman **📊 Data Collection**.")
    st.stop()

# Terapkan filter angkutan
df = df_raw.copy()
if selected_angkutan:
    df = df[df["angkutan"].isin(selected_angkutan)]

if df.empty:
    st.warning("⚠️ Tidak ada data setelah filter.")
    st.stop()

# ── Hitung indeks ─────────────────────────────────────────────
@st.cache_data(show_spinner="Menghitung performance index...")
def compute_classification(df_hash: pd.DataFrame) -> pd.DataFrame:
    summary = compute_port_summary(df_hash)
    if summary.empty:
        return pd.DataFrame()
    perf    = compute_performance_indices(summary)
    result  = classify_quadrant(perf)
    return result

df_classified = compute_classification(df)

if df_classified.empty:
    st.warning("⚠️ Tidak cukup data untuk menghitung indeks performa.")
    st.stop()

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
st.plotly_chart(plot_quadrant_scatter(df_display), use_container_width=True)

# ── Ranking Composite Index ───────────────────────────────────
st.markdown('<div class="section-title">🏅 Ranking Composite Performance Index</div>', unsafe_allow_html=True)

col_rank, col_table = st.columns([2, 1])

with col_rank:
    st.plotly_chart(plot_performance_ranking(df_display, top_n=top_n_rank), use_container_width=True)

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
    st.dataframe(df_rank_tbl, use_container_width=True, height=450)

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
    st.dataframe(df_full, use_container_width=True)

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
        file_name="port_classification_2025.csv",
        mime="text/csv",
        use_container_width=True,
    )

with col_ex2:
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df_export.to_excel(writer, sheet_name="Port Classification", index=False)
    excel_buf.seek(0)
    st.download_button(
        "⬇️ Download Excel",
        data=excel_buf,
        file_name="port_classification_2025.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
