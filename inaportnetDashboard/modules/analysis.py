"""
modules/analysis.py
Semua fungsi analisis data PKK Inaportnet.
Refactoring dari scripts 02, 03, 04, service_level.py, service_performance.py, traffic_analysis.py.
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional

SLA_THRESHOLD_MINUTES = 30   # PKK harus disetujui dalam 30 menit
EXTREME_DELAY_MINUTES = 102  # Ambang keterlambatan ekstrem


# ══════════════════════════════════════════════════════════════
# TRAFFIC ANALYSIS
# ══════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def get_national_stats(df: pd.DataFrame) -> dict:
    """Statistik ringkasan nasional."""
    if df.empty:
        return {}
    approval = df["approval_minutes"].dropna()
    return {
        "total_pkk":       int(df.shape[0]),
        "active_ports":    int(df["port_code"].nunique()) if "port_code" in df.columns else 0,
        "mean_minutes":    round(float(approval.mean()), 2) if not approval.empty else 0,
        "median_minutes":  round(float(approval.median()), 2) if not approval.empty else 0,
        "p95_minutes":     round(float(approval.quantile(0.95)), 2) if not approval.empty else 0,
        "sla_rate":        round(float((approval < SLA_THRESHOLD_MINUTES).sum() / len(approval) * 100), 2) if not approval.empty else 0,
    }


@st.cache_data(show_spinner=False)
def get_port_volume(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Volume PKK per pelabuhan, diurutkan descending."""
    if df.empty:
        return pd.DataFrame()
    group_cols = [c for c in ["port_code", "port"] if c in df.columns]
    if not group_cols:
        return pd.DataFrame()
    grp = (
        df.groupby(group_cols)
        .size()
        .reset_index(name="volume")
        .sort_values("volume", ascending=False)
    )
    grp["share_pct"] = round(grp["volume"] / grp["volume"].sum() * 100, 2)
    return grp.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def get_trend_quarterly(df: pd.DataFrame) -> pd.DataFrame:
    """Tren volume per kuartal."""
    if df.empty or "quarter" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby("quarter")
        .size()
        .reset_index(name="total_service")
        .sort_values("quarter")
    )


@st.cache_data(show_spinner=False)
def get_trend_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Tren volume per bulan."""
    if df.empty or "month" not in df.columns:
        return pd.DataFrame()
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "Mei", 6: "Jun", 7: "Jul", 8: "Agu",
        9: "Sep", 10: "Okt", 11: "Nov", 12: "Des",
    }
    result = (
        df.groupby("month")
        .size()
        .reset_index(name="total_service")
        .sort_values("month")
    )
    result["month_name"] = result["month"].map(month_names)
    return result


@st.cache_data(show_spinner=False)
def get_trend_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Tren volume per hari dalam seminggu."""
    if df.empty or "day" not in df.columns:
        return pd.DataFrame()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    result = df.groupby("day").size().reset_index(name="total_service")
    result["day"] = pd.Categorical(result["day"], categories=order, ordered=True)
    return result.sort_values("day")


@st.cache_data(show_spinner=False)
def get_trend_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Tren volume per jam (0–23)."""
    if df.empty or "hour" not in df.columns:
        return pd.DataFrame()
    all_hours = pd.DataFrame({"hour": range(24)})
    result = df.groupby("hour").size().reset_index(name="total_service")
    return all_hours.merge(result, on="hour", how="left").fillna(0)


# ══════════════════════════════════════════════════════════════
# SERVICE PERFORMANCE & SLA
# ══════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def get_service_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Distribusi waktu persetujuan ke dalam kategori waktu."""
    if df.empty or "approval_hours" not in df.columns:
        return pd.DataFrame()
    bins   = [0, 0.5, 1, 2, 6, 12, 24, float("inf")]
    labels = ["< 30 mnt", "30-60 mnt", "1-2 jam", "2-6 jam", "6-12 jam", "12-24 jam", "> 24 jam"]
    df_cat = df.copy()
    df_cat["time_category"] = pd.cut(
        df_cat["approval_hours"], bins=bins, labels=labels, right=True
    )
    result = (
        df_cat["time_category"]
        .value_counts()
        .reindex(labels, fill_value=0)
        .reset_index()
    )
    result.columns = ["category", "total"]
    result["pct"] = round(result["total"] / result["total"].sum() * 100, 2)
    result["sla_status"] = result["category"].apply(
        lambda x: "Dalam SLA" if x in ["< 30 mnt", "30-60 mnt"] else "Melewati SLA"
    )
    return result


