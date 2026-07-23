"""
modules/preprocessing.py
Preprocessing data PKK: parsing datetime, kalkulasi approval time,
ekstraksi komponen waktu, dan filtering.
Refactoring dari 01_data_preprocessing.py.
"""

import pandas as pd
from datetime import timedelta


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Memproses DataFrame PKK mentah menjadi dataset analisis.

    Langkah:
    1. Parse kolom submission & response sebagai datetime
    2. Hitung approval_time, approval_hours, approval_minutes
    3. Ekstrak komponen waktu: year, quarter, month, date, day, hour
    4. Filter data di luar scope tahun 2025
    5. Tandai record bug (approval_time negatif)

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame hasil scraping atau upload, dengan kolom
        'submission' dan 'response'.

    Returns
    -------
    pd.DataFrame : dataset bersih siap analisis
    """
    if df.empty:
        return df

    df = df.copy()

    # ── 1. Parse datetime ──────────────────────────────────────────
    for col in ["submission", "response"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # ── 2. Hitung approval time ────────────────────────────────────
    if "submission" in df.columns and "response" in df.columns:
        df["approval_time"]    = df["response"] - df["submission"]
        df["approval_hours"]   = df["approval_time"].dt.total_seconds() / 3600
        df["approval_minutes"] = df["approval_time"].dt.total_seconds() / 60

    # ── 3. Komponen waktu dari submission ──────────────────────────
    if "submission" in df.columns:
        df["year"]    = df["submission"].dt.year
        df["quarter"] = df["submission"].dt.to_period("Q").astype(str)
        df["month"]   = df["submission"].dt.month
        df["date"]    = df["submission"].dt.date
        df["day"]     = df["submission"].dt.day_name()
        df["hour"]    = df["submission"].dt.hour

    # ── 4. Filter hanya data tahun 2025 ───────────────────────────
    if "year" in df.columns:
        df = df[df["year"] == 2025].copy()

    # ── 5. Tandai data bug (approval negatif) ──────────────────────
    if "approval_time" in df.columns:
        df["is_bug"] = df["approval_time"] < timedelta(seconds=0)
        # Untuk analisis, set nilai negatif ke NaN
        df.loc[df["is_bug"], ["approval_hours", "approval_minutes"]] = float("nan")

    df = df.reset_index(drop=True)
    return df


def validate_uploaded_file(df: pd.DataFrame) -> dict:
    """
    Validasi DataFrame yang diupload oleh user.

    Returns
    -------
    dict : {'valid': bool, 'message': str, 'is_raw': bool}
        is_raw = True  → perlu dipreprocess
        is_raw = False → sudah memiliki kolom approval_minutes
    """
    required_raw = {"submission", "response"}
    required_processed = {"approval_minutes", "approval_hours"}

    cols = set(df.columns)

    if required_processed.issubset(cols):
        return {
            "valid": True,
            "message": "✅ Data sudah dipreprocess. Siap digunakan.",
            "is_raw": False,
        }
    elif required_raw.issubset(cols):
        return {
            "valid": True,
            "message": "📝 Data mentah terdeteksi. Preprocessing akan dijalankan otomatis.",
            "is_raw": True,
        }
    else:
        missing = (required_raw | required_processed) - cols
        return {
            "valid": False,
            "message": (
                f"❌ Kolom tidak lengkap. Diperlukan salah satu dari: "
                f"'submission'+'response' atau 'approval_minutes'+'approval_hours'. "
                f"Kolom yang hilang: {missing}"
            ),
            "is_raw": False,
        }
