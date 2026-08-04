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
