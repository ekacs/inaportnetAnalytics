"""
modules/database.py
Koneksi dan operasi CRUD ke Supabase atau SQLite lokal untuk data PKK Inaportnet.
Apabila Supabase tidak terhubung, data tersimpan dan diproses secara lokal menggunakan SQLite.
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
from typing import Optional, List

# ──────────────────────────────────────────────────────────────
# Konfigurasi & Inisialisasi SQLite Lokal
# ──────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SQLITE_DB_PATH = os.path.join(DATA_DIR, "inaportnet_local.db")


def init_sqlite_db():
    """Memastikan folder data dan tabel pkk_records di SQLite lokal sudah dibuat."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pkk_records (
        pkk_number TEXT PRIMARY KEY,
        vessel_name TEXT,
        port_code TEXT,
        port TEXT,
        service TEXT,
        submission TEXT,
        response TEXT,
        simpadu TEXT,
        gmt TEXT,
        approval_hours REAL,
        approval_minutes REAL,
        year INTEGER,
        quarter TEXT,
        month INTEGER,
        date TEXT,
        day TEXT,
        hour INTEGER,
        angkutan TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_port_code ON pkk_records(port_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_year ON pkk_records(year);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_submission ON pkk_records(submission);")
    conn.commit()
    conn.close()


def get_sqlite_conn():
    """Mengembalikan koneksi sqlite3."""
    init_sqlite_db()
    return sqlite3.connect(SQLITE_DB_PATH)


# ──────────────────────────────────────────────────────────────
# Client Supabase & Cek Koneksi
# ──────────────────────────────────────────────────────────────

@st.cache_resource
def get_supabase_client():
    """Mengembalikan Supabase client. Menggunakan st.secrets untuk kredensial."""
    try:
        from supabase import create_client
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None


def is_supabase_connected() -> bool:
    """Cek apakah koneksi Supabase Cloud tersedia dan dapat diakses."""
    client = get_supabase_client()
    if client is None:
        return False
    try:
        client.table("pkk_records").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def is_connected() -> bool:
    """Cek apakah database (Supabase Cloud atau SQLite Lokal) siap digunakan."""
    return True


def get_db_mode() -> str:
    """Mengembalikan mode database yang aktif: 'supabase' atau 'sqlite'."""
    return "supabase" if is_supabase_connected() else "sqlite"


def get_db_status_info() -> dict:
    """
    Mengembalikan informasi status koneksi database untuk tampilan UI.
    """
    if is_supabase_connected():
        return {
            "mode": "supabase",
            "label": "✅ Supabase Terhubung",
            "short_label": "Supabase Cloud",
            "is_cloud": True,
            "badge_class": "status-ok"
        }
    else:
        return {
            "mode": "sqlite",
            "label": "📦 SQLite (Lokal)",
            "short_label": "SQLite Local",
            "is_cloud": False,
            "badge_class": "status-ok"
        }


# ──────────────────────────────────────────────────────────────
# Helper Penyelarasan DataFrame ke Skema Database
# ──────────────────────────────────────────────────────────────

def prepare_df_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menyelaraskan nama kolom dan tipe data DataFrame agar sesuai skema pkk_records.
    """
    if df.empty:
        return pd.DataFrame()

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
            df_out[col] = pd.to_numeric(df_out[col], errors="coerce").astype("Int64").astype(object)

    schema_cols = ["pkk_number","vessel_name","port_code","port","service",
                   "submission","response","simpadu","gmt","approval_hours",
                   "approval_minutes","year","quarter","month","date","day","hour","angkutan"]
    return df_out[[c for c in schema_cols if c in df_out.columns]]


# ──────────────────────────────────────────────────────────────
# INSERT / UPSERT
# ──────────────────────────────────────────────────────────────

def insert_pkk_records(df: pd.DataFrame, batch_size: int = 500, progress_callback=None) -> dict:
    """
    Menyimpan DataFrame PKK ke Supabase (jika ada) atau SQLite lokal dengan upsert.
    """
    if df.empty:
        return {"success": True, "inserted": 0, "error": None}

    if is_supabase_connected():
        return _insert_pkk_records_supabase(df, batch_size=batch_size, progress_callback=progress_callback)
    else:
        return _insert_pkk_records_sqlite(df, batch_size=batch_size, progress_callback=progress_callback)


def _insert_pkk_records_supabase(df: pd.DataFrame, batch_size: int = 500, progress_callback=None) -> dict:
    client = get_supabase_client()
    df_out = prepare_df_for_db(df)
    if df_out.empty:
        return {"success": True, "inserted": 0, "error": None}

    records = df_out.where(pd.notnull(df_out), None).to_dict(orient="records")
    total_records = len(records)
    total_inserted = 0

    try:
        if progress_callback:
            progress_callback(0, total_records)
        for i in range(0, total_records, batch_size):
            chunk = records[i : i + batch_size]
            client.table("pkk_records").upsert(chunk, on_conflict="pkk_number").execute()
            total_inserted += len(chunk)
            if progress_callback:
                progress_callback(total_inserted, total_records)
        return {"success": True, "inserted": total_inserted, "error": None}
    except Exception as e:
        return {"success": False, "inserted": total_inserted, "error": str(e)}


def _insert_pkk_records_sqlite(df: pd.DataFrame, batch_size: int = 500, progress_callback=None) -> dict:
    try:
        init_sqlite_db()
        df_out = prepare_df_for_db(df)
        if df_out.empty:
            return {"success": True, "inserted": 0, "error": None}

        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        cols = list(df_out.columns)
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT OR REPLACE INTO pkk_records ({', '.join(cols)}) VALUES ({placeholders})"

        # Flatten records to tuple list
        records = df_out.where(pd.notnull(df_out), None).values.tolist()
        total_records = len(records)
        total_inserted = 0

        if progress_callback:
            progress_callback(0, total_records)

        for i in range(0, total_records, batch_size):
            chunk = records[i : i + batch_size]
            cursor.executemany(sql, chunk)
            conn.commit()
            total_inserted += len(chunk)
            if progress_callback:
                progress_callback(total_inserted, total_records)

        conn.close()
        return {"success": True, "inserted": total_inserted, "error": None}
    except Exception as e:
        return {"success": False, "inserted": 0, "error": str(e)}


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
    Mengambil data PKK dari Supabase Cloud (jika terhubung) atau SQLite lokal.
    """
    if is_supabase_connected():
        return _fetch_pkk_records_supabase(port_codes=port_codes, year=year, angkutan=angkutan, page_size=page_size)
    else:
        return _fetch_pkk_records_sqlite(port_codes=port_codes, year=year, angkutan=angkutan)


def _fetch_pkk_records_supabase(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    page_size: int = 1000,
) -> pd.DataFrame:
    client = get_supabase_client()
    if client is None:
        return pd.DataFrame()

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
        st.error(f"Error mengambil data dari Supabase: {e}")
        return pd.DataFrame()


def _fetch_pkk_records_sqlite(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
) -> pd.DataFrame:
    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)

        sql = "SELECT * FROM pkk_records WHERE 1=1"
        params = []

        if port_codes:
            placeholders = ", ".join(["?"] * len(port_codes))
            sql += f" AND port_code IN ({placeholders})"
            params.extend(port_codes)
        if year:
            sql += " AND year = ?"
            params.append(int(year))
        if angkutan and len(angkutan) == 1:
            sql += " AND angkutan = ?"
            params.append(angkutan[0])

        sql += " ORDER BY submission DESC"

        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()

        if df.empty:
            return pd.DataFrame()

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
        st.error(f"Error mengambil data dari SQLite: {e}")
        return pd.DataFrame()


