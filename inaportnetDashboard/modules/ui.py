"""
modules/ui.py
Komponen UI bersama untuk seluruh halaman dashboard.

Tujuan modul ini: logoutik tampilan yang sebelumnya di-copy-paste di setiap
file pages/*.py. Semua halaman sekarang memanggil fungsi yang sama, sehingga
perubahan visual cukup dilakukan di satu tempat dan tidak bisa lagi
menyimpang antar halaman.
"""

import pandas as pd
import streamlit as st

# ── Palet & tipografi ─────────────────────────────────────────
# Dipakai bersama oleh CSS dan komponen KPI supaya warna di CSS dan
# warna yang benar-benar dirender tidak pernah berbeda.
BRAND_DARK = "#1a4a7a"
BRAND_MID = "#2471a3"
BORDER_LIGHT = "#e2e8f0"
CARD_BORDER = "#e8ecf0"
FONT_STACK = "'Inter', sans-serif"

# ── Definisi navigasi ─────────────────────────────────────────
# Satu daftar = satu sidebar. Tambah halaman baru cukup di sini.
NAV_ITEMS = [
    ("app.py", "🏠 Beranda"),
    ("pages/1_📊_Data_Collection.py", "📊 Data Collection"),
    ("pages/2_🗄️_Database_Viewer.py", "🗄️ Database Viewer"),
    ("pages/3_🚦_Traffic_Overview.py", "🚦 Traffic Overview"),
    ("pages/4_📋_Service_Performance.py", "📋 Service Performance"),
    ("pages/5_🗺️_Port_Classification.py", "🗺️ Port Classification"),
    ("pages/6_🛡️_Fraud_Risk_Screening.py", "🛡️ Fraud Risk Screening"),
]

# Halaman yang sengaja disembunyikan dari navigasi (masih bisa dibuka via URL).
NAV_HIDDEN = {"pages/2_🗄️_Database_Viewer.py"}


def page_css(extra: str = "") -> None:
    """
    CSS global halaman: tipografi, kartu KPI, judul seksi, sembunyikan footer.

    extra
        Blok CSS khas halaman yang hanya dipakai satu halaman (mis. hero
        CFRSI). CSS global tetap sama untuk semua halaman, jadi halaman
        yang butuh gaya sendiri cukup mengoperatkannya di sini.
    """
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: {FONT_STACK}; }}
.kpi-card {{ background: linear-gradient(135deg, {BRAND_DARK}, {BRAND_MID});
            color: white; border-radius: 14px; padding: 1.2rem 1rem;
            text-align: center; box-shadow: 0 4px 16px rgba(26,74,122,0.18); }}
.val      {{ font-size: 2rem; font-weight: 700; }}
.label    {{ font-size: 0.82rem; opacity: 0.85; margin-top: 3px; }}
.section-title   {{ font-size: 1.1rem; font-weight: 600; color: {BRAND_DARK};
                    margin: 1.5rem 0 0.5rem; border-bottom: 2px solid {BORDER_LIGHT};
                    padding-bottom: 6px; }}
.chart-card      {{ background: white; border-radius: 14px; padding: 1.2rem;
                    border: 1px solid {CARD_BORDER};
                    box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 1rem; }}

/* KPI status (halaman Service Performance). `.val`/`.label` di atas sengaja
   tidak di-scope ke .kpi-card supaya kartu status memakainya juga. */
