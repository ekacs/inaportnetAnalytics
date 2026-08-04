"""
modules/database.py
Koneksi dan operasi CRUD ke Supabase untuk data PKK Inaportnet.
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional, List

# ──────────────────────────────────────────────────────────────
# Client Supabase (singleton via cache_resource)
# ──────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _create_supabase_client_cached(url: str, key: str):
    from supabase import create_client
    return create_client(url, key)


def get_supabase_client():
    """Mengembalikan Supabase client. Menggunakan st.secrets untuk kredensial."""
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if not url or not key:
            return None
        return _create_supabase_client_cached(url, key)
    except Exception:
        return None


def is_connected() -> bool:
    """Cek apakah koneksi Supabase tersedia."""
    client = get_supabase_client()
    if client is None:
        return False
    try:
        client.table("pkk_records").select("id").limit(1).execute()
        return True
    except Exception:
        return False


MAX_SUPABASE_RECORDS = 1_500_000

def get_supabase_quota_limit() -> int:
    """Mengembalikan batas maksimal kuota penyimpanan Supabase (default 1,500,000)."""
    try:
        if "MAX_SUPABASE_RECORDS" in st.secrets:
            return int(st.secrets["MAX_SUPABASE_RECORDS"])
    except Exception:
        pass
    return MAX_SUPABASE_RECORDS


def render_quota_full_dialog():
    """
    Menampilkan popup dialog / notifikasi jika kuota penyimpanan Supabase sudah penuh.
    """
    narrative = (
        "👋 **Halo!**\n\n"
        "🌐 **Informasi dari Sistem:**\n"
        "Kuota penyimpanan data Supabase Anda saat ini **sudah penuh**.\n\n"
        "Harap menghubungi **Mas Eka** jika Anda ingin melanjutkan pengisian atau meningkatkan kapasitas data.\n\n"
        "Terima kasih banyak atas kerjasamanya! 🙏😊"
    )
    if hasattr(st, "dialog"):
        @st.dialog("⚠️ Kuota Penyimpanan Supabase Penuh")
        def _show_dialog():
            st.warning("⚠️ **Penyimpanan Penuh**")
            st.markdown(narrative)
            if st.button("OK, Mengerti", type="primary", width="stretch"):
                st.rerun()
        _show_dialog()
    else:
        st.error("⚠️ **Kuota Penyimpanan Supabase Penuh**")
        st.info(narrative)


# ──────────────────────────────────────────────────────────────
# INSERT / UPSERT
# ──────────────────────────────────────────────────────────────

def insert_pkk_records(df: pd.DataFrame, batch_size: int = 500, progress_callback=None) -> dict:
    """
    Menyimpan DataFrame PKK ke Supabase dengan upsert (hindari duplikat).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame preprocessed dengan kolom yang sesuai skema.
    batch_size : int
        Jumlah record per batch insert.
    progress_callback : callable, optional
        Callback function(current, total) untuk memperbarui progress UI.

    Returns
    -------
    dict : {'success': bool, 'inserted': int, 'error': str}
    """
    client = get_supabase_client()
    if client is None:
        return {"success": False, "inserted": 0, "error": "Supabase tidak terkonfigurasi."}

    # Cek kuota penyimpanan Supabase
    db_stats = get_database_stats()
    if db_stats.get("is_full", False):
        return {
            "success": False,
            "inserted": 0,
            "is_quota_full": True,
            "error": "Kuota data Supabase sudah penuh. Harap menghubungi Mas Eka untuk melanjutkan."
        }

    # Siapkan data: rename kolom agar sesuai skema Supabase
    col_map = {
        "PKK_number":       "pkk_number",
        "vessel_name":      "vessel_name",
        "port_code":        "port_code",
        "port":             "port",
        "service":          "service",
        "submission":       "submission",
        "response":         "response",
        "simpadu":          "simpadu",
        "GMT":              "gmt",
        "approval_hours":   "approval_hours",
        "approval_minutes": "approval_minutes",
        "year":             "year",
        "quarter":          "quarter",
        "month":            "month",
        "date":             "date",
        "day":              "day",
        "hour":             "hour",
        "angkutan":         "angkutan",
    }
    df_out = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Konversi tipe data ke Python native (JSON-serializable)
    for col in ["submission", "response"]:
        if col in df_out.columns:
            df_out[col] = pd.to_datetime(df_out[col], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S")
    if "date" in df_out.columns:
        df_out["date"] = df_out["date"].astype(str)
    if "quarter" in df_out.columns:
        df_out["quarter"] = df_out["quarter"].astype(str)
    for col in ["approval_hours", "approval_minutes"]:
        if col in df_out.columns:
            df_out[col] = pd.to_numeric(df_out[col], errors="coerce").round(4)
    for col in ["year", "month", "hour"]:
        if col in df_out.columns:
            df_out[col] = pd.to_numeric(df_out[col], errors="coerce")

    # Pilih kolom yang tersedia di skema
    schema_cols = ["pkk_number","vessel_name","port_code","port","service",
                   "submission","response","simpadu","gmt","approval_hours",
                   "approval_minutes","year","quarter","month","date","day","hour","angkutan"]
    df_out = df_out[[c for c in schema_cols if c in df_out.columns]]

    # Ganti Inf / -Inf dengan NaN, lalu konversi SELURUH kolom ke object dtype
    # agar nilai None tidak ter-cast kembali menjadi float np.nan oleh pandas
    df_out = df_out.replace([np.inf, -np.inf], np.nan)
    df_out = df_out.astype(object)
    df_out = df_out.where(pd.notnull(df_out), None)

    total_records = len(df_out)
    total_inserted = 0

    try:
        if progress_callback:
            progress_callback(0, total_records)
        for i in range(0, total_records, batch_size):
            chunk_df = df_out.iloc[i : i + batch_size]
            chunk = chunk_df.to_dict(orient="records")
            client.table("pkk_records").upsert(chunk, on_conflict="pkk_number").execute()
            total_inserted += len(chunk)
            if progress_callback:
                progress_callback(total_inserted, total_records)
        return {"success": True, "inserted": total_inserted, "error": None}
    except Exception as e:
        return {"success": False, "inserted": total_inserted, "error": str(e)}



# ──────────────────────────────────────────────────────────────
# FETCH
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# FETCH
# ──────────────────────────────────────────────────────────────

def fetch_pkk_records(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    page_size: int = 1000,
) -> pd.DataFrame:
    """
    Mengambil data PKK dari Supabase dengan filter opsional.
    """
    client = get_supabase_client()
    if client is None:
        return pd.DataFrame()

    page_size = 1000  # Batas maksimal per request PostgREST API

    all_records = []
    offset = 0

    try:
        while True:
            q = client.table("pkk_records").select("*")

            if port_codes:
                q = q.in_("port_code", port_codes)
            if year:
                q = q.eq("year", year)
            if angkutan and len(angkutan) == 1:
                q = q.eq("angkutan", angkutan[0])

            response = q.range(offset, offset + page_size - 1).execute()
            if not response.data:
                break
            all_records.extend(response.data)
            if len(response.data) < page_size:
                break
            offset += page_size

        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame(all_records)

        # Konversi tipe data
        for col in ["submission", "response"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        for col in ["approval_hours", "approval_minutes"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ["year", "month", "hour"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        # Rename kolom Supabase ke naming convention app
        df = df.rename(columns={"pkk_number": "PKK_number", "gmt": "GMT"})
        return df

    except Exception as e:
        st.error(f"Error mengambil data dari Supabase: {e}")
        return pd.DataFrame()


def fetch_pkk_records_with_progress(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    page_size: int = 1000,
    label: str = "📥 Mengambil data dari Supabase..."
) -> pd.DataFrame:
    """
    Mengambil seluruh data dari Supabase dengan multithreading (10 parallel workers),
    progress bar interaktif, kecepatan unduh (record/dtk), dan estimasi waktu tersisa (ETA).
    """
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    client = get_supabase_client()
    if client is None:
        st.error("❌ Supabase tidak terkonfigurasi.")
        return pd.DataFrame()

    page_size = 1000  # Batas maksimal per request PostgREST API

    # Hitung total record terfilter terlebih dahulu
    total_count = 0
    try:
        count_q = client.table("pkk_records").select("*", count="exact")
        if port_codes:
            count_q = count_q.in_("port_code", port_codes)
        if year:
            count_q = count_q.eq("year", year)
        if angkutan and len(angkutan) == 1:
            count_q = count_q.eq("angkutan", angkutan[0])
        count_res = count_q.limit(1).execute()
        total_count = count_res.count if count_res.count is not None else 0
    except Exception:
        total_count = 0

    progress_bar = st.progress(0.0)
    status_box = st.empty()

    start_time = time.time()
    all_records = []

    def fetch_page(offset_val):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                q = client.table("pkk_records").select("*")
                if port_codes:
                    q = q.in_("port_code", port_codes)
                if year:
                    q = q.eq("year", year)
                if angkutan and len(angkutan) == 1:
                    q = q.eq("angkutan", angkutan[0])
                res = q.range(offset_val, offset_val + page_size - 1).execute()
                return offset_val, res.data if res.data else []
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(0.3 * (attempt + 1))

    try:
        if total_count > 0:
            offsets = list(range(0, total_count, page_size))
            total_pages = len(offsets)
            page_results = {}
            completed_pages = 0

            # Batching per 50 halaman dengan max 5 parallel worker untuk mencegah socket limit OS / Supabase
            batch_chunk_size = 50
            with ThreadPoolExecutor(max_workers=5) as executor:
                for i in range(0, len(offsets), batch_chunk_size):
                    chunk_offsets = offsets[i:i + batch_chunk_size]
                    future_to_offset = {executor.submit(fetch_page, off): off for off in chunk_offsets}
                    for future in as_completed(future_to_offset):
                        off, data = future.result()
                        page_results[off] = data
                        completed_pages += 1

                        current_count = sum(len(v) for v in page_results.values())
                        elapsed = time.time() - start_time
                        speed = current_count / elapsed if elapsed > 0 else 0
                        pct = min(1.0, completed_pages / total_pages)
                        remaining = max(0, total_count - current_count)
                        eta = remaining / speed if speed > 0 else 0

                        if eta >= 60:
                            eta_str = f"{int(eta // 60)} mnt {int(eta % 60)} dtk"
                        else:
                            eta_str = f"{int(eta)} dtk"

                        progress_bar.progress(pct)
                        status_box.markdown(
                            f"**{label}**\n\n"
                            f"📊 **Progress**: `{current_count:,}` dari `{total_count:,}` record (**{pct*100:.1f}%**)\n\n"
                            f"⚡ **Kecepatan**: `{int(speed):,}` record/detik | ⏳ **Perkiraan Waktu Tersisa (ETA)**: `{eta_str}`"
                        )

            for off in sorted(page_results.keys()):
                all_records.extend(page_results[off])
        else:
            offset = 0
            while True:
                q = client.table("pkk_records").select("*")
                if port_codes:
                    q = q.in_("port_code", port_codes)
                if year:
                    q = q.eq("year", year)
                if angkutan and len(angkutan) == 1:
                    q = q.eq("angkutan", angkutan[0])

                response = q.range(offset, offset + page_size - 1).execute()
                if not response.data:
                    break

                all_records.extend(response.data)
                current_count = len(all_records)
                offset += page_size

                elapsed = time.time() - start_time
                speed = current_count / elapsed if elapsed > 0 else 0

                status_box.markdown(
                    f"**{label}**\n\n"
                    f"📊 **Progress**: `{current_count:,}` record terunduh...\n\n"
                    f"⚡ **Kecepatan**: `{int(speed):,}` record/detik"
                )

                if len(response.data) < page_size:
                    break

        progress_bar.progress(1.0)
        total_time = time.time() - start_time
        status_box.success(f"✅ Berhasil memuat SELURUH `{len(all_records):,}` record dari Supabase dalam `{total_time:.1f}` detik.")

        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame(all_records)

        # Konversi tipe data
        for col in ["submission", "response"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        for col in ["approval_hours", "approval_minutes"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ["year", "month", "hour"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        df = df.rename(columns={"pkk_number": "PKK_number", "gmt": "GMT"})
        return df

    except Exception as e:
        status_box.error(f"❌ Error mengambil data dari Supabase: {e}")
        return pd.DataFrame()


def get_available_ports_from_db() -> List[str]:
    """Ambil daftar port_code yang tersedia di database."""
    client = get_supabase_client()
    if client is None:
        return []
    try:
        # 1. Coba query via view ringkasan pelabuhan (jika ada di Supabase)
        try:
            res_view = client.table("port_summary_view").select("port_code").execute()
            if res_view.data:
                codes = list({r["port_code"] for r in res_view.data if r.get("port_code")})
                if codes:
                    return sorted(codes)
        except Exception:
            pass

        # 2. Jika data sudah dimuat ke session state
        if "df" in st.session_state and not st.session_state["df"].empty and "port_code" in st.session_state["df"].columns:
            codes = list(st.session_state["df"]["port_code"].dropna().unique())
            if codes:
                return sorted(codes)

        # 3. Pagination query untuk scan port_code dari database Supabase
        all_codes = set()
        for offset in range(0, 100000, 2500):
            response = (
                client.table("pkk_records")
                .select("port_code")
                .range(offset, offset + 2499)
                .execute()
            )
            if not response.data:
                break
            batch_codes = {r["port_code"] for r in response.data if r.get("port_code")}
            all_codes.update(batch_codes)
            if len(response.data) < 2500:
                break
        return sorted(list(all_codes))

    except Exception:
        return []


def delete_pkk_records(port_codes: List[str], year: int) -> dict:
    """Hapus data berdasarkan port_code dan year (untuk re-scraping)."""
    client = get_supabase_client()
    if client is None:
        return {"success": False, "error": "Supabase tidak terkonfigurasi."}
    try:
        client.table("pkk_records").delete().in_("port_code", port_codes).eq("year", year).execute()
        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def deduplicate_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Menghapus duplikasi record dari DataFrame berdasarkan pkk_number (atau PKK_number).
    
    Returns
    -------
    (df_clean, duplicate_count)
    """
    if df.empty:
        return df, 0
    
    col_pkk = "PKK_number" if "PKK_number" in df.columns else ("pkk_number" if "pkk_number" in df.columns else None)
    if not col_pkk:
        return df, 0
    
    initial_len = len(df)
    df_clean = df.drop_duplicates(subset=[col_pkk], keep="last").reset_index(drop=True)
    dup_count = initial_len - len(df_clean)
    return df_clean, dup_count


