"""
pages/1_📊_Data_Collection.py
Halaman pengumpulan data: scraping Inaportnet, upload file eksternal,
load dari Supabase, dan ekspor data.
"""

import streamlit as st
import pandas as pd
import io
import zipfile
from modules.scraper      import run_full_scraping, load_port_reference
from modules.preprocessing import preprocess, validate_uploaded_file
from modules.database      import (
    insert_pkk_records, fetch_pkk_records, is_connected,
    deduplicate_dataframe
)
from modules.theme import render_theme_selector

st.set_page_config(page_title="Data Collection · Inaportnet", page_icon="📊", layout="wide")
render_theme_selector()

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.section-header {
    background: linear-gradient(90deg, #1a4a7a, #2471a3);
    color: white;
    padding: 0.7rem 1.2rem;
    border-radius: 10px;
    font-size: 1.05rem;
    font-weight: 600;
    margin: 1.2rem 0 0.8rem;
}
.info-box {
    background: #eaf3fb;
    border-left: 4px solid #2471a3;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1rem;
    font-size: 0.88rem;
    color: #1a4a7a;
}
.stat-pill {
    display:inline-block;
    background:#dbeafe;
    color:#1e40af;
    border-radius:20px;
    padding:2px 12px;
    font-size:0.82rem;
    font-weight:600;
    margin:2px;
}
footer{visibility:hidden;} #MainMenu{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────
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
    db_ok = is_connected()
    st.markdown("**Status Database**")
    if db_ok:
        st.success("✅ Supabase Terhubung")
    else:
        st.warning("⚠️ Supabase Tidak Terhubung")

    if "df" in st.session_state and not st.session_state["df"].empty:
        st.markdown("**Data Sesi**")
        st.success(f"✅ {len(st.session_state['df']):,} record")

# ── Header ────────────────────────────────────────────────────
st.markdown("# 📊 Data Collection")
st.markdown("Ambil, unggah, atau muat data PKK pelabuhan untuk analisis.")

# ── Load referensi pelabuhan ──────────────────────────────────
@st.cache_data(show_spinner=False)
def load_port_ref():
    df = load_port_reference("data/port_code.xlsx")
    if df.empty:
        return pd.DataFrame()
    df = df.dropna(subset=["KODE"])
    df["label"] = df["KODE"].astype(str) + " — " + df["PELABUHAN"].astype(str)
    return df.drop_duplicates(subset=["KODE"]).reset_index(drop=True)

df_port_ref = load_port_ref()
port_labels  = df_port_ref["label"].tolist() if not df_port_ref.empty else []
port_code_of = {row["label"]: row["KODE"] for _, row in df_port_ref.iterrows()} if not df_port_ref.empty else {}

# ════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ════════════════════════════════════════════════════════════════
tab_scrape, tab_upload, tab_supabase, tab_export = st.tabs([
    "🌐 Scraping",
    "📁 Upload File",
    "🗄️ Load dari Supabase",
    "💾 Ekspor Data",
])

# ────────────────────────────────────────────────────────────────
# TAB 1 — SCRAPING
# ────────────────────────────────────────────────────────────────
with tab_scrape:
    st.markdown('<div class="section-header">⚙️ Konfigurasi Scraping</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Pilih pelabuhan yang ingin di-scraping. Semakin banyak pelabuhan dan bulan, semakin lama prosesnya.</div>', unsafe_allow_html=True)

    col_cfg1, col_cfg2 = st.columns([3, 1])

    with col_cfg1:
        selected_labels = st.multiselect(
            "🏗️ Pilih Pelabuhan",
            options=port_labels,
            placeholder="Ketik nama atau kode pelabuhan...",
            help="Pilih satu atau lebih pelabuhan yang akan di-scraping.",
        )

    with col_cfg2:
        year_sel = st.selectbox("📅 Tahun", [2025, 2024], index=0)

    col_ang, col_month = st.columns([1, 2])
    with col_ang:
        angkutan_sel = st.multiselect(
            "🚢 Jenis Angkutan",
            options=["dn — Domestik", "ln — Luar Negeri"],
            default=["dn — Domestik"],
            help="dn = domestik, ln = luar negeri",
        )
        angkutan_codes = [x.split(" — ")[0] for x in angkutan_sel]

    with col_month:
        bulan_range = st.select_slider(
            "📆 Rentang Bulan",
            options=list(range(1, 13)),
            value=(1, 12),
            format_func=lambda x: ["", "Jan","Feb","Mar","Apr","Mei","Jun",
                                    "Jul","Agu","Sep","Okt","Nov","Des"][x],
        )
        months_list = list(range(bulan_range[0], bulan_range[1] + 1))

    selected_port_codes = [port_code_of[lbl] for lbl in selected_labels if lbl in port_code_of]

    # Estimasi durasi
    if selected_port_codes and angkutan_codes:
        n_iter = len(selected_port_codes) * len(angkutan_codes) * len(months_list)
        est_minutes = round(n_iter * 2.5 / 60, 1)  # ~2.5 detik per iterasi
        st.info(
            f"📌 **Estimasi:** {n_iter} iterasi stage 1 "
            f"(~{est_minutes} menit untuk stage 1). "
            f"Stage 2 (approval time) bergantung jumlah PKK ditemukan."
        )

    st.markdown('<div class="section-header">▶ Jalankan Scraping</div>', unsafe_allow_html=True)

    save_to_db = st.checkbox("💾 Simpan otomatis ke Supabase setelah scraping selesai", value=db_ok)

    btn_scrape = st.button(
        "🚀 Mulai Scraping",
        type="primary",
        disabled=(not selected_port_codes or not angkutan_codes),
    )

    if btn_scrape:
        if not selected_port_codes:
            st.toast("❌ Pilih minimal satu pelabuhan.", icon="⚠️")
            st.error("❌ Pilih minimal satu pelabuhan.")
        elif not angkutan_codes:
            st.toast("❌ Pilih minimal satu jenis angkutan.", icon="⚠️")
            st.error("❌ Pilih minimal satu jenis angkutan.")
        else:
            # ── Progress containers ──
            status_txt   = st.empty()
            progress_bar = st.progress(0)
            result_area  = st.empty()

            # ── List log error untuk popup ──
            scraping_errors = []

            # ── Callbacks ──
            def cb_progress1(cur, tot):
                progress_bar.progress(int(cur / tot * 50))  # Stage 1: 0–50%

            def cb_status1(msg):
                status_txt.info(f"**Stage 1 — Daftar PKK**\n\n{msg}")

            def cb_progress2(cur, tot):
                progress_bar.progress(50 + int(cur / tot * 50))  # Stage 2: 50–100%

            def cb_status2(msg):
                status_txt.info(f"**Stage 2 — Waktu Approval**\n\n{msg}")

            def cb_error(err_msg):
                scraping_errors.append(err_msg)
                # Tampilkan popup toast langsung per error
                st.toast(f"⚠️ {err_msg}")

            # ── Jalankan scraping ──
            with st.spinner("Scraping sedang berjalan..."):
                df_raw = run_full_scraping(
                    port_codes=selected_port_codes,
                    angkutan=angkutan_codes,
                    year=year_sel,
                    months=months_list,
                    port_ref_path="data/port_code.xlsx",
                    progress_stage1=cb_progress1,
                    status_stage1=cb_status1,
                    progress_stage2=cb_progress2,
                    status_stage2=cb_status2,
                    error_callback=cb_error,
                )

            progress_bar.empty()
            status_txt.empty()

            # Jika ada log error selama proses, tampilkan popup toast rangkuman
            if scraping_errors:
                st.toast(f"⚠️ Terdapat {len(scraping_errors)} peringatan/error selama proses scraping.", icon="🚨")
                with st.expander(f"⚠️ Detail Log Error Scraping ({len(scraping_errors)} item)"):
                    for err in scraping_errors:
                        st.markdown(f"- `{err}`")

            if df_raw.empty:
                st.warning("⚠️ Tidak ada data yang berhasil diambil. Periksa koneksi atau parameter.")
            else:
                # Preprocessing & Deduplikasi
                with st.spinner("Memproses & mendeteksi duplikasi data..."):
                    df_processed = preprocess(df_raw)
                    df_processed, n_dups = deduplicate_dataframe(df_processed)

                st.session_state["df"] = df_processed
                if n_dups > 0:
                    st.info(f"🧹 **{n_dups:,} record duplikat** terdeteksi dan dibersihkan dari hasil scraping.")
                st.success(f"✅ **{len(df_processed):,} record bersih** berhasil diambil dan diproses.")
                st.toast("✅ Scraping dan pemrosesan data berhasil!", icon="🎉")
                result_area.dataframe(df_processed.head(10), width="stretch")

                # Simpan ke Supabase
                if save_to_db and db_ok:
                    with st.spinner("Menyimpan ke Supabase..."):
                        res = insert_pkk_records(df_processed)
                    if res["success"]:
                        st.success(f"💾 **{res['inserted']:,} record** tersimpan ke Supabase.")
                        st.toast(f"💾 {res['inserted']:,} record tersimpan ke Supabase.", icon="✅")
                    else:
                        st.error(f"❌ Gagal menyimpan ke Supabase: {res['error']}")
                        st.toast(f"❌ Gagal simpan DB: {res['error']}", icon="❌")
                elif save_to_db and not db_ok:
                    st.warning("⚠️ Supabase tidak terhubung. Data hanya tersimpan di sesi ini.")

# ────────────────────────────────────────────────────────────────
# TAB 2 — UPLOAD FILE
# ────────────────────────────────────────────────────────────────
with tab_upload:
    st.markdown('<div class="section-header">📁 Upload Data dari File</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-box">Upload file CSV, Excel, Zip, atau Parquet hasil scraping sebelumnya. '
        'Batas ukuran file hingga <b>500 MB</b>.<br>'
        '💡 <b>Tips Kecepatan:</b> Kompres file CSV menjadi <code>.zip</code>, <code>.csv.gz</code>, atau format <code>.parquet</code> untuk mempercepat upload hingga <b>10x lebih cepat</b>!<br>'
        'Kolom minimal: <code>submission</code> dan <code>response</code>, atau <code>approval_minutes</code>.</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Pilih file CSV, Excel, Zip, atau Parquet",
        type=["csv", "xlsx", "xls", "gz", "zip", "parquet"],
        help="Format yang didukung: .csv, .xlsx, .xls, .gz, .zip, .parquet (Maksimal 500 MB)",
    )

    if uploaded_file is not None:
        file_size_mb = round(uploaded_file.size / (1024 * 1024), 2)
        st.caption(f"📦 Ukuran file: **{file_size_mb} MB**")

        try:
            parse_status = st.empty()
            parse_progress = st.progress(0)
            file_name_lower = uploaded_file.name.lower()

            parse_status.info(f"⏳ Membaca & mendekompresi data ({file_size_mb} MB)...")
            parse_progress.progress(20)

            # Optimasi Parsing berdasarkan format
            if file_name_lower.endswith(".zip"):
                # Ekstraksi file ZIP
                with zipfile.ZipFile(uploaded_file) as z:
                    file_list = [f for f in z.namelist() if not f.startswith("__MACOSX") and not f.endswith("/")]
                    csv_files = [f for f in file_list if f.lower().endswith(".csv")]
                    parquet_files = [f for f in file_list if f.lower().endswith(".parquet")]
                    excel_files = [f for f in file_list if f.lower().endswith(".xlsx") or f.lower().endswith(".xls")]

                    parse_progress.progress(50)
                    if csv_files:
                        with z.open(csv_files[0]) as f:
                            df_upload = pd.read_csv(f)
                    elif parquet_files:
                        with z.open(parquet_files[0]) as f:
                            df_upload = pd.read_parquet(f)
                    elif excel_files:
                        with z.open(excel_files[0]) as f:
                            df_upload = pd.read_excel(f)
                    else:
                        raise ValueError("Tidak ditemukan file CSV, Parquet, atau Excel di dalam arsip ZIP tersebut.")
                parse_progress.progress(100)
            elif file_name_lower.endswith(".parquet"):
                # Parquet (Format biner sangat cepat)
                df_upload = pd.read_parquet(uploaded_file)
                parse_progress.progress(100)
            elif file_name_lower.endswith(".csv") or file_name_lower.endswith(".gz"):
                # Gunakan PyArrow engine jika tersedia untuk kecepatan multi-threading maksimal
                try:
                    parse_progress.progress(40)
                    df_upload = pd.read_csv(uploaded_file, engine="pyarrow")
                    parse_progress.progress(100)
                except Exception:
                    # Fallback ke chunk reading jika pyarrow tidak mendukung buffer tertentu
                    chunks = []
                    chunk_size = 100_000
                    chunk_iter = pd.read_csv(uploaded_file, chunksize=chunk_size)
                    for i, chunk in enumerate(chunk_iter):
                        chunks.append(chunk)
                        pct = min(95, int((i + 1) * chunk_size * 100 / (file_size_mb * 50000 + 1)))
                        parse_progress.progress(pct)
                    df_upload = pd.concat(chunks, ignore_index=True)
                    parse_progress.progress(100)
            else:
                # Excel
                df_upload = pd.read_excel(uploaded_file)
                parse_progress.progress(100)

            parse_status.empty()
            parse_progress.empty()

            st.success(f"✅ File berhasil dibaca: **{len(df_upload):,} baris × {len(df_upload.columns)} kolom** ({file_size_mb} MB)")

            # Preview
            with st.expander("🔍 Preview Data (10 baris pertama)", expanded=True):
                st.dataframe(df_upload.head(10), width="stretch")

            # Validasi
            validation = validate_uploaded_file(df_upload)
            if not validation["valid"]:
                st.error(validation["message"])
            else:
                st.info(validation["message"])
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    save_upload_db = st.checkbox("💾 Simpan ke Supabase", value=db_ok, key="save_upload")
                with col_u2:
                    st.markdown("")

                if st.button("✅ Gunakan Data Ini", type="primary", key="btn_use_upload"):
                    # Step 1: Preprocessing & Deduplication Progress
                    proc_status = st.empty()
                    proc_progress = st.progress(0)

                    proc_status.info("🧹 Memproses data & mendeteksi duplikasi...")
                    proc_progress.progress(30)

                    if validation["is_raw"]:
                        df_final = preprocess(df_upload)
                    else:
                        df_final = df_upload.copy()

                    # Aliasing kolom penting jika belum ada
                    if "code" in df_final.columns and "port_code" not in df_final.columns:
                        df_final["port_code"] = df_final["code"]
                    
                    proc_progress.progress(70)
                    df_final, n_dups = deduplicate_dataframe(df_final)
                    proc_progress.progress(100)

                    proc_status.empty()
                    proc_progress.empty()

                    st.session_state["df"] = df_final
                    if n_dups > 0:
                        st.info(f"🧹 **{n_dups:,} record duplikat** dibersihkan dari file.")
                    st.success(f"✅ **{len(df_final):,} record bersih** siap dianalisis.")

                    # Step 2: Supabase Storage Progress (Batch size 2,500 untuk kecepatan transfer)
                    if save_upload_db and db_ok:
                        db_status = st.empty()
                        db_progress = st.progress(0)
                        
                        tot_recs = len(df_final)
                        def db_progress_cb(cur, tot):
                            pct = int(cur / tot * 100) if tot > 0 else 0
                            db_progress.progress(pct)
                            db_status.info(
                                f"💾 **Menyimpan ke Supabase:** {cur:,} / {tot:,} record ({pct}%) "
                                f"— Estimasi sisa waktu: ~{max(0, round((tot - cur) / 3000, 1))} detik"
                            )

                        res = insert_pkk_records(df_final, batch_size=2500, progress_callback=db_progress_cb)
                        
                        db_status.empty()
                        db_progress.empty()

                        if res["success"]:
                            st.success(f"💾 **{res['inserted']:,} record** berhasil tersimpan ke Supabase.")
                            st.toast(f"💾 {res['inserted']:,} record tersimpan ke Supabase.", icon="✅")
                        else:
                            st.error(f"❌ Gagal menyimpan ke Supabase: {res['error']}")

        except MemoryError:
            st.error(
                "❌ **Kehabisan Memori (MemoryError):** File terlalu besar untuk dibaca sekaligus ke RAM. "
                "Disarankan untuk membagi file menjadi beberapa bagian lebih kecil atau menggunakan format `.csv`."
            )
        except Exception as e:
            st.error(f"❌ **Gagal membaca file:** {e}")

# ────────────────────────────────────────────────────────────────
# TAB 3 — LOAD DARI SUPABASE
# ────────────────────────────────────────────────────────────────
with tab_supabase:
    st.markdown('<div class="section-header">🗄️ Muat Data dari Supabase</div>', unsafe_allow_html=True)

    if not is_connected():
        st.error("❌ Supabase tidak terhubung. Isi kredensial di `.streamlit/secrets.toml`.")
        st.code(
            'SUPABASE_URL = "https://xxxx.supabase.co"\nSUPABASE_KEY = "your-anon-key"',
            language="toml"
        )
    else:
        st.success("✅ Koneksi Supabase aktif.")

        col_db1, col_db2, col_db3 = st.columns(3)

        with col_db1:
            year_db = st.selectbox("📅 Tahun", [2025, 2024], key="year_db")

        with col_db2:
            angkutan_db = st.multiselect(
                "🚢 Jenis Angkutan",
                ["dn — Domestik", "ln — Luar Negeri"],
                default=["dn — Domestik", "ln — Luar Negeri"],
                key="angkutan_db",
            )
            angkutan_db_codes = [x.split(" — ")[0] for x in angkutan_db]

        with col_db3:
            filter_port_db = st.multiselect(
                "🏗️ Filter Pelabuhan (opsional)",
                options=port_labels,
                placeholder="Kosongkan = semua pelabuhan",
                key="port_db",
            )
            filter_codes_db = [port_code_of[lbl] for lbl in filter_port_db if lbl in port_code_of]

        if st.button("📥 Muat dari Supabase", type="primary", width="stretch"):
            with st.spinner("Mengambil data dari Supabase (mungkin memerlukan beberapa saat)..."):
                df_db = fetch_pkk_records(
                    port_codes=filter_codes_db if filter_codes_db else None,
                    year=year_db,
                    angkutan=angkutan_db_codes if len(angkutan_db_codes) < 2 else None,
                )

            if df_db.empty:
                st.warning("⚠️ Tidak ada data ditemukan dengan filter tersebut.")
            else:
                st.session_state["df"] = df_db
                st.success(f"✅ **{len(df_db):,} record** berhasil dimuat dari Supabase.")
                with st.expander("🔍 Preview Data"):
                    st.dataframe(df_db.head(20), width="stretch")

# ────────────────────────────────────────────────────────────────
# TAB 4 — EKSPOR DATA
# ────────────────────────────────────────────────────────────────
with tab_export:
    st.markdown('<div class="section-header">💾 Ekspor Data</div>', unsafe_allow_html=True)

    df_current = st.session_state.get("df", pd.DataFrame())

    if df_current.empty:
        st.warning("⚠️ Belum ada data di sesi. Silakan ambil atau muat data terlebih dahulu.")
    else:
        st.success(f"✅ Data siap diekspor: **{len(df_current):,} record**")

        col_ex1, col_ex2 = st.columns(2)

        # Export CSV
        with col_ex1:
            st.markdown("#### 📄 Export CSV")
            csv_buf = df_current.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_buf,
                file_name="inaportnet_pkk_2025.csv",
                mime="text/csv",
                width="stretch",
            )

        # Export Excel
        with col_ex2:
            st.markdown("#### 📊 Export Excel")
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                df_current.to_excel(writer, sheet_name="Data PKK", index=False)

                # Sheet ringkasan per pelabuhan
                if "port_code" in df_current.columns and "approval_minutes" in df_current.columns:
                    from modules.analysis import compute_port_summary
                    summary = compute_port_summary(df_current)
                    if not summary.empty:
                        summary.to_excel(writer, sheet_name="Ringkasan Pelabuhan", index=False)

            excel_buf.seek(0)
            st.download_button(
                label="⬇️ Download Excel",
                data=excel_buf,
                file_name="inaportnet_pkk_2025.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )

        # Preview kolom
        st.markdown("#### 🔍 Preview Data")
        st.dataframe(df_current.head(20), width="stretch")

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Total Record", f"{len(df_current):,}")
        with col_stat2:
            st.metric("Jumlah Kolom", len(df_current.columns))
        with col_stat3:
            if "port_code" in df_current.columns:
                st.metric("Pelabuhan Unik", df_current["port_code"].nunique())
