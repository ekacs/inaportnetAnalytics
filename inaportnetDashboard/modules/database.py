"""
modules/database.py
Operasi CRUD SQLite lokal untuk data PKK Inaportnet.
"""

import os
import sqlite3
import datetime as _dt
import numpy as _np
import pandas as pd
from typing import Optional, List, Callable

# ──────────────────────────────────────────────────────────────
# Konfigurasi & Inisialisasi SQLite Lokal
# ──────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SQLITE_DB_PATH = os.path.join(DATA_DIR, "inaportnet_local.db")


_SQLITE_TIMEOUT_S = 30  # Streamlit rerun + insert batch butuh tunggu lock lama


def _connect():
    """Buka koneksi SQLite dengan timeout & WAL agar tahan 'database is locked'.

    - timeout/busy_timeout 30 dtk: pembaca (COUNT(*)/fetch) menunggu penulis
      (insert batch) selesai, bukan langsung OperationalError.
    - journal_mode=WAL: baca tidak diblokir tulis (DB 140MB, insert lama).
    """
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=_SQLITE_TIMEOUT_S)
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute(f"PRAGMA busy_timeout = {_SQLITE_TIMEOUT_S * 1000};")
    except Exception:
        pass
    return conn


def init_sqlite_db():
    """Memastikan folder data dan tabel pkk_records SQLite lokal sudah dibuat."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = _connect()
    try:
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
        )
    """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_port_code ON pkk_records(port_code);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_year ON pkk_records(year);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_submission ON pkk_records(submission);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_number ON pkk_records(pkk_number);")
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_sqlite_conn():
    """Membuka koneksi SQLite baru."""
    init_sqlite_db()
    return _connect()


# ──────────────────────────────────────────────────────────────
# Status Database
# ──────────────────────────────────────────────────────────────

def is_connected() -> bool:
    """Cek apakah database siap digunakan."""
    return True


def get_db_mode() -> str:
    """Mengembalikan mode database yang aktif."""
    return "sqlite"


def get_db_status_info() -> dict:
    """Mengembalikan informasi status koneksi database untuk tampilan UI."""
    return {
        "mode": "sqlite",
        "label": "📦 SQLite (Lokal)",
        "short_label": "SQLite Local",
        "is_cloud": False,
        "badge_class": "status-ok"
    }


# ──────────────────────────────────────────────────────────────
# Helper Sanitasi Tipe untuk SQLite (Opsi A: string ISO)
# sqlite3 stdlib hanya menerima None/str/int/float/bytes.
# ──────────────────────────────────────────────────────────────

_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
_DATE_FMT = "%Y-%m-%d"


def _to_datetime_str(value):
    """Konversi nilai datetime-like ke string ISO atau None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, str):
        s = value.strip()
        if s == "" or s.lower() in ("nan", "nat", "none", "null"):
            return None
        try:
            parsed = pd.to_datetime(s, errors="coerce")
            if pd.isna(parsed):
                return s
            return parsed.strftime(_DATETIME_FMT)
        except Exception:
            return s
    try:
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.strftime(_DATETIME_FMT)
    except Exception:
        return None


def _to_date_str(value):
    """Konversi nilai date-like ke 'YYYY-MM-DD' atau None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, str):
        s = value.strip()
        if s == "" or s.lower() in ("nan", "nat", "none", "null"):
            return None
        try:
            parsed = pd.to_datetime(s, errors="coerce")
            if pd.isna(parsed):
                return s
            return parsed.strftime(_DATE_FMT)
        except Exception:
            return s
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.strftime(_DATE_FMT)
    except Exception:
        return None

def _to_float_or_none(value):
    try:
        if value is None:
            return None
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        if isinstance(value, str):
            s = value.strip().replace(",", ".")
            if s == "" or s.lower() in ("nan", "nat", "none", "null"):
                return None
            return float(s)
        return float(value)
    except Exception:
        return None


