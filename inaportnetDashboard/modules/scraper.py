"""
modules/scraper.py
Fungsi web scraping dari portal monitoring Inaportnet.
Refactoring dari 00_data_collection.py menjadi fungsi modular.

Anti-detection:
  - requests.Session() untuk connection pooling & persistent cookies
  - Rotasi User-Agent (browser-like)
  - Random delay antar-request (jitter)
  - Retry dengan exponential backoff (max 3 attempt)
"""

import os
import requests
import pandas as pd
import random
import time
from io import StringIO
from typing import List, Callable, Optional, Dict, Any

BASE_URL = "https://monitoring-inaportnet.dephub.go.id"
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(os.path.dirname(_MODULE_DIR), "data")

# ── User-Agent rotation (browser-like) ────────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]

# ── Retry config ──────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2   # exponential: 2s, 4s, 8s

# ── Delay config (anti-detection) ─────────────────────────────
STAGE1_DELAY_MIN = 1.5   # detik antar request stage 1
STAGE1_DELAY_MAX = 3.0
STAGE2_DELAY_MIN = 0.8   # detik antar request stage 2
STAGE2_DELAY_MAX = 2.0


# ══════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════

def _create_session() -> requests.Session:
    """
    Membuat requests.Session dengan headers browser-like.
    Session menjaga persistent cookies dari server (menandakan
    client yang sah, bukan bot sekali pakai).
    """
    session = requests.Session()
    ua = random.choice(_USER_AGENTS)
    session.headers.update({
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    })
    return session


def _request_with_retry(
    session: requests.Session,
    url: str,
    timeout: int = 30,
    max_retries: int = MAX_RETRIES,
) -> requests.Response:
    """
    HTTP GET dengan retry & exponential backoff.
    Melempar exception jika semua retry gagal.
    """
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code == 429:
                # Rate limited — backoff lebih lama
                wait = RETRY_BACKOFF_BASE ** attempt + random.uniform(2, 5)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_exception = e
            if attempt < max_retries:
                wait = RETRY_BACKOFF_BASE ** attempt + random.uniform(0, 1)
                time.sleep(wait)
            continue
        except requests.exceptions.HTTPError:
            raise
    raise last_exception  # type: ignore[misc]


def _progress_info(idx: int, total: int, start_time: float, errors: int) -> Dict[str, Any]:
    """
    Menghitung informasi progress untuk callback.
    Returns dict dengan: percent, elapsed, elapsed_str, eta_str, errors
    """
    elapsed = time.time() - start_time
    pct = (idx / total * 100) if total > 0 else 0
    rate = idx / elapsed if elapsed > 0 else 0
    remaining = (total - idx) / rate if rate > 0 else 0

    def _fmt(seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}d"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}d"
        else:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h}j {m}m"

    return {
        "percent": round(pct, 1),
        "elapsed": elapsed,
        "elapsed_str": _fmt(elapsed),
        "eta_str": _fmt(remaining) if remaining > 0 else "-",
        "errors": errors,
        "rate": round(rate, 2),
    }


# ══════════════════════════════════════════════════════════════
# STAGE 1: PKK LIST
# ══════════════════════════════════════════════════════════════