def fetch_pkk_records_paginated(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[pd.DataFrame, int]:
    """
    Mengambil data PKK dengan filter, pencarian, dan pagination dari Supabase atau SQLite.
    """
    if is_supabase_connected():
        return _fetch_pkk_records_paginated_supabase(
            port_codes=port_codes, year=year, angkutan=angkutan, search_query=search_query, limit=limit, offset=offset
        )
    else:
        return _fetch_pkk_records_paginated_sqlite(
            port_codes=port_codes, year=year, angkutan=angkutan, search_query=search_query, limit=limit, offset=offset
        )


def _fetch_pkk_records_paginated_supabase(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[pd.DataFrame, int]:
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
        st.error(f"Error fetching data dari Supabase: {e}")
        return pd.DataFrame(), 0


def _fetch_pkk_records_paginated_sqlite(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[pd.DataFrame, int]:
    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)

        where_clause = " WHERE 1=1"
        params = []

        if port_codes:
            placeholders = ", ".join(["?"] * len(port_codes))
            where_clause += f" AND port_code IN ({placeholders})"
            params.extend(port_codes)
        if year:
            where_clause += " AND year = ?"
            params.append(int(year))
        if angkutan and len(angkutan) == 1:
            where_clause += " AND angkutan = ?"
            params.append(angkutan[0])
        if search_query and search_query.strip():
            sq = f"%{search_query.strip()}%"
            where_clause += " AND (pkk_number LIKE ? OR vessel_name LIKE ?)"
            params.extend([sq, sq])

        count_sql = f"SELECT COUNT(*) FROM pkk_records{where_clause}"
        cursor = conn.cursor()
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]

        data_sql = f"SELECT * FROM pkk_records{where_clause} ORDER BY submission DESC"
        data_params = list(params)
        if limit > 0:
            data_sql += " LIMIT ? OFFSET ?"
            data_params.extend([limit, offset])

        df = pd.read_sql_query(data_sql, conn, params=data_params)
        conn.close()

        DEFAULT_COLS = [
            "PKK_number", "vessel_name", "port_code", "port", "service",
            "submission", "response", "simpadu", "GMT", "approval_hours",
            "approval_minutes", "year", "quarter", "month", "date", "day",
            "hour", "angkutan"
        ]

        if df.empty:
            return pd.DataFrame(columns=DEFAULT_COLS), total_count

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
        st.error(f"Error fetching data dari SQLite: {e}")
        return pd.DataFrame(), 0


# ──────────────────────────────────────────────────────────────
# UTILITIES & MAINTENANCE
# ──────────────────────────────────────────────────────────────

def get_available_ports_from_db() -> List[str]:
    """Ambil daftar port_code yang tersedia di database."""
    if is_supabase_connected():
        client = get_supabase_client()
        try:
            response = client.table("pkk_records").select("port_code").execute()
            codes = list({r["port_code"] for r in response.data if r.get("port_code")})
            return sorted(codes)
        except Exception:
            return []
    else:
        try:
            init_sqlite_db()
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT port_code FROM pkk_records WHERE port_code IS NOT NULL AND port_code != ''")
            rows = cursor.fetchall()
            conn.close()
            return sorted([r[0] for r in rows if r[0]])
        except Exception:
            return []


def delete_pkk_records(port_codes: List[str], year: int) -> dict:
    """Hapus data berdasarkan port_code dan year."""
    if is_supabase_connected():
        client = get_supabase_client()
        try:
            client.table("pkk_records").delete().in_("port_code", port_codes).eq("year", year).execute()
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        try:
            init_sqlite_db()
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cursor = conn.cursor()
            placeholders = ", ".join(["?"] * len(port_codes))
            sql = f"DELETE FROM pkk_records WHERE port_code IN ({placeholders}) AND year = ?"
            cursor.execute(sql, port_codes + [year])
            conn.commit()
            conn.close()
            return {"success": True, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e)}


