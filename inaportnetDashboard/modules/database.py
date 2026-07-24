"""
modules/database.py
Koneksi dan operasi CRUD ke Supabase untuk data PKK Inaportnet.
"""

import pandas as pd
import streamlit as st
from typing import Optional, List

# ──────────────────────────────────────────────────────────────
# Client Supabase (singleton via cache_resource)
# ──────────────────────────────────────────────────────────────

@st.cache_resource
def get_supabase_client():
    """Mengembalikan Supabase client. Menggunakan st.secrets untuk kredensial."""
    try:
        from supabase import create_client
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
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


# ──────────────────────────────────────────────────────────────
# INSERT / UPSERT
# ──────────────────────────────────────────────────────────────

def insert_pkk_records(df: pd.DataFrame, batch_size: int = 500) -> dict:
    """
    Menyimpan DataFrame PKK ke Supabase dengan upsert (hindari duplikat).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame preprocessed dengan kolom yang sesuai skema.
    batch_size : int
        Jumlah record per batch insert.

    Returns
    -------
    dict : {'success': bool, 'inserted': int, 'error': str}
    """
    client = get_supabase_client()
    if client is None:
        return {"success": False, "inserted": 0, "error": "Supabase tidak terkonfigurasi."}

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
            df_out[col] = df_out[col].astype(float).round(4)
    for col in ["year", "month", "hour"]:
        if col in df_out.columns:
            df_out[col] = df_out[col].astype("Int64").astype(object)

    # Pilih kolom yang tersedia di skema
    schema_cols = ["pkk_number","vessel_name","port_code","port","service",
                   "submission","response","simpadu","gmt","approval_hours",
                   "approval_minutes","year","quarter","month","date","day","hour","angkutan"]
    df_out = df_out[[c for c in schema_cols if c in df_out.columns]]

    records = df_out.where(pd.notnull(df_out), None).to_dict(orient="records")
    total_inserted = 0

    try:
        for i in range(0, len(records), batch_size):
            chunk = records[i : i + batch_size]
            client.table("pkk_records").upsert(chunk, on_conflict="pkk_number").execute()
            total_inserted += len(chunk)
        return {"success": True, "inserted": total_inserted, "error": None}
    except Exception as e:
        return {"success": False, "inserted": total_inserted, "error": str(e)}


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

    Parameters
    ----------
    port_codes : list of str, optional
        Filter berdasarkan kode pelabuhan.
    year : int, optional
        Filter berdasarkan tahun.
    angkutan : list of str, optional
        Filter ['dn'], ['ln'], atau ['dn','ln'].
    page_size : int
        Jumlah record per halaman (pagination).

    Returns
    -------
    pd.DataFrame
    """
    client = get_supabase_client()
    if client is None:
        return pd.DataFrame()

    all_records = []
    offset = 0

    try:
        while True:
            q = client.table("pkk_records").select("*")

            # Terapkan filter
            if port_codes:
                q = q.in_("port_code", port_codes)
            if year:
                q = q.eq("year", year)
            if angkutan and len(angkutan) == 1:
                q = q.eq("angkutan", angkutan[0])
            # Jika angkutan keduanya, tidak perlu filter

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


def get_available_ports_from_db() -> List[str]:
    """Ambil daftar port_code yang tersedia di database."""
    client = get_supabase_client()
    if client is None:
        return []
    try:
        response = (
            client.table("pkk_records")
            .select("port_code")
            .execute()
        )
        codes = list({r["port_code"] for r in response.data if r.get("port_code")})
        return sorted(codes)
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


def check_and_clean_db_duplicates(progress_callback=None) -> dict:
    """
    Mendeteksi dan menghapus record duplikat di Supabase (pkk_records) berdasarkan pkk_number.
    
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
            progress_callback("detect", "🔍 Mendeteksi data yang tersimpan di Supabase...", 20)

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
    Mengembalikan statistik metrik ringkas dari tabel pkk_records di Supabase.
    """
    client = get_supabase_client()
    if client is None:
        return {"connected": False, "total_records": 0, "unique_ports": 0, "error": "Supabase tidak terkonfigurasi"}

    try:
        # Request total count
        res_count = client.table("pkk_records").select("id", count="exact").limit(1).execute()
        total_records = res_count.count if res_count.count is not None else 0

        # Unique ports
        codes = get_available_ports_from_db()

        return {
            "connected": True,
            "total_records": total_records,
            "unique_ports": len(codes),
            "available_port_codes": codes,
            "error": None
        }
    except Exception as e:
        return {"connected": False, "total_records": 0, "unique_ports": 0, "error": str(e)}


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