def scrape_pkk_list(
    port_codes: List[str],
    angkutan: List[str],
    year: int,
    months: List[int],
    progress_callback: Optional[Callable] = None,
    status_callback: Optional[Callable] = None,
    error_callback: Optional[Callable[[str], None]] = None,
    pause_check: Optional[Callable[[], bool]] = None,
    stop_check: Optional[Callable[[], bool]] = None,
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
    progress_callback : callable(info: dict)
        Dipanggil setiap iterasi dengan dict progress info.
    status_callback : callable(message: str)
        Dipanggil untuk update teks status.
    error_callback : callable(message: str), optional
        Dipanggil jika terjadi error/gagal ambil per iterasi.

    Returns
    -------
    pd.DataFrame : kolom [nomor_pkk, nama_kapal, pelabuhan_kode, bulan, angkutan]
    """
    hasil = []
    total_iterations = len(angkutan) * len(port_codes) * len(months)
    current = 0
    error_count = 0
    start_time = time.time()
    session = _create_session()

    for svc in angkutan:
        for port in port_codes:
            for month in months:
                current += 1
                info = _progress_info(current, total_iterations, start_time, error_count)
                if progress_callback:
                    progress_callback(info)
                if status_callback:
                    status_callback(
                        f"[{current}/{total_iterations}] Mengambil PKK list: "
                        f"{port} | {svc.upper()} | Bulan {month:02d}/{year} "
                        f"— {info['elapsed_str']} berlalu, sisa ~{info['eta_str']}"
                    )

                if stop_check and stop_check():
                    break
                while pause_check and pause_check():
                    time.sleep(0.5)

                url = (
                    f"{BASE_URL}/monitoring/byPort/list/"
                    f"{port}/{svc}/{year}/{month:02d}"
                )
                try:
                    r = _request_with_retry(session, url, timeout=30)
                    js = r.json()
                    if not js.get("data"):
                        continue
                    df = pd.DataFrame(js["data"])
                    df["bulan"] = month
                    df["pelabuhan"] = port
                    df["angkutan"] = svc
                    hasil.append(df)
                except requests.exceptions.Timeout:
                    error_count += 1
                    if error_callback:
                        error_callback(f"Timeout: {port} | {svc.upper()} | Bulan {month:02d}/{year}")
                except requests.exceptions.HTTPError as e:
                    error_count += 1
                    if error_callback:
                        error_callback(f"HTTP {e.response.status_code}: {port} | {svc.upper()} | Bulan {month:02d}/{year}")
                except Exception as e:
                    error_count += 1
                    if error_callback:
                        error_callback(f"Error {port} ({svc} M{month:02d}): {str(e)}")

                # Delay antar-request (anti-detection)
                if current < total_iterations:
                    time.sleep(random.uniform(STAGE1_DELAY_MIN, STAGE1_DELAY_MAX))
        
        if stop_check and stop_check():
            break
    
    if stop_check and stop_check():
        if progress_callback:
            progress_callback(_progress_info(current, total_iterations, start_time, error_count))

    # Final progress
    if progress_callback:
        progress_callback(_progress_info(total_iterations, total_iterations, start_time, error_count))

    if not hasil:
        return pd.DataFrame()

    df_all = pd.concat(hasil, ignore_index=True)

    # Pilih kolom yang relevan
    keep_cols = ["nomor_pkk", "nama_kapal", "pelabuhan_kode", "bulan", "angkutan"]
    available = [c for c in keep_cols if c in df_all.columns]
    return df_all[available].drop_duplicates(subset=["nomor_pkk"]).reset_index(drop=True)


# ══════════════════════════════════════════════════════════════
# STAGE 2: APPROVAL TIMES
# ══════════════════════════════════════════════════════════════

def scrape_approval_times(
    df_pkk: pd.DataFrame,
    progress_callback: Optional[Callable] = None,
    status_callback: Optional[Callable] = None,
    error_callback: Optional[Callable[[str], None]] = None,
    pause_check: Optional[Callable[[], bool]] = None,
    stop_check: Optional[Callable[[], bool]] = None,
) -> pd.DataFrame:
    """
    Tahap 2: Mengambil waktu permohonan dan persetujuan untuk setiap nomor PKK.

    Features:
      - Connection pooling via requests.Session
      - Random delay antar-request (0.8–2.0 detik)
      - Retry dengan exponential backoff (max 3 attempt)
      - Progress callback dengan info elapsed, ETA, error count

    Parameters
    ----------
    df_pkk : pd.DataFrame
        DataFrame dengan kolom 'nomor_pkk'.
    progress_callback : callable(info: dict)
        Dipanggil setiap request dengan dict:
        {percent, elapsed_str, eta_str, errors, rate, current, total, pkk_number}
    status_callback : callable(message: str)
    error_callback : callable(message: str), optional

    Returns
    -------
    pd.DataFrame : kolom [nomor_pkk, Layanan, Permohonan, Persetujuan, Nomor Produk]
    """
    approval_list = []
    total = len(df_pkk)
    error_count = 0
    success_count = 0
    start_time = time.time()
    session = _create_session()

    for idx, nomor_pkk in enumerate(df_pkk["nomor_pkk"], start=1):
        info = _progress_info(idx, total, start_time, error_count)
        info["current"] = idx
        info["total"] = total
        info["pkk_number"] = nomor_pkk
        info["success"] = success_count

        if progress_callback:
            progress_callback(info)

        if status_callback and (idx % 10 == 0 or idx == 1 or idx == total):
            status_callback(
                f"[{idx}/{total}] Mengambil approval time: PKK {nomor_pkk} "
                f"— {info['elapsed_str']} berlalu, sisa ~{info['eta_str']} "
                f"— {success_count} berhasil, {error_count} gagal"
            )

        if stop_check and stop_check():
            break
        while pause_check and pause_check():
            time.sleep(0.5)

        url = f"{BASE_URL}/monitoring/detail?nomor_pkk={nomor_pkk}"
        try:
            r = _request_with_retry(session, url, timeout=30)
            dfs = pd.read_html(StringIO(r.text))
            if len(dfs) < 3:
                if error_callback:
                    error_callback(f"Format tabel tidak sesuai untuk PKK {nomor_pkk} (ditemukan {len(dfs)} tabel)")
                error_count += 1
                time.sleep(random.uniform(STAGE2_DELAY_MIN, STAGE2_DELAY_MAX))
                continue
            approval = dfs[2].copy()
            approval.columns = approval.columns.get_level_values(1)
            approval = approval[approval["Layanan"] == "PKK"]
            approval = approval[["Layanan", "Permohonan", "Persetujuan", "Nomor Produk"]].copy()
            approval["nomor_pkk"] = nomor_pkk
            approval_list.append(approval)
            success_count += 1
        except requests.exceptions.Timeout:
            error_count += 1
            if error_callback:
                error_callback(f"Timeout: detail PKK {nomor_pkk}")
        except requests.exceptions.HTTPError as e:
            error_count += 1
            if error_callback:
                error_callback(f"HTTP {e.response.status_code}: detail PKK {nomor_pkk}")
        except Exception as e:
            error_count += 1
            if error_callback:
                error_callback(f"Gagal membaca PKK {nomor_pkk}: {str(e)}")

        # Delay antar-request (anti-detection)
        if idx < total:
            time.sleep(random.uniform(STAGE2_DELAY_MIN, STAGE2_DELAY_MAX))

    # Final progress
    if progress_callback:
        final = _progress_info(total if not (stop_check and stop_check()) else idx, total, start_time, error_count)
        final["current"] = total
        final["total"] = total
        final["success"] = success_count
        progress_callback(final)

    if not approval_list:
        return pd.DataFrame()

    return pd.concat(approval_list, ignore_index=True)


# ══════════════════════════════════════════════════════════════
# PORT REFERENCE & FULL PIPELINE
# ══════════════════════════════════════════════════════════════

def load_port_reference(filepath: str = None) -> pd.DataFrame:
    if filepath is None:
        filepath = os.path.join(_DATA_DIR, "port_code.xlsx")
    elif not os.path.isabs(filepath):
        filepath = os.path.join(_DATA_DIR, os.path.basename(filepath))
    try:
        df = pd.read_excel(filepath)
        return df
    except Exception:
        return pd.DataFrame(columns=["KODE", "PELABUHAN"])


def run_full_scraping(
    port_codes: List[str],
    angkutan: List[str],
    year: int,
    months: List[int],
    port_ref_path: str = None,
    progress_stage1: Optional[Callable] = None,
    status_stage1: Optional[Callable] = None,
    progress_stage2: Optional[Callable] = None,
    status_stage2: Optional[Callable] = None,
    error_callback: Optional[Callable[[str], None]] = None,
    pause_check: Optional[Callable[[], bool]] = None,
    stop_check: Optional[Callable[[], bool]] = None,
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
        error_callback=error_callback,
        pause_check=pause_check,
        stop_check=stop_check,
    )

    if df_pkk.empty:
        return pd.DataFrame()

    # --- Tahap 2: Waktu Approval ---
    approval_df = scrape_approval_times(
        df_pkk=df_pkk,
        progress_callback=progress_stage2,
        status_callback=status_stage2,
        error_callback=error_callback,
        pause_check=pause_check,
        stop_check=stop_check,
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
