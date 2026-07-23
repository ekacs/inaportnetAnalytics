"""
modules/analysis.py
Semua fungsi analisis data PKK Inaportnet.
Refactoring dari scripts 02, 03, 04, service_level.py, service_performance.py, traffic_analysis.py.
"""

import pandas as pd
import numpy as np
from typing import Optional

SLA_THRESHOLD_MINUTES = 30   # PKK harus disetujui dalam 30 menit
EXTREME_DELAY_MINUTES = 102  # Ambang keterlambatan ekstrem


# ══════════════════════════════════════════════════════════════
# TRAFFIC ANALYSIS
# ══════════════════════════════════════════════════════════════

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


def get_port_volume(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Volume PKK per pelabuhan, diurutkan descending."""
    if df.empty or "port_code" not in df.columns:
        return pd.DataFrame()
    grp = (
        df.groupby(["port_code", "port"])
        .size()
        .reset_index(name="volume")
        .sort_values("volume", ascending=False)
    )
    grp["share_pct"] = round(grp["volume"] / grp["volume"].sum() * 100, 2)
    return grp.reset_index(drop=True)


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


def get_trend_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Tren volume per hari dalam seminggu."""
    if df.empty or "day" not in df.columns:
        return pd.DataFrame()
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    result = df.groupby("day").size().reset_index(name="total_service")
    result["day"] = pd.Categorical(result["day"], categories=order, ordered=True)
    return result.sort_values("day")


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

def get_service_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Distribusi waktu persetujuan ke dalam kategori waktu."""
    if df.empty or "approval_hours" not in df.columns:
        return pd.DataFrame()
    bins   = [0, 0.5, 1, 2, 6, 12, 24, float("inf")]
    labels = ["< 30 mnt", "30-60 mnt", "1-2 jam", "2-6 jam", "6-12 jam", "12-24 jam", "> 24 jam"]
    df = df.copy()
    df["time_category"] = pd.cut(
        df["approval_hours"], bins=bins, labels=labels, right=True
    )
    result = (
        df["time_category"]
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


def get_top_longest_approval(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N pelabuhan dengan rata-rata waktu persetujuan terlama."""
    if df.empty or "port" not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby(["port_code", "port"])
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


def get_sla_compliance_by_port(df: pd.DataFrame, sla_minutes: float = SLA_THRESHOLD_MINUTES) -> pd.DataFrame:
    """SLA compliance rate per pelabuhan."""
    if df.empty:
        return pd.DataFrame()
    result = (
        df.groupby(["port_code", "port"])
        .agg(
            total=("approval_minutes", "count"),
            compliant=("approval_minutes", lambda x: (x < sla_minutes).sum()),
        )
        .reset_index()
    )
    result["compliance_rate"] = round(result["compliant"] / result["total"] * 100, 2)
    result["non_compliance_rate"] = round(100 - result["compliance_rate"], 2)
    return result.sort_values("compliance_rate", ascending=True)


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
    if df.empty:
        return pd.DataFrame()

    summary = (
        df.groupby(["port_code", "port"])
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


def compute_performance_indices(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung 4 indeks performa dan composite index dari summary per pelabuhan.

    Returns
    -------
    pd.DataFrame ditambahkan kolom:
        compliance_index, efficiency_index, consistency_index,
        robustness_index, composite_index
    """
    if summary.empty:
        return summary

    df = summary.copy()

    df["compliance_index"]  = _winsorized_minmax(df["sla_compliance"],             higher_is_better=True)
    df["efficiency_index"]  = _winsorized_minmax(df["mean_response_time"],          higher_is_better=False)
    df["consistency_index"] = _winsorized_minmax(df["coefficient_of_variation"],    higher_is_better=False)
    df["robustness_index"]  = _winsorized_minmax(df["extreme_delay_index"],         higher_is_better=False)

    df["composite_index"] = (
        df["compliance_index"]
        + df["efficiency_index"]
        + df["consistency_index"]
        + df["robustness_index"]
    ) / 4

    return df.sort_values("composite_index", ascending=False).reset_index(drop=True)


def classify_quadrant(port_perf: pd.DataFrame) -> pd.DataFrame:
    """
    Klasifikasi pelabuhan ke 4 kuadran berdasarkan volume dan composite index.

    Kuadran:
        Benchmark Port  → Volume tinggi & Indeks tinggi
        Efficient Port  → Volume rendah & Indeks tinggi
        Developing Port → Volume rendah & Indeks rendah
        Congested Port  → Volume tinggi & Indeks rendah

    Returns
    -------
    pd.DataFrame dengan kolom tambahan:
        quadrant, volume_log
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