def deduplicate_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Menghapus duplikasi record dari DataFrame berdasarkan pkk_number.
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
    Mendeteksi dan menghapus record duplikat di Database berdasarkan pkk_number.
    """
    if is_supabase_connected():
        return _check_and_clean_db_duplicates_supabase(progress_callback=progress_callback)
    else:
        return _check_and_clean_db_duplicates_sqlite(progress_callback=progress_callback)


def _check_and_clean_db_duplicates_supabase(progress_callback=None) -> dict:
    client = get_supabase_client()
    if client is None:
        return {
            "total_checked": 0, "duplicates_found": 0, "duplicates_removed": 0,
            "clean_count": 0, "success": False, "error": "Supabase tidak terkonfigurasi."
        }

    try:
        if progress_callback:
            progress_callback("detect", "🔍 Mendeteksi data yang tersimpan di Supabase...", 20)

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

        seen = {}
        duplicate_ids = []
        for r in all_rows:
            pkk = r.get("pkk_number")
            rec_id = r.get("id")
            if not pkk or not rec_id:
                continue
            if pkk in seen:
                duplicate_ids.append(seen[pkk])
                seen[pkk] = rec_id
            else:
                seen[pkk] = rec_id

        duplicates_found = len(duplicate_ids)

        if duplicates_found > 0:
            if progress_callback:
                progress_callback("clean", f"🧹 Menghapus {duplicates_found:,} record duplikat dari Supabase...", 75)

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


def _check_and_clean_db_duplicates_sqlite(progress_callback=None) -> dict:
    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        if progress_callback:
            progress_callback("detect", "🔍 Mendeteksi data yang tersimpan di SQLite...", 20)

        cursor.execute("SELECT COUNT(*) FROM pkk_records")
        total_checked = cursor.fetchone()[0]

        if total_checked == 0:
            conn.close()
            return {
                "total_checked": 0, "duplicates_found": 0, "duplicates_removed": 0,
                "clean_count": 0, "success": True, "error": None
            }

        if progress_callback:
            progress_callback("count", f"🔢 Menghitung duplikasi data dari {total_checked:,} record...", 50)

        cursor.execute("""
            SELECT COUNT(*) FROM pkk_records 
            WHERE rowid NOT IN (
                SELECT MIN(rowid) FROM pkk_records GROUP BY pkk_number
            )
        """)
        duplicates_found = cursor.fetchone()[0]

        if duplicates_found > 0:
            if progress_callback:
                progress_callback("clean", f"🧹 Menghapus {duplicates_found:,} record duplikat dari SQLite...", 75)
            cursor.execute("""
                DELETE FROM pkk_records 
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM pkk_records GROUP BY pkk_number
                )
            """)
            conn.commit()
            duplicates_removed = duplicates_found
        else:
            duplicates_removed = 0

        cursor.execute("SELECT COUNT(*) FROM pkk_records")
        clean_count = cursor.fetchone()[0]
        conn.close()

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


def get_database_stats() -> dict:
    """
    Mengembalikan statistik metrik ringkas dari database (Supabase atau SQLite).
    """
    if is_supabase_connected():
        client = get_supabase_client()
        try:
            res_count = client.table("pkk_records").select("id", count="exact").limit(1).execute()
            total_records = res_count.count if res_count.count is not None else 0
            codes = get_available_ports_from_db()
            return {
                "connected": True,
                "db_type": "supabase",
                "total_records": total_records,
                "unique_ports": len(codes),
                "available_port_codes": codes,
                "error": None
            }
        except Exception:
            pass

    # Fallback to SQLite
    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pkk_records")
        total_records = cursor.fetchone()[0]
        conn.close()
        codes = get_available_ports_from_db()
        return {
            "connected": True,
            "db_type": "sqlite",
            "total_records": total_records,
            "unique_ports": len(codes),
            "available_port_codes": codes,
            "error": None
        }
    except Exception as e:
        return {"connected": False, "db_type": "none", "total_records": 0, "unique_ports": 0, "error": str(e)}


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
