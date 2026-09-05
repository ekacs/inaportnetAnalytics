"""
modules/analysis.py
Semua fungsi analisis data PKK Inaportnet.
Refactoring dari scripts 02, 03, 04, service_level.py, service_performance.py, traffic_analysis.py.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

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


# ══════════════════════════════════════════════════════════════
# COMPOSITE FRAUD RISK SCREENING INDEX (CFRSI) ENGINE
# ══════════════════════════════════════════════════════════════

def _minmax_scale_port(series: pd.Series, low: float = 0.10, high: float = 1.00) -> pd.Series:
    """Min-Max scaling ke rentang [low, high]."""
    s_min = series.min()
    s_max = series.max()
    if s_max == s_min:
        return pd.Series((low + high) / 2.0, index=series.index)
    normalized = (series - s_min) / (s_max - s_min)
    return low + normalized * (high - low)


def compute_fraud_risk_analysis(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Hitung deteksi anomali 3 lapis dan Composite Fraud Risk Screening Index (CFRSI).

    Metodologi (Wijaya & Setyawan, 2026):
    1. Rule-Based Engine (5 Red Flag criteria)
    2. Statistical Engine (OLS Residuals & Modified Z-Score <= -2.5)
    3. Unsupervised ML Engine (Isolation Forest, contamination=0.07)
    4. Min-Max normalization ke [0.10, 1.00] & equal weighting
    5. Klasifikasi 5 Tier Risiko (Percentile vs Fixed Scale)

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]:
        - df_analyzed: DataFrame tingkat transaksi dengan kolom flag anomali
        - cfrsi_df: DataFrame tingkat pelabuhan dengan skor CFRSI dan kategori risiko
    """
    if df.empty or "approval_minutes" not in df.columns:
        return df, pd.DataFrame()

    data = df.copy()

    # Ekstraksi jam jika belum ada
    if "hour" not in data.columns and "submission_time" in data.columns:
        try:
            data["hour"] = pd.to_datetime(data["submission_time"]).dt.hour
        except Exception:
            data["hour"] = 12

    # 1. RULE-BASED ANOMALY DETECTION (5 Red Flags)
    # R1: Quick Approval (< 10 detik)
    data["rf_quick_approval"] = data["approval_minutes"] < (10.0 / 60.0)

    # R2: Long Duration (> 8 jam / 480 menit)
    data["rf_long_duration"] = data["approval_minutes"] > 480.0

    # R3: Low Oversight (00.00 - 04.00)
    data["rf_low_oversight"] = data["hour"].isin([0, 1, 2, 3]) if "hour" in data.columns else False

    # R4: GT Manipulation
    if "gt_flag" in data.columns:
        data["rf_gt_manipulation"] = data["gt_flag"].astype(bool)
    elif "gt" in data.columns and "vessel_name" in data.columns:
        gt_std = data.groupby("vessel_name")["gt"].transform("std").fillna(0)
        data["rf_gt_manipulation"] = gt_std > 0.15 * data["gt"]
    else:
        data["rf_gt_manipulation"] = False

    # R5: Same Vessel in 2 Ports (< 2 jam / 120 menit)
    if "vessel_name" in data.columns and "submission_time" in data.columns and "port_code" in data.columns:
        try:
            data["sub_dt"] = pd.to_datetime(data["submission_time"])
            data = data.sort_values(["vessel_name", "sub_dt"])
            data["prev_vessel"] = data["vessel_name"].shift(1)
            data["prev_port"] = data["port_code"].shift(1)
            data["prev_time"] = data["sub_dt"].shift(1)

            time_diff = (data["sub_dt"] - data["prev_time"]).dt.total_seconds() / 60.0
            same_vessel_diff_port = (
                (data["vessel_name"] == data["prev_vessel"]) &
                (data["port_code"] != data["prev_port"]) &
                (time_diff < 120.0) &
                (time_diff >= 0)
            )
            data["rf_same_vessel_2ports"] = same_vessel_diff_port.fillna(False)
            data.drop(columns=["sub_dt", "prev_vessel", "prev_port", "prev_time"], errors="ignore", inplace=True)
        except Exception:
            data["rf_same_vessel_2ports"] = False
    else:
        data["rf_same_vessel_2ports"] = False

    # Total Red Flags
    data["red_flag_count"] = (
        data["rf_quick_approval"].astype(int) +
        data["rf_long_duration"].astype(int) +
        data["rf_low_oversight"].astype(int) +
        data["rf_gt_manipulation"].astype(int) +
        data["rf_same_vessel_2ports"].astype(int)
    )
    data["is_red_flag"] = data["red_flag_count"] > 0

    # 2. STATISTICAL OUTLIER DETECTION (OLS Residuals & Modified Z-Score)
    data["log_approval"] = np.log1p(data["approval_minutes"].clip(lower=0))
    if "port_code" in data.columns:
        port_vol = data.groupby("port_code").transform("size")
        data["port_daily_vol"] = port_vol
    else:
        data["port_daily_vol"] = 100

    gt_series = data["gt"] if "gt" in data.columns else pd.Series(1000, index=data.index)
    gt_cat = pd.qcut(gt_series.rank(method="first"), q=4, labels=["Q1", "Q2", "Q3", "Q4"])

    X = pd.DataFrame({
        "const": 1.0,
        "daily_vol": data["port_daily_vol"].fillna(100),
        "gt_Q2": (gt_cat == "Q2").astype(int),
        "gt_Q3": (gt_cat == "Q3").astype(int),
        "gt_Q4": (gt_cat == "Q4").astype(int),
    }, index=data.index)

    if "day" in data.columns:
        day_dummies = pd.get_dummies(data["day"], prefix="day", drop_first=True)
        X = pd.concat([X, day_dummies], axis=1)

    y = data["log_approval"]
    try:
        model = LinearRegression().fit(X.astype(float), y)
        residuals = y - model.predict(X.astype(float))
    except Exception:
        residuals = y - y.median()

    med_res = np.median(residuals)
    mad = np.median(np.abs(residuals - med_res))
    if mad == 0:
        mad = 1e-6
    mod_z = 0.6745 * (residuals - med_res) / mad
    data["mod_zscore"] = mod_z
    data["is_stat_anomaly"] = data["mod_zscore"] <= -2.5

    # 3. MACHINE LEARNING ANOMALY DETECTION (Isolation Forest)
    features = ["log_approval"]
    if "gt" in data.columns:
        data["feature_gt"] = np.log1p(data["gt"].clip(lower=1))
        features.append("feature_gt")
    if "port_daily_vol" in data.columns:
        data["feature_vol"] = np.log1p(data["port_daily_vol"].clip(lower=1))
        features.append("feature_vol")
    if "hour" in data.columns:
        features.append("hour")

    X_mat = data[features].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_mat)

    try:
        if_model = IsolationForest(
            n_estimators=100,
            max_samples=min(256, len(data)),
            max_features=1.0,
            contamination=0.07,
            random_state=42,
            n_jobs=-1
        )
        preds = if_model.fit_predict(X_scaled)
        scores = if_model.decision_function(X_scaled)
        data["if_score"] = scores
        data["is_ml_anomaly"] = preds == -1
    except Exception:
        data["if_score"] = 0.0
        data["is_ml_anomaly"] = False

    # 4. AGGREGATION LEVEL PELABUHAN & SKOR CFRSI
    group_cols = [c for c in ["port_code", "port"] if c in data.columns]
    if not group_cols:
        return data, pd.DataFrame()

    port_summary = data.groupby(group_cols).agg(
        volume=("approval_minutes", "count"),
        rf_quick=("rf_quick_approval", "sum"),
        rf_long=("rf_long_duration", "sum"),
        rf_low_oversight=("rf_low_oversight", "sum"),
        rf_gt=("rf_gt_manipulation", "sum"),
        rf_same_vessel=("rf_same_vessel_2ports", "sum"),
        total_red_flags=("is_red_flag", "sum"),
        stat_anomalies=("is_stat_anomaly", "sum"),
        ml_anomalies=("is_ml_anomaly", "sum"),
        mean_mod_zscore=("mod_zscore", "mean"),
        mean_if_score=("if_score", "mean"),
    ).reset_index()

    port_summary["rf_ratio"] = port_summary["total_red_flags"] / port_summary["volume"]
    port_summary["stat_ratio"] = port_summary["stat_anomalies"] / port_summary["volume"]
    port_summary["ml_ratio"] = port_summary["ml_anomalies"] / port_summary["volume"]
    port_summary["red_flag_pct"] = round(port_summary["rf_ratio"] * 100, 2)

    # Sub-indeks normalisasi [0.10 - 1.00]
    port_summary["rule_based_index"] = _minmax_scale_port(port_summary["rf_ratio"])
    port_summary["statistical_index"] = _minmax_scale_port(port_summary["stat_ratio"])
    port_summary["ml_index"] = _minmax_scale_port(port_summary["ml_ratio"])

    # Composite Fraud Risk Screening Index (CFRSI)
    port_summary["cfrsi"] = (
        port_summary["rule_based_index"] +
        port_summary["statistical_index"] +
        port_summary["ml_index"]
    ) / 3.0

    # 5. KLASIFIKASI KATEGORI RISIKO
    labels_5 = ["Sangat Rendah", "Rendah", "Sedang", "Tinggi", "Sangat Tinggi"]

    # Percentile-based (Quintiles)
    try:
        port_summary["risk_tier_percentile"] = pd.qcut(
            port_summary["cfrsi"].rank(method="first"),
            q=5,
            labels=labels_5
        )
    except Exception:
        port_summary["risk_tier_percentile"] = "Sedang"

    # Fixed-scale approach (0.10-0.28, 0.28-0.46, 0.46-0.64, 0.64-0.82, 0.82-1.00)
    fixed_bins = [0.0, 0.28, 0.46, 0.64, 0.82, 1.01]
    port_summary["risk_tier_fixed"] = pd.cut(
        port_summary["cfrsi"],
        bins=fixed_bins,
        labels=labels_5,
        right=False
    )

    return data, port_summary.sort_values("cfrsi", ascending=False).reset_index(drop=True)