def clean_and_deduplicate_pkk_rpc() -> dict:
    """
    Memanggil Supabase Stored Procedure (clean_and_deduplicate_pkk) di server-side.
    Menghapus baris kosong (null pkk_number) & duplikat secara instan di SQL level.
    """
    client = get_supabase_client()
    if client is None:
        return {"success": False, "deleted_nulls": 0, "deleted_duplicates": 0, "error": "Supabase tidak terkonfigurasi."}

    try:
        response = client.rpc("clean_and_deduplicate_pkk").execute()
        res_data = response.data if hasattr(response, "data") else response
        if isinstance(res_data, dict):
            return {
                "success": True,
                "deleted_nulls": res_data.get("deleted_nulls", 0),
                "deleted_duplicates": res_data.get("deleted_duplicates", 0),
                "error": None
            }
        return {"success": True, "deleted_nulls": 0, "deleted_duplicates": 0, "error": None}
    except Exception as e:
        return {"success": False, "deleted_nulls": 0, "deleted_duplicates": 0, "error": str(e)}


def check_and_clean_db_duplicates(progress_callback=None) -> dict:
    """
    Mendeteksi dan menghapus record duplikat di Supabase (pkk_records) berdasarkan pkk_number.
    Mencoba RPC server-side lebih dahulu. Jika belum ada, gunakan fallback client-side.
    
    Parameters
    ----------
    progress_callback : callable, optional
        Fungsi callback (step_code, message, pct) untuk update UI modal.
        
    Returns
    -------
    dict : {'total_checked': int, 'duplicates_found': int, 'duplicates_removed': int, 'clean_count': int, 'success': bool, 'error': str}
    """
    client = get_supabase_client()
    if client is None:
        return {
            "total_checked": 0, "duplicates_found": 0, "duplicates_removed": 0,
            "clean_count": 0, "success": False, "error": "Supabase tidak terkonfigurasi."
        }

    try:
        if progress_callback:
            progress_callback("detect", "⚡ Memulai pembersihan cepat server-side (Supabase RPC)...", 30)

        # Coba jalankan via RPC Server-Side terlebih dahulu
        rpc_res = clean_and_deduplicate_pkk_rpc()
        if rpc_res["success"]:
            # Ambil total record tersisa
            count_resp = client.table("pkk_records").select("id", count="exact").limit(1).execute()
            clean_count = count_resp.count if hasattr(count_resp, "count") and count_resp.count is not None else 0
            dups_removed = rpc_res["deleted_duplicates"] + rpc_res["deleted_nulls"]
            total_checked = clean_count + dups_removed

            if progress_callback:
                progress_callback("complete", f"✅ Data bersih via Supabase RPC! Dihapus: {dups_removed:,} (Duplikat: {rpc_res['deleted_duplicates']:,}, Null: {rpc_res['deleted_nulls']:,}). Total bersih: {clean_count:,} record.", 100)

            return {
                "total_checked": total_checked,
                "duplicates_found": dups_removed,
                "duplicates_removed": dups_removed,
                "clean_count": clean_count,
                "success": True,
                "error": None
            }

        if progress_callback:
            progress_callback("detect", "🔍 Mendeteksi data yang tersimpan di Supabase (Fallback Client-Side)...", 20)

        # Ambil id dan pkk_number seluruh data dari Supabase
        all_rows = []
        offset = 0
        page_size = 5000
        while True:
            resp = client.table("pkk_records").select("id, pkk_number, scraped_at").range(offset, offset + page_size - 1).execute()
            if not resp.data:
                break
            all_rows.extend(resp.data)
            if len(resp.data) < page_size:
                break
            offset += page_size

        total_checked = len(all_rows)
        if total_checked == 0:
            return {
                "total_checked": 0, "duplicates_found": 0, "duplicates_removed": 0,
                "clean_count": 0, "success": True, "error": None
            }

        if progress_callback:
            progress_callback("count", f"🔢 Menghitung duplikasi data dari {total_checked:,} record...", 50)

        # Cari pkk_number ganda
        seen = {}
        duplicate_ids = []
        for r in all_rows:
            pkk = r.get("pkk_number")
            rec_id = r.get("id")
            if not pkk or not rec_id:
                continue
            if pkk in seen:
                # Duplikat ditemukan! Simpan ID lama untuk dihapus
                duplicate_ids.append(seen[pkk])
                seen[pkk] = rec_id  # simpan yang terbaru
            else:
                seen[pkk] = rec_id

        duplicates_found = len(duplicate_ids)

        if duplicates_found > 0:
            if progress_callback:
                progress_callback("clean", f"🧹 Menghapus {duplicates_found:,} record duplikat dari Supabase...", 75)

            # Hapus ID duplikat secara batch
            batch_size = 200
            duplicates_removed = 0
            for i in range(0, len(duplicate_ids), batch_size):
                chunk = duplicate_ids[i:i + batch_size]
                client.table("pkk_records").delete().in_("id", chunk).execute()
                duplicates_removed += len(chunk)
        else:
            duplicates_removed = 0

        clean_count = total_checked - duplicates_removed

        if progress_callback:
            progress_callback("complete", f"✅ Data bersih dari duplikasi! Total: {clean_count:,} record.", 100)

        return {
            "total_checked": total_checked,
            "duplicates_found": duplicates_found,
            "duplicates_removed": duplicates_removed,
            "clean_count": clean_count,
            "success": True,
            "error": None
        }

    except Exception as e:
        return {
            "total_checked": 0, "duplicates_found": 0, "duplicates_removed": 0,
            "clean_count": 0, "success": False, "error": str(e)
        }



