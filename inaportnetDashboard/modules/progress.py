"""
modules/progress.py
Helper progress bar + info durasi yang dipakai ulang di semua page.

Pola yang didukung:
- Fetch DB deterministik  : make_fetch_progress() -> callback (done, total, phase)
                            untuk fetch_pkk_records(progress_callback=..., chunk_size=...)
- Insert DB deterministik  : make_insert_progress() -> callback (cur, tot)
                            untuk insert_pkk_records(df, progress_callback=...)
- Proses monolit (agregasi pandas, compute_*, ML fit, ekspor file):
                            timed_status() -> context manager spinner + elapsed
                            + ringkasan durasi akhir. Jujur tanpa % palsu.
"""

import time
from contextlib import contextmanager


def fmt_dur(sec: float) -> str:
    """Format detik -> '5 dtk' atau '02:15'."""
    sec = max(0.0, float(sec))
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    if m:
        return f"{m:02d}:{s:02d}"
    return f"{s:d} dtk"


def make_fetch_progress(st, label="📥 Memuat", chunk_note=""):
    """Buat (bar, status, callback, t0, done) untuk fetch DB chunked.

    Contoh:
        bar, status, cb, t0, done = make_fetch_progress(st)
        df = fetch_pkk_records(progress_callback=cb, chunk_size=50000)
        done(len(df), "Database")
    """
    t0 = time.perf_counter()
    bar = st.progress(0, text=f"⏳ {label} — menyiapkan...")
    status = st.empty()

    def _cb(done_n: int, total_n: int, phase: str):
        el = time.perf_counter() - t0
        if phase == "counting" or total_n <= 0:
            bar.progress(0, text=f"🔍 {label} — menghitung total record...")
            status.info(f"🔍 Menghitung total record... • ⏱️ {fmt_dur(el)}")
            return
        pct = min(1.0, done_n / total_n)
        rate = (done_n / el) if el > 0 else 0.0
        eta = ((total_n - done_n) / rate) if rate > 0 else 0.0
        bar.progress(pct, text=f"{label} {pct:.0%} • sisa ~{fmt_dur(eta)}")
        status.info(
            f"{label}: **{done_n:,} / {total_n:,}** record ({pct:.0%})"
            f" • ⏱️ {fmt_dur(el)} • ~{rate:,.0f}/dtk • sisa ~{fmt_dur(eta)}"
            + (f" • {chunk_note}" if chunk_note else "")
        )

    def _done(n: int, source: str = ""):
        dur = time.perf_counter() - t0
        bar.progress(1.0, text="✅ Selesai")
        src = f" dari {source}" if source else ""
        status.success(f"✅ **{n:,} record** dimuat{src} dalam **{fmt_dur(dur)}**.")

    return bar, status, _cb, t0, _done


def make_insert_progress(st, label="💾 Menyimpan", target="Database"):
    """Buat (bar, status, callback, t0, done) untuk insert DB per batch.

    Contoh:
        bar, status, cb, t0, done = make_insert_progress(st)
        res = insert_pkk_records(df, progress_callback=cb)
        done(res["inserted"], target)
    """
    t0 = time.perf_counter()
    bar = st.progress(0, text=f"⏳ {label} — menyiapkan...")
    status = st.empty()

    def _cb(cur: int, tot: int):
        el = time.perf_counter() - t0
        pct = min(1.0, (cur / tot)) if tot > 0 else 0.0
        rate = (cur / el) if el > 0 else 0.0
        eta = ((tot - cur) / rate) if rate > 0 else 0.0
        bar.progress(pct, text=f"{label} {pct:.0%} • sisa ~{fmt_dur(eta)}")
        status.info(
            f"{label} ke **{target}:** {cur:,} / {tot:,} record ({pct:.0%})"
            f" • ⏱️ {fmt_dur(el)} • ~{rate:,.0f}/dtk • sisa ~{fmt_dur(eta)}"
        )

    def _done(n: int, target_name: str = ""):
        dur = time.perf_counter() - t0
        bar.progress(1.0, text="✅ Selesai")
        tgt = target_name or target
        status.success(f"✅ **{n:,} record** tersimpan ke {tgt} dalam **{fmt_dur(dur)}**.")

    return bar, status, _cb, t0, _done


@contextmanager
def timed_status(st, label, done_label=None):
    """Spinner + elapsed untuk proses monolit tanpa callback (agregasi, ML, ekspor).

    Contoh:
        with timed_status(st, "⚙️ Menghitung SLA..."):
            df = get_sla_...(df)
        # otomatis tampil "✅ ... selesai dalam X"

    Mengembalikan dict {"t0": ...} agar durasi bisa dipakai manual bila perlu.
    """
    t0 = time.perf_counter()
    box = st.empty()
    box.info(f"{label} • ⏱️ mulai...")
    info = {"t0": t0}
    try:
        yield info
    finally:
        dur = time.perf_counter() - t0
        msg = done_label or f"{label} selesai"
        box.success(f"{msg} dalam **{fmt_dur(dur)}**.")
