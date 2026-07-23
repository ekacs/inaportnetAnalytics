"""
modules/database.py
Koneksi dan operasi CRUD ke Supabase untuk data PKK Inaportnet.
"""

import pandas as pd
import streamlit as st
from typing import Optional, List
import math

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