# ──────────────────────────────────────────────────────────────
# DATABASE EXPLORER & STATS
# ──────────────────────────────────────────────────────────────

def get_database_stats() -> dict:
    """
    Mengembalikan statistik metrik ringkas dan kuota penyimpanan dari tabel pkk_records di Supabase.
    """
    client = get_supabase_client()
    max_quota = get_supabase_quota_limit()
    if client is None:
        return {
            "connected": False,
            "total_records": 0,
            "max_quota": max_quota,
            "quota_pct": 0.0,
            "is_full": False,
            "unique_ports": 0,
            "error": "Supabase tidak terkonfigurasi"
        }

    try:
        # Request total count
        res_count = client.table("pkk_records").select("id", count="exact").limit(1).execute()
        total_records = res_count.count if res_count.count is not None else 0

        # Unique ports
        codes = get_available_ports_from_db()

        quota_pct = round(total_records / max_quota * 100, 1) if max_quota > 0 else 0.0
        is_full = total_records >= max_quota

        return {
            "connected": True,
            "total_records": total_records,
            "max_quota": max_quota,
            "quota_pct": min(100.0, quota_pct),
            "is_full": is_full,
            "unique_ports": len(codes),
            "available_port_codes": codes,
            "error": None
        }
    except Exception as e:
        return {
            "connected": False,
            "total_records": 0,
            "max_quota": max_quota,
            "quota_pct": 0.0,
            "is_full": False,
            "unique_ports": 0,
            "error": str(e)
        }


