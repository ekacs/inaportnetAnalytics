"""
modules/database.py
Operasi CRUD SQLite lokal untuk data PKK Inaportnet.
"""

import os
import sqlite3
import pandas as pd
from typing import Optional, List

# ──────────────────────────────────────────────────────────────
# Konfigurasi & Inisialisasi SQLite Lokal
# ──────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SQLITE_DB_PATH = os.path.join(DATA_DIR, "inaportnet_local.db")


def init_sqlite_db():
    """Memastikan folder data dan tabel pkk_records SQLite lokal sudah dibuat."""
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
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_port_code ON pkk_records(port_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_year ON pkk_records(year);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkk_submission ON pkk_records(submission);")
    conn.commit()
    conn.close()


def get_sqlite_conn():
    """Membuka koneksi SQLite baru."""
    init_sqlite_db()
    return sqlite3.connect(SQLITE_DB_PATH)


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
# Helper Penyelaraskan DataFrame Skema Database
# ──────────────────────────────────────────────────────────────

def prepare_df_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """Menyelaraskan nama kolom dan tipe data DataFrame agar sesuai skema pkk_records."""
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

    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    target_cols = list(col_map.values())
    for c in target_cols:
        if c not in df.columns:
            df[c] = None

    return df[target_cols]


# ──────────────────────────────────────────────────────────────
# INSERT
# ──────────────────────────────────────────────────────────────

def insert_pkk_records(df: pd.DataFrame) -> dict:
    """Insert records into SQLite database."""
    if df.empty:
        return {"success": True, "inserted": 0, "error": None}

    df_db = prepare_df_for_db(df)
    if df_db.empty:
        return {"success": True, "inserted": 0, "error": None}

    try:
        return _insert_pkk_records_sqlite(df_db)
    except Exception as e:
        return {"success": False, "inserted": 0, "error": str(e)}


def _insert_pkk_records_sqlite(df: pd.DataFrame) -> dict:
    """Insert records into SQLite."""
    if df.empty:
        return {"success": True, "inserted": 0, "error": None}

    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        inserted = 0
        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO pkk_records
                    (pkk_number, vessel_name, port_code, port, service, submission, response,
                     simpadu, gmt, approval_hours, approval_minutes, year, quarter, month,
                     date, day, hour, angkutan)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get("pkk_number"), row.get("vessel_name"), row.get("port_code"),
                    row.get("port"), row.get("service"), row.get("submission"),
                    row.get("response"), row.get("simpadu"), row.get("gmt"),
                    row.get("approval_hours"), row.get("approval_minutes"),
                    row.get("year"), row.get("quarter"), row.get("month"),
                    row.get("date"), row.get("day"), row.get("hour"), row.get("angkutan")
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                continue

        conn.commit()
        conn.close()
        return {"success": True, "inserted": inserted, "error": None}
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
    """Mengambil data PKK dari SQLite."""
    return _fetch_pkk_records_sqlite(port_codes=port_codes, year=year, angkutan=angkutan)


def _fetch_pkk_records_sqlite(
    port_codes: Optional[List[str]] = None,
    year: Optional[int] = None,
    angkutan: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Mengambil data dari SQLite."""
    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)

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
        query = f"SELECT * FROM pkk_records WHERE {where_sql} ORDER BY submission DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        df.rename(columns={"pkk_number": "PKK_number", "gmt": "GMT"}, inplace=True, errors="ignore")
        return df
    except Exception as e:
        return pd.DataFrame()


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
    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)

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
        conn.close()

        df.rename(columns={"pkk_number": "PKK_number", "gmt": "GMT"}, inplace=True, errors="ignore")
        return df, int(total_count)
    except Exception as e:
        return pd.DataFrame(), 0


# ──────────────────────────────────────────────────────────────
# DELETE
# ──────────────────────────────────────────────────────────────

def delete_pkk_records(port_codes: List[str], year: int) -> dict:
    """Hapus data berdasarkan port_code dan year dari SQLite."""
    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(port_codes))
        cursor.execute(
            f"DELETE FROM pkk_records WHERE port_code IN ({placeholders}) AND year = ?",
            port_codes + [year]
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return {"success": True, "deleted": deleted, "error": None}
    except Exception as e:
        return {"success": False, "deleted": 0, "error": str(e)}


def delete_all_sqlite_records() -> dict:
    """Hapus SEMUA record dari SQLite lokal + hapus file .db dari disk."""
    try:
        count = 0
        if os.path.exists(SQLITE_DB_PATH):
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM pkk_records")
            count = cursor.fetchone()[0]
            conn.close()

        for ext in ("", "-shm", "-wal"):
            path = SQLITE_DB_PATH + ext
            if os.path.exists(path):
                os.remove(path)

        return {"success": True, "deleted": count, "error": None}
    except Exception as e:
        return {"success": False, "deleted": 0, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# STATS & PORTS
# ──────────────────────────────────────────────────────────────

def get_database_stats() -> dict:
    """Mengembalikan statistik metrik ringkas dari database SQLite."""
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


def get_available_ports_from_db() -> List[str]:
    """Ambil daftar port_code yang tersedia di database."""
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


# ──────────────────────────────────────────────────────────────
# DEDUPLICATION
# ──────────────────────────────────────────────────────────────

def check_and_clean_db_duplicates(progress_callback=None) -> dict:
    """Deteksi dan hapus duplikasi data berdasarkan pkk_number di SQLite."""
    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        if progress_callback:
            progress_callback("counting", "Menghitung total record...", 10)

        cursor.execute("SELECT COUNT(*) FROM pkk_records")
        total_checked = cursor.fetchone()[0]

        if total_checked == 0:
            conn.close()
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
            conn.close()
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
        conn.close()

        if progress_callback:
            progress_callback("complete", f"Data bersih dari duplikasi! Total: {clean_count:,} record.", 100)

        return {
            "success": True, "total_checked": total_checked, "duplicates_found": duplicates_found,
            "duplicates_removed": duplicates_removed, "clean_count": clean_count, "error": None
        }
    except Exception as e:
        return {
            "success": False, "total_checked": 0, "duplicates_found": 0,
            "duplicates_removed": 0, "clean_count": 0, "error": str(e)
        }


# ──────────────────────────────────────────────────────────────
# SQL DUMP
# ──────────────────────────────────────────────────────────────

def generate_sql_dump() -> str:
    """Generate SQL INSERT statements from SQLite database."""
    try:
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pkk_records ORDER BY submission DESC")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        conn.close()

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