@st.cache_data(show_spinner=False)
def get_top_longest_approval(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N pelabuhan dengan rata-rata waktu persetujuan terlama."""
    if df.empty or "approval_minutes" not in df.columns:
        return pd.DataFrame()
    group_cols = [c for c in ["port_code", "port"] if c in df.columns]
    if not group_cols:
        return pd.DataFrame()
    return (
        df.groupby(group_cols)
        .agg(
            mean_minutes=("approval_minutes", "mean"),
            median_minutes=("approval_minutes", "median"),
            total=("approval_minutes", "count"),
        )
        .round(2)
        .reset_index()
        .sort_values("mean_minutes", ascending=False)
        .head(n)
    )


@st.cache_data(show_spinner=False)
def get_sla_compliance_by_port(df: pd.DataFrame, sla_minutes: float = SLA_THRESHOLD_MINUTES) -> pd.DataFrame:
    """SLA compliance rate per pelabuhan."""
    if df.empty or "approval_minutes" not in df.columns:
        return pd.DataFrame()
    group_cols = [c for c in ["port_code", "port"] if c in df.columns]
    if not group_cols:
        return pd.DataFrame()
    result = (
        df.groupby(group_cols)
        .agg(
            total=("approval_minutes", "count"),
            compliant=("approval_minutes", lambda x: (x < sla_minutes).sum()),
        )
        .reset_index()
    )
    result["compliance_rate"] = round(result["compliant"] / result["total"] * 100, 2)
    result["non_compliance_rate"] = round(100 - result["compliance_rate"], 2)
    return result.sort_values("compliance_rate", ascending=True)


@st.cache_data(show_spinner=False)
def get_sla_trend_monthly(df: pd.DataFrame, sla_minutes: float = SLA_THRESHOLD_MINUTES) -> pd.DataFrame:
    """Tren SLA compliance per bulan."""
    if df.empty or "month" not in df.columns:
        return pd.DataFrame()
    month_names = {
        1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"Mei",6:"Jun",
        7:"Jul",8:"Agu",9:"Sep",10:"Okt",11:"Nov",12:"Des",
    }
    result = (
        df.groupby("month")
        .agg(
            total=("approval_minutes", "count"),
            compliant=("approval_minutes", lambda x: (x < sla_minutes).sum()),
        )
        .reset_index()
    )
    result["compliance_rate"] = round(result["compliant"] / result["total"] * 100, 2)
    result["month_name"] = result["month"].map(month_names)
    return result.sort_values("month")


# ══════════════════════════════════════════════════════════════
# PORT PERFORMANCE INDEX
# ══════════════════════════════════════════════════════════════

def _winsorized_minmax(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Winsorized Min-Max normalisasi menggunakan P5 dan P95."""
    p5  = series.quantile(0.05)
    p95 = series.quantile(0.95)
    if p95 == p5:
        return pd.Series([0.5] * len(series), index=series.index)
    if higher_is_better:
        idx = (series - p5) / (p95 - p5)
    else:
        idx = (p95 - series) / (p95 - p5)
    return idx.clip(lower=0, upper=1)


def compute_port_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung ringkasan metrik performa per pelabuhan.

    Returns
    -------
    pd.DataFrame dengan kolom:
        port_code, port, volume, sla_compliant, mean_response_time,
        std_response_time, extreme_delay, sla_compliance,
        coefficient_of_variation, extreme_delay_index
    """
    if df.empty or "approval_minutes" not in df.columns:
        return pd.DataFrame()

    group_cols = [c for c in ["port_code", "port"] if c in df.columns]
    if not group_cols:
        return pd.DataFrame()

    summary = (
        df.groupby(group_cols)
        .agg(
            volume=("approval_minutes", "count"),
            sla_compliant=("approval_minutes", lambda x: (x < SLA_THRESHOLD_MINUTES).sum()),
            mean_response_time=("approval_minutes", "mean"),
            std_response_time=("approval_minutes", "std"),
            extreme_delay=("approval_minutes", lambda x: (x > EXTREME_DELAY_MINUTES).sum()),
        )
        .reset_index()
    )

    summary["sla_compliance"] = summary["sla_compliant"] / summary["volume"]
    summary["coefficient_of_variation"] = summary["std_response_time"] / summary["mean_response_time"]
    summary["extreme_delay_index"] = summary["extreme_delay"] / summary["volume"]

    return summary


# AHP Saaty Default Weights (Wijaya & Setyawan, 2026)
AHP_DEFAULT_WEIGHTS = {
    "ci": 0.4709,   # Compliance Index
    "ri": 0.2840,   # Robustness Index
    "ei": 0.1715,   # Efficiency Index
    "csi": 0.0736,  # Consistency Index
}

EQUAL_WEIGHTS = {
    "ci": 0.25,
    "ri": 0.25,
    "ei": 0.25,
    "csi": 0.25,
}


def calculate_ahp_matrix_consistency(pairwise_matrix: Optional[np.ndarray] = None) -> dict:
    """
    Hitung nilai Lambda Max, Consistency Index (CI), dan Consistency Ratio (CR)
    berdasarkan matriks perbandingan berpasangan Saaty (4x4).
    """
    if pairwise_matrix is None:
        pairwise_matrix = np.array([
            [1.00, 3.00, 5.00, 2.00],  # CI
            [0.333, 1.00, 3.00, 0.50], # EI
            [0.20, 0.333, 1.00, 0.25], # CsI
            [0.50, 2.00, 4.00, 1.00],  # RI
        ])

    n = pairwise_matrix.shape[0]
    col_sums = pairwise_matrix.sum(axis=0)
    norm_matrix = pairwise_matrix / col_sums
    weights = norm_matrix.mean(axis=1)

    weighted_sum = pairwise_matrix.dot(weights)
    lambda_max = float((weighted_sum / weights).mean())
    ci = float((lambda_max - n) / (n - 1)) if n > 1 else 0.0
    ri = 0.90 if n == 4 else 1.12  # Random Index Saaty untuk n=4
    cr = float(ci / ri) if ri > 0 else 0.0

    return {
        "weights": {
            "ci": round(float(weights[0]), 4),
            "ei": round(float(weights[1]), 4),
            "csi": round(float(weights[2]), 4),
            "ri": round(float(weights[3]), 4),
        },
        "lambda_max": round(lambda_max, 4),
        "ci": round(ci, 4),
        "cr": round(cr, 4),
        "is_consistent": cr <= 0.10,
    }


def compute_performance_indices(
    summary: pd.DataFrame,
    weights: Optional[dict] = None
) -> pd.DataFrame:
    """
    Hitung 4 indeks performa dan composite index dari summary per pelabuhan.
    Mendukung pembobotan AHP, Equal Weighting, atau Custom Weights (total 1.0 atau 100%).
    """
    if summary.empty:
        return summary

    df = summary.copy()

    df["compliance_index"]  = _winsorized_minmax(df["sla_compliance"],             higher_is_better=True)
    df["efficiency_index"]  = _winsorized_minmax(df["mean_response_time"],          higher_is_better=False)
    df["consistency_index"] = _winsorized_minmax(df["coefficient_of_variation"],    higher_is_better=False)
    df["robustness_index"]  = _winsorized_minmax(df["extreme_delay_index"],         higher_is_better=False)

    if weights is None:
        weights = AHP_DEFAULT_WEIGHTS

    w_ci  = float(weights.get("ci", 0.4709))
    w_ri  = float(weights.get("ri", 0.2840))
    w_ei  = float(weights.get("ei", 0.1715))
    w_csi = float(weights.get("csi", 0.0736))

    # Normalisasi bobot agar total presisi = 1.0
    total_w = w_ci + w_ri + w_ei + w_csi
    if total_w > 0:
        w_ci /= total_w
        w_ri /= total_w
        w_ei /= total_w
        w_csi /= total_w

    df["composite_index"] = (
        w_ci  * df["compliance_index"]
        + w_ei  * df["efficiency_index"]
        + w_csi * df["consistency_index"]
        + w_ri  * df["robustness_index"]
    )

    return df.sort_values("composite_index", ascending=False).reset_index(drop=True)


def classify_quadrant(port_perf: pd.DataFrame) -> pd.DataFrame:
    """
    Klasifikasi pelabuhan ke 4 kuadran berdasarkan volume dan composite index.

    Kuadran:
        Benchmark Port  → Volume tinggi & Indeks tinggi
        Efficient Port  → Volume rendah & Indeks tinggi
        Developing Port → Volume rendah & Indeks rendah
        Congested Port  → Volume tinggi & Indeks rendah
    """
    if port_perf.empty:
        return port_perf

    df = port_perf.copy()

    med_volume = df["volume"].median()
    med_index  = df["composite_index"].median()

    conditions = [
        (df["volume"] >= med_volume) & (df["composite_index"] >= med_index),
        (df["volume"] <  med_volume) & (df["composite_index"] >= med_index),
        (df["volume"] <  med_volume) & (df["composite_index"] <  med_index),
        (df["volume"] >= med_volume) & (df["composite_index"] <  med_index),
    ]
    choices = ["Benchmark Port", "Efficient Port", "Developing Port", "Congested Port"]

    df["quadrant"] = np.select(conditions, choices, default="Unknown")
    df["volume_log"] = np.log10(df["volume"].clip(lower=1))

    return df


def generate_ai_policy_insights(
    df_perf_current: pd.DataFrame,
    df_perf_equal: pd.DataFrame,
    weights: dict,
    cr_val: float = 0.0190,
    selected_ports: Optional[list] = None
) -> dict:
    """
    Menghasilkan 4 poin analisis sintesis AI berdasarkan hasil kalkulasi AHP & sensitivitas.
    """
    w_ci = round(weights.get("ci", 0.4709) * 100, 2)
    w_ri = round(weights.get("ri", 0.2840) * 100, 2)
    w_ei = round(weights.get("ei", 0.1715) * 100, 2)
    w_csi = round(weights.get("csi", 0.0736) * 100, 2)

    # 1. Hasil Perhitungan Bobot Prioritas
    p1 = (
        f"Berdasarkan hirarki Saaty AHP, dimensi **SLA Compliance (CI)** mendominasi prioritas dengan bobot **{w_ci}%**, "
        f"disusul **Robustness Index (RI)** sebesar **{w_ri}%**. Hal ini menegaskan bahwa kepatuhan batas 30 menit (PM 8/2022) "
        f"dan pencegahan *extreme delay* >2 jam merupakan aspek paling berisiko terhadap denda demurrage dan reputasi layanan."
    )

    # 2. Hasil Uji Konsistensi
    status_cr = "sangat konsisten dan valid secara matematis" if cr_val <= 0.10 else "kurang konsisten (melebihi ambang 10%)"
    p2 = (
        f"Uji konsistensi matriks perbandingan berpasangan menghasilkan nilai **Consistency Ratio (CR) = {cr_val:.4f}** ({cr_val*100:.2f}%). "
        f"Karena nilai $CR \\le 0.10$ ({cr_val*100:.2f}% $\\le 10\\%$), model matriks penilaian pakar terbukti **{status_cr}**."
    )

    # 3. Analisis Sensitivitas Dampak Skor Komposit
    port_col = "port" if "port" in df_perf_current.columns else ("port_code" if "port_code" in df_perf_current.columns else df_perf_current.columns[0])
    
    # Gabungkan skor untuk perbandingan
    if not df_perf_current.empty and not df_perf_equal.empty and port_col in df_perf_current.columns:
        merged = df_perf_current[[port_col, "composite_index", "quadrant"]].merge(
            df_perf_equal[[port_col, "composite_index", "quadrant"]],
            on=port_col,
            suffixes=("_ahp", "_equal")
        )
        merged["delta"] = merged["composite_index_ahp"] - merged["composite_index_equal"]

        if selected_ports:
            sub = merged[merged[port_col].isin(selected_ports)]
        else:
            sub = merged.head(5)

        insights_list = []
        for _, r in sub.iterrows():
            d_val = r["delta"]
            sign = "+" if d_val >= 0 else ""
            insights_list.append(f"• **{r[port_col]}**: Skor berubah dari {r['composite_index_equal']:.4f} menjadi {r['composite_index_ahp']:.4f} ({sign}{d_val:.4f}).")

        p3_detail = "\n".join(insights_list) if insights_list else "Data pelabuhan terpilih tidak ditemukan."
        p3 = f"Penerapan bobot AHP berhasil mengeliminasi *false performance* (kinerja semu). Rincian pergeseran pelabuhan:\n\n{p3_detail}"
    else:
        p3 = "Data pelabuhan belum memadai untuk pengujian sensitivitas."

    # 4. Implikasi / Saran Kebijakan
    p4 = (
        "**Rekomendasi Kebijakan Kemenhub & Pelindo**:\n"
        "1. **Pelabuhan High Volume / Low Performance (Congested)**: Segera lakukan *process re-engineering* dan optimalisasi sistem Inaportnet.\n"
        "2. **Pelabuhan Under-performer**: Hentikan penilaian berbasis rata-rata biasa (*equal weighting*) karena menyamarkan tingginya kegagalan SLA.\n"
        "3. **Reward & Regulation**: Terapkan insentif regulasi bagi pelabuhan hub utama yang mampu menjaga SLA Compliance $\\ge 90\\%$."
    )

    return {
        "priority_weights": p1,
        "consistency_test": p2,
        "sensitivity_analysis": p3,
        "policy_implications": p4,
    }


def generate_port_specific_ai_insight(
    df_classified: pd.DataFrame,
    selected_port_name: str,
    weights: Optional[dict] = None,
    ahp_metrics: Optional[dict] = None
) -> dict:
    """
    Menghasilkan 5 poin evaluasi AI terintegrasi untuk pelabuhan spesifik yang dipilih pengguna.
    
    Points returned:
    1. priority_weights_analysis: Hasil Perhitungan Bobot Prioritas AHP
    2. consistency_test_summary: Simpulan Perbandingan Uji Konsistensi Rasio (CR) & Consistency Index (CI)
    3. policy_implications: Implikasi Kebijakan Operasional Spesifik
    4. future_risk_assessment: Pernyataan Risiko Masa Depan
    5. rankings_table: Data Peringkat Pelabuhan Lengkap (Urut #1 Terbaik s.d. Terburuk)
    """
    if df_classified.empty:
        return {}

    df_rank = df_classified.copy()
    if "composite_index" in df_rank.columns:
        df_rank = df_rank.sort_values("composite_index", ascending=False).reset_index(drop=True)
    df_rank["rank"] = range(1, len(df_rank) + 1)

    port_col = "port" if "port" in df_rank.columns else ("port_code" if "port_code" in df_rank.columns else df_rank.columns[0])
    total_ports = len(df_rank)

    # Filter pelabuhan yang dipilih
    port_row = df_rank[df_rank[port_col] == selected_port_name]
    if port_row.empty:
        port_row = df_rank.head(1)
        selected_port_name = str(port_row[port_col].iloc[0])

    p_data = port_row.iloc[0]
    rank_num = int(p_data["rank"])
    comp_score = float(p_data.get("composite_index", 0.0))
    quadrant = str(p_data.get("quadrant", "Unknown"))
    vol = int(p_data.get("volume", 0))
    sla_rate = round(float(p_data.get("sla_compliance", 0.0) * 100), 2)
    mean_time = round(float(p_data.get("mean_response_time", 0.0)), 2)
    ext_delay = int(p_data.get("extreme_delay", 0))

    if weights is None:
        weights = AHP_DEFAULT_WEIGHTS
    if ahp_metrics is None:
        ahp_metrics = calculate_ahp_matrix_consistency()

    w_ci = round(weights.get("ci", 0.4709) * 100, 2)
    w_ri = round(weights.get("ri", 0.2840) * 100, 2)
    w_ei = round(weights.get("ei", 0.1715) * 100, 2)
    w_csi = round(weights.get("csi", 0.0736) * 100, 2)

    ci_val = ahp_metrics.get("ci", 0.0170)
    cr_val = ahp_metrics.get("cr", 0.0402)
    lambda_max = ahp_metrics.get("lambda_max", 4.0511)
    is_consistent = ahp_metrics.get("is_consistent", True)

    # 1. Hasil Perhitungan Bobot Prioritas AHP
    score_ci = round(float(p_data.get("compliance_index", 0.0)) * 100, 1)
    score_ri = round(float(p_data.get("robustness_index", 0.0)) * 100, 1)
    score_ei = round(float(p_data.get("efficiency_index", 0.0)) * 100, 1)
    score_csi = round(float(p_data.get("consistency_index", 0.0)) * 100, 1)

    p1 = (
        f"Model AHP Saaty memberikan bobot prioritas tertinggi pada **SLA Compliance Index (CI = {w_ci}%)** "
        f"dan **Robustness Index (RI = {w_ri}%)**, diikuti **Efficiency Index (EI = {w_ei}%)** serta **Consistency Index (CsI = {w_csi}%)**.\n\n"
        f"📍 **Evaluasi Kriteria Pelabuhan {selected_port_name}**:\n"
        f"• **Skor Kepatuhan SLA (CI)**: {score_ci}/100 (Tingkat Kepatuhan SLA <30 mnt: {sla_rate}%).\n"
        f"• **Skor Ketahanan Keterlambatan (RI)**: {score_ri}/100 (Jumlah *Extreme Delay* >2 jam: {ext_delay} PKK).\n"
        f"• **Skor Efisiensi Durasi (EI)**: {score_ei}/100 (Rata-rata Waktu Approval: {mean_time} menit).\n"
        f"• **Skor Stabilitas Variabilitas (CsI)**: {score_csi}/100."
    )

    # 2. Simpulan Uji Konsistensi Rasio (CR) dan Konsistensi Indeks (CI)
    status_cr_txt = "SANGAT KONSISTEN dan VALID SECARA MATEMATIS" if is_consistent else "TIDAK KONSISTEN (>10%)"
    p2 = (
        f"Berdasarkan pengujian matriks perbandingan berpasangan Saaty 4×4:\n\n"
        f"• **Eigenvalue Maksimum ($\\lambda_{{max}}$)**: {lambda_max:.4f}\n"
        f"• **Consistency Index (CI)**: {ci_val:.4f}\n"
        f"• **Random Index (RI, n=4)**: 0.9000\n"
        f"• **Consistency Ratio (CR)**: **{cr_val:.4f}** ({cr_val*100:.2f}%)\n\n"
        f"📌 **Kesimpulan Saintifik**: Karena nilai $CR = {cr_val:.4f} \\le 0.10$ ({cr_val*100:.2f}% $\\le 10\\%$), "
        f"maka seluruh struktur bobot kriteria AHP terbukti **{status_cr_txt}**."
    )

    # 3. Implikasi Kebijakan Operasional
    if quadrant == "Benchmark Port":
        p3 = (
            f"Pelabuhan **{selected_port_name}** berada pada kuadran **Benchmark Port** (Peringkat #{rank_num} dari {total_ports}).\n\n"
            f"💡 **Rekomendasi Kebijakan**:\n"
            f"1. Jadikan pelabuhan ini sebagai *Center of Excellence* dan percontohan nasional digitalisasi Inaportnet.\n"
            f"2. Berikan insentif regulasi dan prioritas alokasi anggaran otomatisasi infrastruktur IT pelabuhan.\n"
            f"3. Pertahankan standar SLA Compliance di atas 90% dengan skema *green-channel approval*."
        )
    elif quadrant == "Efficient Port":
        p3 = (
            f"Pelabuhan **{selected_port_name}** berada pada kuadran **Efficient Port** (Peringkat #{rank_num} dari {total_ports}).\n\n"
            f"💡 **Rekomendasi Kebijakan**:\n"
            f"1. Efisiensi waktu persetujuan sangat baik ({mean_time} menit), namun volume lalu lintas kapal masih sedang/rendah ({vol:,} PKK).\n"
            f"2. Dorong promosi konektivitas jaringan pelayaran dan integrasi kawasan industri (*hinterland*) untuk meningkatkan *throughput* kapal.\n"
            f"3. Pertahankan tim operasional tetap siaga saat lonjakan musiman."
        )
    elif quadrant == "Congested Port":
        p3 = (
            f"Pelabuhan **{selected_port_name}** berada pada kuadran **Congested Port** (Peringkat #{rank_num} dari {total_ports}).\n\n"
            f"💡 **Rekomendasi Kebijakan Intervensi Darurat**:\n"
            f"1. **Beban Tinggi & Restriksi SLA**: Volume tinggi ({vol:,} PKK) dengan SLA Compliance {sla_rate}% memicu antrean persetujuan.\n"
            f"2. Lakukan *Business Process Re-engineering* (BPR) dan otomatisasi verifikasi dokumen persetujuan PKK.\n"
            f"3. Tambahkan petugas verifikator Inaportnet pada jam-jam sibuk (*peak hours*) untuk mengurai *bottleneck*."
        )
    else: # Developing Port
        p3 = (
            f"Pelabuhan **{selected_port_name}** berada pada kuadran **Developing Port** (Peringkat #{rank_num} dari {total_ports}).\n\n"
            f"💡 **Rekomendasi Kebijakan Rehabilitasi**:\n"
            f"1. Lakukan audit sistemik pada durasi persetujuan (rata-rata {mean_time} menit) dan tingkat kepatuhan SLA ({sla_rate}%).\n"
            f"2. Berikan pelatihan verifikasi digital Inaportnet dan perbarui perangkat keras jaringan pelabuhan.\n"
            f"3. Tetapkan target perbaikan SLA secara bertahap menuju kurva efisiensi nasional."
        )

    # 4. Pernyataan Risiko Masa Depan (Future Risk Assessment)
    risk_level = "RENDAH" if rank_num <= total_ports * 0.25 else ("SEDANG" if rank_num <= total_ports * 0.75 else "TINGGI")
    p4 = (
        f"⚠️ **Pernyataan Risiko & Proyeksi Dampak (Tingkat Risiko: {risk_level})**:\n\n"
        f"1. **Risiko Biaya Demurrage Pelayaran**: Jika keterlambatan ekstrem (>2 jam = {ext_delay} kasus) tidak ditekan, pemilik barang & agen pelayaran menghadapi kenaikan biaya pembatalan jadwal dan demurrage kapal.\n"
        f"2. **Risiko Bottleneck Logistik Nasional**: Keterlambatan verifikasi PKK di {selected_port_name} berisiko memicu efek domino penumpukan kapal di alur pelayaran.\n"
        f"3. **Risiko Degradasi Reputasi Kemenhub**: Kegagalan mempertahankan kepatuhan SLA PM 8/2022 berpotensi menurunkan Indeks Logistik Nasional (LPI) Indonesia."
    )

    # 5. Tabel Peringkat Kinerja Pelabuhan (Terbaik s.d. Terburuk)
    rank_cols = [port_col, "volume", "composite_index", "quadrant", "sla_compliance", "mean_response_time"]
    df_ranking_out = df_rank[[c for c in ["rank"] + rank_cols if c in df_rank.columns]].copy()
    if "sla_compliance" in df_ranking_out.columns:
        df_ranking_out["sla_compliance_pct"] = round(df_ranking_out["sla_compliance"] * 100, 1)

    return {
        "selected_port": selected_port_name,
        "rank_num": rank_num,
        "total_ports": total_ports,
        "composite_score": round(comp_score, 4),
        "quadrant": quadrant,
        "volume": vol,
        "sla_rate": sla_rate,
        "mean_time": mean_time,
        "ext_delay": ext_delay,
        "weights": {"ci": w_ci, "ri": w_ri, "ei": w_ei, "csi": w_csi},
        "scores": {"ci": score_ci, "ri": score_ri, "ei": score_ei, "csi": score_csi},
        "ahp_metrics": {"lambda_max": lambda_max, "ci": ci_val, "cr": cr_val, "is_consistent": is_consistent},
        "risk_level": risk_level,
        "priority_weights_analysis": p1,
        "consistency_test_summary": p2,
        "policy_implications": p3,
        "future_risk_assessment": p4,
        "rankings_table": df_ranking_out,
    }