def fetch_pkk_records_paginated(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[pd.DataFrame, int]:
    """
    Mengambil data PKK dari Supabase dengan filter, pencarian kata kunci, dan pagination.

    Returns
    -------
    (pd.DataFrame, total_count)
    """
    client = get_supabase_client()
    if client is None:
        return pd.DataFrame(), 0

    try:
        q = client.table("pkk_records").select("*", count="exact")

        if port_codes:
            q = q.in_("port_code", port_codes)
        if year:
            q = q.eq("year", year)
        if angkutan and len(angkutan) == 1:
            q = q.eq("angkutan", angkutan[0])
        if search_query and search_query.strip():
            sq = search_query.strip()
            q = q.or_(f"pkk_number.ilike.%{sq}%,vessel_name.ilike.%{sq}%")

        q = q.order("submission", desc=True)

        if limit > 0:
            q = q.range(offset, offset + limit - 1)

        response = q.execute()
        total_count = response.count if response.count is not None else 0

        DEFAULT_COLS = [
            "PKK_number", "vessel_name", "port_code", "port", "service",
            "submission", "response", "simpadu", "GMT", "approval_hours",
            "approval_minutes", "year", "quarter", "month", "date", "day",
            "hour", "angkutan"
        ]

        if not response.data:
            return pd.DataFrame(columns=DEFAULT_COLS), total_count

        df = pd.DataFrame(response.data)

        # Datetime conversions
        for col in ["submission", "response"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        for col in ["approval_hours", "approval_minutes"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ["year", "month", "hour"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        df = df.rename(columns={"pkk_number": "PKK_number", "gmt": "GMT"})
        return df, total_count

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame(), 0


def generate_sql_dump(df: pd.DataFrame, table_name: str = "pkk_records") -> str:
    """
    Menghasilkan script SQL INSERT statement dari DataFrame PKK untuk kebutuhan dump/backup.
    """
    if df.empty:
        return "-- Database kosong\n"

    lines = [
        f"-- SQL Dump for table `{table_name}`",
        f"-- Total Records: {len(df)}",
        f"-- Generated by Inaportnet Analytics Dashboard",
        "----------------------------------------------------\n"
    ]

    col_map = {
        "PKK_number": "pkk_number", "vessel_name": "vessel_name",
        "port_code": "port_code", "port": "port", "service": "service",
        "submission": "submission", "response": "response", "simpadu": "simpadu",
        "GMT": "gmt", "approval_hours": "approval_hours",
        "approval_minutes": "approval_minutes", "year": "year",
        "quarter": "quarter", "month": "month", "date": "date",
        "day": "day", "hour": "hour", "angkutan": "angkutan"
    }

    df_sql = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    for _, row in df_sql.iterrows():
        cols = []
        vals = []
        for col, val in row.items():
            if pd.isna(val) or val is None:
                continue
            cols.append(col)
            if isinstance(val, (int, float)):
                vals.append(str(val))
            else:
                clean_val = str(val).replace("'", "''")
                vals.append(f"'{clean_val}'")

        if cols and vals:
            stmt = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({', '.join(vals)}) ON CONFLICT (pkk_number) DO NOTHING;"
            lines.append(stmt)

    return "\n".join(lines)


def render_sidebar_sync_widget():
    """
    Menampilkan widget sinkronisasi data Supabase di sidebar (dapat dipanggil dari halaman manapun).
    """
    if is_connected():
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔄 Sinkronisasi Supabase")
        if "df" in st.session_state and not st.session_state["df"].empty:
            st.sidebar.caption(f"Sesi Aktif: **{len(st.session_state['df']):,} record**")
        else:
            st.sidebar.caption("Sesi Aktif: Belum ada data")

        if st.sidebar.button("🔄 Auto-Load / Sinkronkan Data", type="primary", use_container_width=True, key="btn_sidebar_sync_global"):
            df_loaded = fetch_pkk_records_with_progress(page_size=5000, label="🔄 Memuat data Supabase ke sesi...")
            if not df_loaded.empty:
                st.session_state["df"] = df_loaded
                st.sidebar.success(f"✅ Dimuat: {len(df_loaded):,} record!")
                st.rerun()
            else:
                st.sidebar.error("❌ Supabase masih kosong.")