def _to_int_or_none(value):
    try:
        if value is None:
            return None
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        if isinstance(value, str):
            s = value.strip()
            if s == "" or s.lower() in ("nan", "nat", "none", "null"):
                return None
            return int(float(s.replace(",", ".")))
        return int(float(value))
    except Exception:
        return None


def _to_text_or_none(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, str):
        s = value.strip()
        if s == "" or s.lower() in ("nan", "nat", "none", "null"):
            return None
        return s
    try:
        if isinstance(value, (_np.generic, pd.Timestamp)):
            conv = _to_datetime_str(value)
            return conv if conv is not None else str(value).strip()
        return str(value).strip()
    except Exception:
        return None


def _to_sqlite_value(value):
    """Pengaman lapis-2: pastikan nilai tunggal aman untuk bind sqlite3."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bytes)):
        if isinstance(value, float) and pd.isna(value):
            return None
        return value
    if isinstance(value, _np.integer):
        return int(value)
    if isinstance(value, _np.floating):
        f = float(value)
        return None if pd.isna(f) else f
    if isinstance(value, _np.bool_):
        return int(bool(value))
    if isinstance(value, (_np.datetime64, pd.Timestamp)):
        return _to_datetime_str(value)
    if isinstance(value, _dt.datetime):
        try:
            return value.strftime(_DATETIME_FMT)
        except Exception:
            return None
    if isinstance(value, _dt.date):
        try:
            return value.strftime(_DATE_FMT)
        except Exception:
            return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return str(value)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────
# Helper Penyelarasan DataFrame ke Skema Database
# ──────────────────────────────────────────────────────────────

def _to_datetime_str(series: pd.Series, fmt: str) -> pd.Series:
    """
    Ubah kolom menjadi string bertanggal dengan format target.

    Format diketahui pasti (data influx sudah dinormalkan ke %Y-%m-%d %H:%M:%S),
    jadi format itu dicoba lebih dulu. Tanpa ini pandas menebak format per
    elemen dengan dateutil, yang jauh lebih lambat dan memunculkan warning
    "Could not infer format".values yang tak sesuai format tetap jadi NaT.
    """
    try:
        return pd.to_datetime(series, format=fmt, errors="coerce").dt.strftime(fmt)
    except (ValueError, TypeError):
        return pd.to_datetime(series, errors="coerce").dt.strftime(fmt)


def prepare_df_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """Menyelaraskan nama kolom dan tipe data sesuai skema pkk_records secara cepat & aman."""
    if df.empty:
        return pd.DataFrame()

    col_map = {
        "PKK_number": "pkk_number",
        "vessel_name": "vessel_name",
        "port_code": "port_code",
        "port": "port",
        "service": "service",
        "submission": "submission",
        "response": "response",
        "simpadu": "simpadu",
        "GMT": "gmt",
        "approval_hours": "approval_hours",
        "approval_minutes": "approval_minutes",
        "year": "year",
        "quarter": "quarter",
        "month": "month",
        "date": "date",
        "day": "day",
        "hour": "hour",
        "angkutan": "angkutan",
    }

    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}).copy()

    target_cols = list(col_map.values())
    for c in target_cols:
        if c not in df.columns:
            df[c] = None

    # Sanitasi vektorisasi cepat untuk kolom datetime/date
    for c in ("submission", "response", "simpadu", "gmt"):
        df[c] = _to_datetime_str(df[c], _DATETIME_FMT)

    df["date"] = _to_datetime_str(df["date"], _DATE_FMT)

    for c in ("approval_hours", "approval_minutes"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in ("year", "month", "hour"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df[target_cols]


# ──────────────────────────────────────────────────────────────
# INSERT
# ──────────────────────────────────────────────────────────────

def insert_pkk_records(df: pd.DataFrame, progress_callback: Optional[Callable[[int, int], None]] = None) -> dict:
    """Insert records into SQLite database dengan batch insert berkecepatan tinggi."""
    if df.empty:
        return {"success": True, "inserted": 0, "error": None}

    df_db = prepare_df_for_db(df)
    if df_db.empty:
        return {"success": True, "inserted": 0, "error": None}

    try:
        return _insert_pkk_records_sqlite(df_db, progress_callback=progress_callback)
    except Exception as e:
        return {"success": False, "inserted": 0, "error": str(e)}


def _insert_pkk_records_sqlite(
    df: pd.DataFrame,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    batch_size: int = 50000,
) -> dict:
    """Insert records into SQLite dengan batching executemany dan optimasi WAL."""
    if df.empty:
        return {"success": True, "inserted": 0, "error": None}

    conn = None
    try:
        init_sqlite_db()
        conn = _connect()
        cursor = conn.cursor()

        target_cols = [
            "pkk_number", "vessel_name", "port_code", "port", "service",
            "submission", "response", "simpadu", "gmt", "approval_hours",
            "approval_minutes", "year", "quarter", "month", "date", "day",
            "hour", "angkutan"
        ]

        for c in target_cols:
            if c not in df.columns:
                df[c] = None

        total_rows = len(df)
        inserted = 0

        insert_sql = f"""
            INSERT OR REPLACE INTO pkk_records
            ({", ".join(target_cols)})
            VALUES ({", ".join(["?"] * len(target_cols))})
        """

        clean_df = df[target_cols].where(pd.notnull(df[target_cols]), None)

        for start_idx in range(0, total_rows, batch_size):
            end_idx = min(start_idx + batch_size, total_rows)
            batch_slice = clean_df.iloc[start_idx:end_idx]

            records = [
                tuple(
                    None if (isinstance(val, float) and pd.isna(val)) or val is None or (isinstance(val, str) and val in ("nan", "None", "<NA>", "nat", "NaT", ""))
                    else (int(val) if col in ("year", "month", "hour") and val is not None and not pd.isna(val) else val)
                    for col, val in zip(target_cols, row)
                )
                for row in batch_slice.itertuples(index=False, name=None)
            ]

            cursor.executemany(insert_sql, records)
            conn.commit()
            inserted += len(records)

            if progress_callback:
                progress_callback(inserted, total_rows)

        return {"success": True, "inserted": inserted, "error": None}
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return {"success": False, "inserted": 0, "error": str(e)}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────
# FETCH
# ──────────────────────────────────────────────────────────────

def fetch_pkk_records(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    page_size: int = 1000,
    progress_callback: Optional[Callable] = None,
    chunk_size: int = 50000,
) -> pd.DataFrame:
    """Mengambil data PKK dari SQLite secara bertahap (chunked) dengan progres.

    progress_callback(done, total, phase) dengan phase 'counting'/'fetching'.
    """
    return _fetch_pkk_records_sqlite(
        port_codes=port_codes, year=year, angkutan=angkutan,
        progress_callback=progress_callback, chunk_size=chunk_size,
    )


def _fetch_pkk_records_sqlite(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    progress_callback: Optional[Callable] = None,
    chunk_size: int = 50000,
) -> pd.DataFrame:
    """Mengambil data dari SQLite per chunk agar UI bisa menampilkan progres."""
    conn = None
    try:
        init_sqlite_db()
        conn = _connect()

        where_clauses = ["1=1"]
        params = []

        if port_codes:
            placeholders = ",".join(["?"] * len(port_codes))
            where_clauses.append(f"port_code IN ({placeholders})")
            params.extend(port_codes)
        if year is not None:
            where_clauses.append("year = ?")
            params.append(int(year))
        if angkutan and len(angkutan) == 1:
            where_clauses.append("angkutan = ?")
            params.append(angkutan[0])

        where_sql = " AND ".join(where_clauses)
        if progress_callback:
            try:
                progress_callback(0, 0, "counting")
            except Exception:
                pass
        total = int(conn.execute(
            f"SELECT COUNT(*) FROM pkk_records WHERE {where_sql}", params
        ).fetchone()[0] or 0)
        if total == 0:
            return pd.DataFrame()

        try:
            chunk_size = int(chunk_size)
        except Exception:
            chunk_size = 50000
        if chunk_size <= 0:
            chunk_size = 50000

        base_query = f"SELECT * FROM pkk_records WHERE {where_sql} ORDER BY submission DESC"
        chunks = []
        fetched = 0
        for offset in range(0, total, chunk_size):
            chunk_df = pd.read_sql_query(
                f"{base_query} LIMIT ? OFFSET ?",
                conn, params=[*params, int(chunk_size), int(offset)],
            )
            if chunk_df.empty:
                break
            chunks.append(chunk_df)
            fetched += len(chunk_df)
            if progress_callback:
                try:
                    progress_callback(min(fetched, total), total, "fetching")
                except Exception:
                    pass
        df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()

        df.rename(columns={"pkk_number": "PKK_number", "gmt": "GMT"}, inplace=True, errors="ignore")
        return df
    except Exception as e:
        return pd.DataFrame()
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def fetch_pkk_records_paginated(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[pd.DataFrame, int]:
    """Mengambil data PKK dengan filter, pencarian, dan pagination dari SQLite."""
    return _fetch_pkk_records_paginated_sqlite(
        port_codes=port_codes, year=year, angkutan=angkutan, search_query=search_query, limit=limit, offset=offset
    )


def _fetch_pkk_records_paginated_sqlite(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[pd.DataFrame, int]:
    """Mengambil data dari SQLite dengan pagination."""
    conn = None
    try:
        init_sqlite_db()
        conn = _connect()

        where_clause = "WHERE 1=1"
        params = []

        if port_codes:
            placeholders = ",".join(["?"] * len(port_codes))
            where_clause += f" AND port_code IN ({placeholders})"
            params.extend(port_codes)
        if year is not None:
            where_clause += " AND year = ?"
            params.append(int(year))
        if angkutan and len(angkutan) == 1:
            where_clause += " AND angkutan = ?"
            params.append(angkutan[0])
        if search_query and search_query.strip():
            sq = f"%{search_query.strip()}%"
            where_clause += " AND (pkk_number LIKE ? OR vessel_name LIKE ?)"
            params.extend([sq, sq])

        count_query = f"SELECT COUNT(*) FROM pkk_records {where_clause}"
        total_count = pd.read_sql_query(count_query, conn, params=params).iloc[0, 0]

        data_query = f"SELECT * FROM pkk_records {where_clause} ORDER BY submission DESC LIMIT ? OFFSET ?"
        df = pd.read_sql_query(data_query, conn, params=params + [limit, offset])

        df.rename(columns={"pkk_number": "PKK_number", "gmt": "GMT"}, inplace=True, errors="ignore")
        return df, int(total_count)
    except Exception as e:
        return pd.DataFrame(), 0
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────────────────────

def delete_pkk_records(port_codes: List[str], year: int) -> dict:
    """Hapus data berdasarkan port_code dan year dari SQLite."""
    conn = None
    try:
        init_sqlite_db()
        conn = _connect()
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(port_codes))
        cursor.execute(
            f"DELETE FROM pkk_records WHERE port_code IN ({placeholders}) AND year = ?",
            port_codes + [year]
        )
        deleted = cursor.rowcount
        conn.commit()
        return {"success": True, "deleted": deleted, "error": None}
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return {"success": False, "deleted": 0, "error": str(e)}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def delete_all_sqlite_records() -> dict:
    """Hapus SEMUA record dari SQLite lokal + hapus file .db dari disk."""
    conn = None
    try:
        count = 0
        if os.path.exists(SQLITE_DB_PATH):
            conn = _connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pkk_records")
            count = cursor.fetchone()[0]
            try:
                conn.close()
            except Exception:
                pass
            conn = None

        for ext in ("", "-shm", "-wal"):
            path = SQLITE_DB_PATH + ext
            if os.path.exists(path):
                os.remove(path)

        return {"success": True, "deleted": count, "error": None}
    except Exception as e:
        return {"success": False, "deleted": 0, "error": str(e)}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────
# STATS & PORTS
# ──────────────────────────────────────────────────────────────

def get_database_stats() -> dict:
    """Mengembalikan statistik metrik ringkas dari database SQLite."""
    conn = None
    try:
        init_sqlite_db()
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pkk_records")
        total_records = cursor.fetchone()[0]
        try:
            conn.close()
        except Exception:
            pass
        conn = None
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
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def get_available_ports_from_db() -> List[str]:
    """Ambil daftar port_code yang tersedia di database."""
    conn = None
    try:
        init_sqlite_db()
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT port_code FROM pkk_records WHERE port_code IS NOT NULL AND port_code != ''")
        rows = cursor.fetchall()
        return sorted([r[0] for r in rows if r[0]])
    except Exception:
        return []
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────
# DEDUPLICATION
# ──────────────────────────────────────────────────────────────

def deduplicate_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Menghapus duplikasi record dari DataFrame berdasarkan pkk_number."""
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
    """Deteksi dan hapus duplikasi data berdasarkan pkk_number di SQLite."""
    conn = None
    try:
        init_sqlite_db()
        conn = _connect()
        cursor = conn.cursor()

        if progress_callback:
            progress_callback("counting", "Menghitung total record...", 10)

        cursor.execute("SELECT COUNT(*) FROM pkk_records")
        total_checked = cursor.fetchone()[0]

        if total_checked == 0:
            return {
                "success": True, "total_checked": 0, "duplicates_found": 0,
                "duplicates_removed": 0, "clean_count": 0, "error": None
            }

        if progress_callback:
            progress_callback("detecting", "Mendeteksi duplikasi...", 40)

        cursor.execute("""
            SELECT pkk_number, COUNT(*) as cnt
            FROM pkk_records
            GROUP BY pkk_number
            HAVING cnt > 1
        """)
        duplicates = cursor.fetchall()
        duplicates_found = sum(cnt - 1 for _, cnt in duplicates)

        if duplicates_found == 0:
            return {
                "success": True, "total_checked": total_checked, "duplicates_found": 0,
                "duplicates_removed": 0, "clean_count": total_checked, "error": None
            }

        if progress_callback:
            progress_callback("cleaning", f"Menghapus {duplicates_found} duplikasi...", 70)

        cursor.execute("""
            DELETE FROM pkk_records
            WHERE rowid NOT IN (
                SELECT MIN(rowid) FROM pkk_records GROUP BY pkk_number
            )
        """)
        duplicates_removed = cursor.rowcount
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM pkk_records")
        clean_count = cursor.fetchone()[0]

        if progress_callback:
            progress_callback("complete", f"Data bersih dari duplikasi! Total: {clean_count:,} record.", 100)

        return {
            "success": True, "total_checked": total_checked, "duplicates_found": duplicates_found,
            "duplicates_removed": duplicates_removed, "clean_count": clean_count, "error": None
        }
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return {
            "success": False, "total_checked": 0, "duplicates_found": 0,
            "duplicates_removed": 0, "clean_count": 0, "error": str(e)
        }
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────
# SQL DUMP
# ──────────────────────────────────────────────────────────────

def generate_sql_dump() -> str:
    """Generate SQL INSERT statements from SQLite database."""
    conn = None
    try:
        init_sqlite_db()
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pkk_records ORDER BY submission DESC")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        if not rows:
            return "-- Tidak ada data di database\n"

        lines = ["-- Inaportnet Analytics SQL Dump", "-- Generated from SQLite Local", ""]

        for row in rows:
            values = []
            for val in row:
                if val is None:
                    values.append("NULL")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    escaped = str(val).replace("'", "''")
                    values.append(f"'{escaped}'")
            cols_str = ", ".join(columns)
            vals_str = ", ".join(values)
            lines.append(f"INSERT INTO pkk_records ({cols_str}) VALUES ({vals_str});")

        return "\n".join(lines)
    except Exception as e:
        return f"-- Error generating dump: {e}\n"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