.kpi-ok   {{ background: linear-gradient(135deg,#1e8449,#27ae60); color:white;
            border-radius:14px; padding:1.2rem 1rem; text-align:center;
            box-shadow:0 4px 16px rgba(30,132,73,.18); }}
.kpi-warn {{ background: linear-gradient(135deg,#b7770d,#f39c12); color:white;
            border-radius:14px; padding:1.2rem 1rem; text-align:center;
            box-shadow:0 4px 16px rgba(183,119,13,.18); }}
.kpi-bad  {{ background: linear-gradient(135deg,#922b21,#e74c3c); color:white;
            border-radius:14px; padding:1.2rem 1rem; text-align:center;
            box-shadow:0 4px 16px rgba(146,43,33,.18); }}
.kpi-neu  {{ background: linear-gradient(135deg,{BRAND_DARK},{BRAND_MID}); color:white;
            border-radius:14px; padding:1.2rem 1rem; text-align:center;
            box-shadow:0 4px 16px rgba(26,74,122,.18); }}

/* Kuadran pelabuhan (halaman Port Classification). */
.quadrant-pill {{ display:inline-block; border-radius:20px; padding:3px 12px;
                 font-size:0.8rem; font-weight:600; margin:2px; }}
.q-benchmark {{ background:#d4efdf; color:#1e8449; }}
.q-efficient {{ background:#d6eaf8; color:#1a5276; }}
.q-developing{{ background:#fdebd0; color:#784212; }}
.q-congested {{ background:#fadbd8; color:#922b21; }}
.legend-box  {{ background:#f8fafc; border:1px solid {BORDER_LIGHT};
                border-radius:10px; padding:1rem; font-size:0.88rem; }}

footer{{visibility:hidden;}} #MainMenu{{visibility:hidden;}}
[data-testid="stSidebarNav"]{{display:none !important;}}
{extra}
</style>
""",
        unsafe_allow_html=True,
    )


def render_sidebar_nav(footer: str = "") -> None:
    """
    Sidebar dengan judul aplikasi dan tautan navigasi ke semua halaman.

    footer
        Markdown opsional yang dicetak di bawah daftar navigasi, mis. blok
        kredit metodologi di halaman CFRSI. Nav link-nya sendiri tetap
        berasal dari NAV_ITEMS supaya tidak ada dua sumber kebenaran.
    """
    with st.sidebar:
        st.markdown("### 🚢 Inaportnet Analytics")
        st.markdown("---")
        st.markdown("**Navigasi**")
        for path, label in NAV_ITEMS:
            if path in NAV_HIDDEN:
                continue
            st.page_link(path, label=label)
        st.markdown("---")
        if footer:
            st.markdown(footer)


def arrow_safe_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renses DataFrame supaya pasti bisa diserialisasi Arrow oleh st.dataframe.

    Kolom ``object`` yang isinya campuran tipe (mis. sebagian int, sebagian
    str) tidak punya satu representasi Arrow yang valid, sehingga
    st.dataframe melempar ArrowTypeError. Mengubah kolom seperti itu menjadi
    string menutup kelas bug ini secara umum, bukan hanya untuk kasus kolom
    tanpa header.
    """
    for col in df.columns:
        if df[col].dtype != object:
            continue
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        if not all(isinstance(v, (str, bytes)) for v in non_null):
            df[col] = df[col].map(
                lambda v: v if isinstance(v, (str, bytes)) or pd.isna(v) else str(v)
            )
    return df


def show_df(df: pd.DataFrame, **kwargs) -> None:
    """st.dataframe dengan sanitasi Arrow otomatis."""
    st.dataframe(arrow_safe_df(df), **kwargs)


def kpi_card(value: str, label: str) -> None:
    """Kartu KPI dengan gradient brand (HTML statis, tanpa input pengguna)."""
    st.markdown(
        f'<div class="kpi-card"><div class="val">{value}</div>'
        f'<div class="label">{label}</div></div>',
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    """Judul seksi dengan garis bawah, konsisten antar halaman."""
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def load_session_df(
    key: str = "df",
    port_key: str = "ui_port_filter",
    angkutan_key: str = "ui_angkutan_filter",
    chunk_size: int = 50_000,
) -> pd.DataFrame:
    """
    Ambil DataFrame analisis dari session, dengan auto-load dari SQLite bila
    session masih kosong.

    Fungsi ini menggantikan blok auto-load yang sebelumnya di-copy-paste di
    4 halaman. Bedanya: error tidak lagi ditelan diam-diam, melainkan
    dilaporkan ke user lewat st.warning supaya DB yang rusak/path salah
    tidak terlihat identik dengan "belum ada data".

    Returns
    -------
    pandas.DataFrame
        DataFrame siap analisis; kosong bila tidak ada data.
    """
    df = st.session_state.get(key)
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df

    try:
        from modules.database import fetch_pkk_records
        from modules.preprocessing import preprocess
        from modules.progress import timed_status

        with timed_status(st, "Memuat data dari database..."):
            raw = fetch_pkk_records(chunk_size=chunk_size)
            df = preprocess(raw) if not raw.empty else raw
    except Exception as exc:  # noqa: BLE001 - sengaja dilaporkan, bukan ditelan
        st.warning(
            f"⚠️ Gagal memuat data dari database: `{type(exc).__name__}: {exc}`. "
            "Silakan muat data manual di halaman **📊 Data Collection**."
        )
        return pd.DataFrame()

    if not df.empty:
        st.session_state[key] = df
    return df


def render_data_filters(
    df: pd.DataFrame,
    port_key: str,
    angkutan_key: str,
    extra_widgets=None,
) -> tuple[list, list]:
    """
    Widget filter Pelabuhan + Angkutan di sidebar, dan status database.

    Mengembalikan (selected_ports, selected_angkutan, extra_values).
    Widget key dibuat unik per halaman lewat parameter, jadi state tiap
    halaman terpisah.

    extra_widgets
        Dict berisi widget khas halaman, misal
        ``{"sla_threshold": lambda: st.slider(...)}``. Dipanggil di dalam
        `with st.sidebar:` sehingga tidak perlu st.sidebar di tiap call
        site. Nilai kembalinya dikembalikan lewat extra_values supaya
        halaman bisa membacanya seperti variabel biasa.
    """
    with st.sidebar:
        if not df.empty and "port" in df.columns:
            if "_cache_all_ports" not in st.session_state or st.session_state.get("_cache_ports_len") != len(df):
                st.session_state["_cache_all_ports"] = sorted(df["port"].dropna().unique().tolist())
                st.session_state["_cache_ports_len"] = len(df)
            all_ports = st.session_state["_cache_all_ports"]
            selected_ports = st.multiselect(
                "🏗️ Filter Pelabuhan",
                options=all_ports,
                placeholder="Semua pelabuhan",
                key=port_key,
            )
        else:
            selected_ports = []

        if not df.empty and "angkutan" in df.columns:
            if "_cache_all_ang" not in st.session_state or st.session_state.get("_cache_ang_len") != len(df):
                st.session_state["_cache_all_ang"] = sorted(df["angkutan"].dropna().unique().tolist())
                st.session_state["_cache_ang_len"] = len(df)
            angkutan_options = st.session_state["_cache_all_ang"]
            selected_angkutan = st.multiselect(
                "🚢 Filter Angkutan",
                options=angkutan_options,
                placeholder="Semua",
                key=angkutan_key,
            )
        else:
            selected_angkutan = []

        st.markdown("---")
        from modules.database import get_db_status_info

        db_info = get_db_status_info()
        st.markdown("**Status Database**")
        st.success(f"{db_info.get('label', '—')}")
        if isinstance(df, pd.DataFrame) and not df.empty:
            st.success(f"✅ {len(df):,} record")

        # Widget khas halaman. Dipanggil di dalam `with st.sidebar:`, jadi
        # cukup `lambda: st.slider(...)` tanpa st.sidebar lagi.
        #
        # PENTING: hasilnya dikembalikan lewat dict, TIDAK ditulis ke
        # st.session_state. Streamlit melempar StreamlitAPIException kalau
        # session_state sebuah key diubah setelah widget-nya diinstansiasi.
        extra_values = {}
        if extra_widgets:
            st.markdown("---")
            for name, fn in extra_widgets.items():
                extra_values[name] = fn()

    return selected_ports, selected_angkutan, extra_values
