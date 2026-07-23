"""
pages/5_🗄️_Database_Viewer.py
Halaman penjelajah database Supabase secara langsung (Live Database Viewer)
dan opsi pengunduhan data dalam berbagai format (CSV, Excel, JSON, SQL).
"""

import streamlit as st
import pandas as pd
import io
import json
from modules.database import (
    is_connected, get_database_stats, fetch_pkk_records_paginated,
    fetch_pkk_records, generate_sql_dump
)
from modules.scraper import load_port_reference
from modules.theme import render_theme_selector

st.set_page_config(
    page_title="Database Viewer · Inaportnet",
    page_icon="🗄️",
    layout="wide"
)

render_theme_selector()

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.section-header {
    background: linear-gradient(90deg, #0f2d52, #1a4a7a);
    color: white;
    padding: 0.7rem 1.2rem;
    border-radius: 10px;
    font-size: 1.05rem;
    font-weight: 600;
    margin: 1.2rem 0 0.8rem;
}
.info-box {
    background: #eaf3fb;
    border-left: 4px solid #1a4a7a;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1rem;
    font-size: 0.88rem;
    color: #0f2d52;
}
.metric-card {
    background: white;
    border: 1px solid #e8ecf0;
    border-radius: 12px;
    padding: 1.1rem 1rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.metric-card .val   { font-size: 1.8rem; font-weight: 700; color: #1a4a7a; }
.metric-card .label { font-size: 0.82rem; color: #6c757d; margin-top: 2px; }
.metric-card .sub   { font-size: 0.75rem; color: #adb5bd; margin-top: 1px; }

footer{visibility:hidden;} #MainMenu{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar Navigation ────────────────────────────────────────
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
    
    db_ok = is_connected()
    st.markdown("**Status Database**")
    if db_ok:
        st.success("✅ Supabase Terhubung")
    else:
        st.warning("⚠️ Supabase Tidak Terhubung")
        
    if "df" in st.session_state and not st.session_state["df"].empty:
        st.markdown("**Data Sesi Analisis**")
        st.info(f"📌 {len(st.session_state['df']):,} record dimuat")

# ── Header ────────────────────────────────────────────────────
st.markdown("# 🗄️ Live Database Viewer & Downloader")
st.markdown("Inspeksi langsung database Supabase secara real-time, lakukan pencarian/filter, dan unduh database dalam berbagai format.")

if not db_ok:
    st.error("❌ **Koneksi Supabase Belum Terkonfigurasi**")
    st.info(
        "Isi kredensial `SUPABASE_URL` dan `SUPABASE_KEY` di file `.streamlit/secrets.toml` "
        "agar dapat melihat dan mengunduh database."
    )
    st.stop()

# ── Load Port Reference ───────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_port_ref():
    df = load_port_reference("data/port_code.xlsx")
    if df.empty:
        return pd.DataFrame()
    df = df.dropna(subset=["KODE"])
    df["label"] = df["KODE"].astype(str) + " — " + df["PELABUHAN"].astype(str)
    return df.drop_duplicates(subset=["KODE"]).reset_index(drop=True)

df_port_ref = load_port_ref()
port_labels = df_port_ref["label"].tolist() if not df_port_ref.empty else []
port_code_of = {row["label"]: row["KODE"] for _, row in df_port_ref.iterrows()} if not df_port_ref.empty else {}

# ── DB Ringkasan Metrik ────────────────────────────────────────
db_stats = get_database_stats()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="val">{db_stats.get('total_records', 0):,}</div>
        <div class="label">Total Record Database</div>
        <div class="sub">Tabel pkk_records</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="val">{db_stats.get('unique_ports', 0)}</div>
        <div class="label">Pelabuhan Terdaftar</div>
        <div class="sub">Kode LOCODE Unik</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div class="metric-card">
        <div class="val">2025</div>
        <div class="label">Tahun Data</div>
        <div class="sub">Inaportnet PKK</div>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown("""
    <div class="metric-card">
        <div class="val">Active</div>
        <div class="label">Status Server</div>
        <div class="sub">Supabase Cloud</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# FILTER & SEARCH CONTROLS
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🔍 Filter & Pencarian Database</div>', unsafe_allow_html=True)

col_f1, col_f2, col_f3 = st.columns([2, 2, 1])

with col_f1:
    search_q = st.text_input(
        "🔎 Cari PKK / Kapal",
        placeholder="Ketik Nomor PKK atau Nama Kapal...",
        help="Mencari kata kunci pada kolom pkk_number atau vessel_name."
    )

with col_f2:
    selected_ports_lbl = st.multiselect(
        "🏗️ Filter Pelabuhan",
        options=port_labels,
        placeholder="Kosongkan untuk semua pelabuhan...",
    )
    selected_port_codes = [port_code_of[lbl] for lbl in selected_ports_lbl if lbl in port_code_of]

with col_f3:
    year_sel = st.selectbox(
        "📅 Tahun",
        options=[None, 2025, 2024],
        index=0,
        format_func=lambda x: "Semua Tahun" if x is None else str(x)
    )

col_f4, col_f5, col_f6 = st.columns([1.5, 1, 1])

with col_f4:
    angkutan_sel = st.multiselect(
        "🚢 Jenis Angkutan",
        options=["dn — Domestik", "ln — Luar Negeri"],
        default=["dn — Domestik", "ln — Luar Negeri"],
    )
    angkutan_codes = [x.split(" — ")[0] for x in angkutan_sel]

with col_f5:
    page_size = st.selectbox("📄 Baris per Halaman", [50, 100, 250, 500, 1000, 5000], index=1)

with col_f6:
    current_page = st.number_input("📖 Halaman ke-", min_value=1, value=1, step=1)

offset_val = (current_page - 1) * page_size

# ════════════════════════════════════════════════════════════════
# FETCH DATA
# ════════════════════════════════════════════════════════════════
with st.spinner("Mengambil data langsung dari Supabase..."):
    df_db_view, total_filtered_count = fetch_pkk_records_paginated(
        port_codes=selected_port_codes if selected_port_codes else None,
        year=year_sel,
        angkutan=angkutan_codes if len(angkutan_codes) == 1 else None,
        search_query=search_q,
        limit=page_size,
        offset=offset_val,
    )

total_pages = max(1, (total_filtered_count + page_size - 1) // page_size)

# ── Data Table View Header ────────────────────────────────────
st.markdown('<div class="section-header">📊 Tampilan Tabel Database (Live View)</div>', unsafe_allow_html=True)

col_stat_info, col_btn_load = st.columns([3, 1])
with col_stat_info:
    st.markdown(
        f"**Menampilkan `{len(df_db_view):,}` dari `{total_filtered_count:,}` record terfilter** "
        f"(Halaman **{current_page}** dari **{total_pages}**)"
    )

with col_btn_load:
    if st.button("📥 Muat ke Sesi Analisis", type="primary", use_container_width=True):
        if not df_db_view.empty:
            st.session_state["df"] = df_db_view
            st.success(f"✅ **{len(df_db_view):,} record** dimuat ke sesi analisis aktif.")
        else:
            st.warning("⚠️ Tabel kosong, tidak ada data untuk dimuat.")

if total_filtered_count == 0 or df_db_view.empty:
    st.warning("⚠️ **Database Kosong atau Tidak Ada Data Terfilter**")
    st.info(
        "💡 **Petunjuk:** Jika Supabase baru dikonfigurasi dan masih kosong, silakan buka halaman "
        "**📊 Data Collection** lalu jalankan **Mulai Scraping** atau **Upload File** (pastikan centang 'Simpan otomatis ke Supabase') "
        "agar data tersimpan ke database."
    )
else:
    # Filter config keys dynamically
    available_cols = set(df_db_view.columns)
    col_cfg = {
        "PKK_number": st.column_config.TextColumn("Nomor PKK", width="medium"),
        "vessel_name": st.column_config.TextColumn("Nama Kapal", width="medium"),
        "port_code": st.column_config.TextColumn("Kode Port", width="small"),
        "port": st.column_config.TextColumn("Pelabuhan", width="medium"),
        "service": st.column_config.TextColumn("Layanan", width="small"),
        "submission": st.column_config.DatetimeColumn("Permohonan", format="YYYY-MM-DD HH:mm"),
        "response": st.column_config.DatetimeColumn("Persetujuan", format="YYYY-MM-DD HH:mm"),
        "approval_minutes": st.column_config.NumberColumn("Approval (mnt)", format="%.2f"),
        "approval_hours": st.column_config.NumberColumn("Approval (jam)", format="%.2f"),
        "angkutan": st.column_config.TextColumn("Angkutan", width="small"),
    }
    cfg_used = {k: v for k, v in col_cfg.items() if k in available_cols}

    # Render Interactive DataFrame
    st.dataframe(
        df_db_view,
        use_container_width=True,
        height=450,
        column_config=cfg_used
    )

# ════════════════════════════════════════════════════════════════
# DOWNLOAD DATABASE OPTIONS
# ════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">💾 Opsi Mengunduh Database</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="info-box">'
    'Pilih lingkup data yang ingin diunduh (Data Tampilan Halaman Ini vs Seluruh Data Terfilter dari Database), '
    'lalu pilih format file yang Anda butuhkan (CSV, Excel, JSON, atau SQL Dump).'
    '</div>',
    unsafe_allow_html=True
)

scope_option = st.radio(
    "🎯 Lingkup Data Unduhan:",
    options=[
        f"📄 Hanya Data di Halaman Ini ({len(df_db_view):,} record)",
        f"🌐 Seluruh Data Terfilter dari Supabase ({total_filtered_count:,} record)",
    ],
    index=0,
    horizontal=True,
)

if scope_option.startswith("🌐"):
    with st.spinner("Mengambil seluruh data terfilter dari Supabase untuk diunduh..."):
        df_download = fetch_pkk_records(
            port_codes=selected_port_codes if selected_port_codes else None,
            year=year_sel,
            angkutan=angkutan_codes if len(angkutan_codes) == 1 else None,
        )
else:
    df_download = df_db_view.copy()

if df_download.empty:
    st.warning("⚠️ Tidak ada data yang tersedia untuk diunduh.")
else:
    col_dl1, col_dl2, col_dl3, col_dl4 = st.columns(4)

    # 1. Download CSV
    with col_dl1:
        st.markdown("#### 📄 Format CSV")
        csv_bytes = df_download.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_bytes,
            file_name=f"inaportnet_pkk_db_{len(df_download)}_records.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # 2. Download Excel
    with col_dl2:
        st.markdown("#### 📊 Format Excel")
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
            df_download.to_excel(writer, sheet_name="Data PKK", index=False)
            if "port_code" in df_download.columns and "approval_minutes" in df_download.columns:
                from modules.analysis import compute_port_summary
                summary = compute_port_summary(df_download)
                if not summary.empty:
                    summary.to_excel(writer, sheet_name="Ringkasan Pelabuhan", index=False)
        excel_buf.seek(0)
        st.download_button(
            label="⬇️ Download Excel",
            data=excel_buf,
            file_name=f"inaportnet_pkk_db_{len(df_download)}_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # 3. Download JSON
    with col_dl3:
        st.markdown("#### 🌐 Format JSON")
        json_str = df_download.to_json(orient="records", date_format="iso", indent=2)
        st.download_button(
            label="⬇️ Download JSON",
            data=json_str.encode("utf-8"),
            file_name=f"inaportnet_pkk_db_{len(df_download)}_records.json",
            mime="application/json",
            use_container_width=True,
        )

    # 4. Download SQL Dump
    with col_dl4:
        st.markdown("#### 🗄️ Format SQL Dump")
        sql_dump = generate_sql_dump(df_download)
        st.download_button(
            label="⬇️ Download SQL Dump",
            data=sql_dump.encode("utf-8"),
            file_name=f"inaportnet_pkk_db_{len(df_download)}_records.sql",
            mime="application/sql",
            use_container_width=True,
        )