def get_fraud_national_summary(df_analyzed: pd.DataFrame, cfrsi_df: pd.DataFrame) -> dict:
    """Statistik ringkasan nasional analisis risiko fraud."""
    if df_analyzed.empty or cfrsi_df.empty:
        return {}

    total_pkk = len(df_analyzed)
    red_flag_pkk = int(df_analyzed["is_red_flag"].sum()) if "is_red_flag" in df_analyzed.columns else 0
    stat_pkk = int(df_analyzed["is_stat_anomaly"].sum()) if "is_stat_anomaly" in df_analyzed.columns else 0
    ml_pkk = int(df_analyzed["is_ml_anomaly"].sum()) if "is_ml_anomaly" in df_analyzed.columns else 0

    high_risk_ports = int((cfrsi_df["risk_tier_fixed"].isin(["Tinggi", "Sangat Tinggi"])).sum()) if "risk_tier_fixed" in cfrsi_df.columns else 0
    mean_cfrsi = float(cfrsi_df["cfrsi"].mean()) if "cfrsi" in cfrsi_df.columns else 0.0

    return {
        "total_pkk": total_pkk,
        "red_flag_pkk": red_flag_pkk,
        "red_flag_pct": round(red_flag_pkk / total_pkk * 100, 2) if total_pkk > 0 else 0.0,
        "stat_pkk": stat_pkk,
        "stat_pct": round(stat_pkk / total_pkk * 100, 2) if total_pkk > 0 else 0.0,
        "ml_pkk": ml_pkk,
        "ml_pct": round(ml_pkk / total_pkk * 100, 2) if total_pkk > 0 else 0.0,
        "high_risk_ports": high_risk_ports,
        "mean_cfrsi": round(mean_cfrsi, 3),
        "total_ports": len(cfrsi_df),
    }
