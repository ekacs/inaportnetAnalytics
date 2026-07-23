"""
modules/scraper.py
Fungsi web scraping dari portal monitoring Inaportnet.
Refactoring dari 00_data_collection.py menjadi fungsi modular.
"""

import requests
import pandas as pd
from io import StringIO
from typing import List, Callable, Optional
import time

BASE_URL = "https://monitoring-inaportnet.dephub.go.id"


def scrape_pkk_list(
    port_codes: List[str],
    angkutan: List[str],
    year: int,
    months: List[int],
    progress_callback: Optional[Callable] = None,
    status_callback: Optional[Callable] = None,
) -> pd.DataFrame:
    """
    Tahap 1: Mengambil daftar nomor PKK untuk setiap kombinasi
    pelabuhan × jenis angkutan × bulan.

    Parameters
    ----------
    port_codes : list of str
        Kode LOCODE pelabuhan (misal: ['IDTJB', 'IDJKT']).
    angkutan : list of str
        Jenis angkutan: ['dn'], ['ln'], atau ['dn', 'ln'].
    year : int
        Tahun data (misal: 2025).
    months : list of int
        Daftar bulan yang di-scraping (1–12).
    progress_callback : callable(current, total)
        Dipanggil setiap iterasi untuk update progress bar.
    status_callback : callable(message: str)
        Dipanggil untuk update teks status.

    Returns
    -------
    pd.DataFrame : kolom [nomor_pkk, nama_kapal, pelabuhan_kode, bulan, angkutan]
    """
    hasil = []
    total_iterations = len(angkutan) * len(port_codes) * len(months)
    current = 0

    for svc in angkutan:
        for port in port_codes:
            for month in months:
                current += 1
                if progress_callback:
                    progress_callback(current, total_iterations)
                if status_callback:
                    status_callback(
                        f"[{current}/{total_iterations}] Mengambil PKK list: "
                        f"{port} | {svc.upper()} | Bulan {month:02d}/{year}"
                    )

                url = (
                    f"{BASE_URL}/monitoring/byPort/list/"
                    f"{port}/{svc}/{year}/{month:02d}"
                )
                try:
                    r = requests.get(url, timeout=30)
                    if r.status_code != 200:
                        continue
                    js = r.json()
                    if not js.get("data"):
                        continue
                    df = pd.DataFrame(js["data"])
                    df["bulan"] = month
                    df["pelabuhan"] = port
                    df["angkutan"] = svc
                    hasil.append(df)
                except Exception:
                    continue

    if not hasil:
        return pd.DataFrame()

    df_all = pd.concat(hasil, ignore_index=True)

    # Pilih kolom yang relevan
    keep_cols = ["nomor_pkk", "nama_kapal", "pelabuhan_kode", "bulan", "angkutan"]
    available = [c for c in keep_cols if c in df_all.columns]
    return df_all[available].drop_duplicates(subset=["nomor_pkk"]).reset_index(drop=True)


def scrape_approval_times(
    df_pkk: pd.DataFrame,
    progress_callback: Optional[Callable] = None,
    status_callback: Optional[Callable] = None,
) -> pd.DataFrame:
    """
    Tahap 2: Mengambil waktu permohonan dan persetujuan untuk setiap nomor PKK.

    Parameters
    ----------
    df_pkk : pd.DataFrame
        DataFrame dengan kolom 'nomor_pkk'.
    progress_callback : callable(current, total)
    status_callback : callable(message: str)

    Returns
    -------
    pd.DataFrame : kolom [nomor_pkk, Layanan, Permohonan, Persetujuan, Nomor Produk]
    """
    approval_list = []
    total = len(df_pkk)

    for idx, nomor_pkk in enumerate(df_pkk["nomor_pkk"], start=1):
        if progress_callback:
            progress_callback(idx, total)
        if status_callback and idx % 50 == 0:
            status_callback(
                f"[{idx}/{total}] Mengambil approval time: PKK {nomor_pkk}"
            )

        url = f"{BASE_URL}/monitoring/detail?nomor_pkk={nomor_pkk}"
        try:
            html = requests.get(url, timeout=30).text
            dfs = pd.read_html(StringIO(html))
            approval = dfs[2].copy()
            approval.columns = approval.columns.get_level_values(1)
            approval = approval[approval["Layanan"] == "PKK"]
            approval = approval[["Layanan", "Permohonan", "Persetujuan", "Nomor Produk"]].copy()
            approval["nomor_pkk"] = nomor_pkk
            approval_list.append(approval)
        except Exception:
            continue

    if not approval_list:
        return pd.DataFrame()

    return pd.concat(approval_list, ignore_index=True)


def load_port_reference(filepath: str = "data/port_code.xlsx") -> pd.DataFrame:
    """
    Memuat referensi kode dan nama pelabuhan dari file Excel.

    Returns
    -------
    pd.DataFrame : kolom minimal [KODE, PELABUHAN]
    """
    try:
        df = pd.read_excel(filepath)
        return df
    except Exception as e:
        return pd.DataFrame(columns=["KODE", "PELABUHAN"])


def run_full_scraping(
    port_codes: List[str],
    angkutan: List[str],
    year: int,
    months: List[int],
    port_ref_path: str = "data/port_code.xlsx",
    progress_stage1: Optional[Callable] = None,
    status_stage1: Optional[Callable] = None,
    progress_stage2: Optional[Callable] = None,
    status_stage2: Optional[Callable] = None,
) -> pd.DataFrame:
    """
    Menjalankan scraping lengkap (2 tahap) dan menggabungkan hasilnya
    dengan referensi nama pelabuhan.

    Returns
    -------
    pd.DataFrame : data PKK mentah (belum dipreprocess) dengan kolom:
        port_code, port, PKK_number, vessel_name, service,
        submission, response, simpadu, GMT, angkutan
    """
    # --- Tahap 1: Daftar PKK ---
    df_pkk = scrape_pkk_list(
        port_codes=port_codes,
        angkutan=angkutan,
        year=year,
        months=months,
        progress_callback=progress_stage1,
        status_callback=status_stage1,
    )

    if df_pkk.empty:
        return pd.DataFrame()

    # --- Tahap 2: Waktu Approval ---
    approval_df = scrape_approval_times(
        df_pkk=df_pkk,
        progress_callback=progress_stage2,
        status_callback=status_stage2,
    )

    if approval_df.empty:
        return pd.DataFrame()

    # --- Gabungkan PKK + Approval ---
    df_merged = df_pkk.merge(approval_df, on="nomor_pkk", how="left")

    # --- Gabungkan dengan referensi pelabuhan ---
    df_port = load_port_reference(port_ref_path)
    if not df_port.empty:
        df_merged = df_merged.merge(
            df_port, left_on="pelabuhan_kode", right_on="KODE", how="left"
        )

    # --- Rename kolom ke standar app ---
    rename_map = {
        "pelabuhan_kode": "port_code",
        "PELABUHAN":      "port",
        "nomor_pkk":      "PKK_number",
        "nama_kapal":     "vessel_name",
        "Layanan":        "service",
        "Permohonan":     "submission",
        "Persetujuan":    "response",
        "Nomor Produk":   "simpadu",
    }
    df_merged = df_merged.rename(columns=rename_map)

    # Pilih kolom final
    final_cols = [
        "port_code", "port", "PKK_number", "vessel_name",
        "service", "submission", "response", "simpadu", "angkutan"
    ]
    available = [c for c in final_cols if c in df_merged.columns]
    return df_merged[available].drop_duplicates(subset=["PKK_number"]).reset_index(drop=True)
