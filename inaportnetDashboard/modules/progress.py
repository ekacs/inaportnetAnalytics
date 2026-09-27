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


def render_load_summary_card(st, load_info: dict) -> None:
    """Render kartu ringkasan estimasi waktu & progres muat data profesional.

    Menggantikan animasi canvas dino yang berat dengan kartu metrik performa tinggi,
    bersih, cepat, dan selaras dengan tema maritim Inaportnet.
    """
    if not load_info:
        return

    dur_total = float(load_info.get("dur_total", 0.0))
    dur_fetch = float(load_info.get("dur_fetch", 0.0))
    dur_prep  = float(load_info.get("dur_prep", 0.0))
    records   = int(load_info.get("records", 0))
    rate      = float(load_info.get("rate", 0.0))
    source    = str(load_info.get("source", "SQLite (Lokal)"))
    year      = str(load_info.get("year", "-"))
    angkutan  = str(load_info.get("angkutan", "-"))
    ports     = load_info.get("ports", ["Semua Pelabuhan"])

    # Format durasi
    def _sec_str(sec: float) -> str:
        if sec < 1.0:
            return f"{sec * 1000:.0f} ms"
        return f"{sec:.2f} dtk"

    if isinstance(ports, list):
        if len(ports) <= 3:
            ports_str = ", ".join(ports)
        else:
            ports_str = f"{ports[0]}, {ports[1]} (+{len(ports)-2} lainnya)"
    else:
        ports_str = str(ports)

    # Performa badge
    if dur_total > 0 and rate >= 50000:
        perf_badge = '<span style="background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0; border-radius:12px; padding:2px 8px; font-size:0.75rem; font-weight:600;">⚡ Kecepatan Tinggi</span>'
    else:
        perf_badge = '<span style="background:#eff6ff; color:#1e40af; border:1px solid #bfdbfe; border-radius:12px; padding:2px 8px; font-size:0.75rem; font-weight:600;">⏱️ Waktu Standar</span>'

    card_html = f"""
<div style="background: white; border: 1px solid #cbd5e1; border-left: 5px solid #0284c7;
            border-radius: 10px; padding: 12px 16px; margin: 0.8rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom: 10px;">
        <div>
            <div style="font-size:0.96rem; font-weight:700; color:#0f172a; display:flex; align-items:center; gap:6px;">
                <span>✅ Data Berhasil Dimuat dari {source}</span>
                {perf_badge}
            </div>
            <div style="font-size:0.8rem; color:#64748b; margin-top:2px;">
                Tahun: <b>{year}</b> • Angkutan: <b>{angkutan}</b> • Pelabuhan: <i>{ports_str}</i>
            </div>
        </div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:4px 10px; text-align:right;">
            <div style="font-size:0.72rem; color:#64748b;">TOTAL RECORD</div>
            <div style="font-size:1.15rem; font-weight:800; color:#0284c7;">{records:,} <span style="font-size:0.75rem; font-weight:400; color:#64748b;">baris</span></div>
        </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px;">
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px; text-align:center;">
            <div style="font-size:0.7rem; color:#64748b; font-weight:600; text-transform:uppercase;">⏱️ Total Waktu</div>
            <div style="font-size:1.1rem; font-weight:700; color:#0f172a; margin-top:2px;">{_sec_str(dur_total)}</div>
        </div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px; text-align:center;">
            <div style="font-size:0.7rem; color:#64748b; font-weight:600; text-transform:uppercase;">📥 Query SQLite</div>
            <div style="font-size:1.1rem; font-weight:700; color:#0284c7; margin-top:2px;">{_sec_str(dur_fetch)}</div>
        </div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px; text-align:center;">
            <div style="font-size:0.7rem; color:#64748b; font-weight:600; text-transform:uppercase;">⚙️ Preprocessing</div>
            <div style="font-size:1.1rem; font-weight:700; color:#059669; margin-top:2px;">{_sec_str(dur_prep)}</div>
        </div>
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px; text-align:center;">
            <div style="font-size:0.7rem; color:#64748b; font-weight:600; text-transform:uppercase;">⚡ Throughput</div>
            <div style="font-size:1.1rem; font-weight:700; color:#7c3aed; margin-top:2px;">~{rate:,.0f} <span style="font-size:0.7rem; font-weight:400;">/dtk</span></div>
        </div>
    </div>
</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)

