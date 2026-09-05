"""
scripts/05_fraud_risk_analysis.py
==================================
Analisis Deteksi Anomali & Perhitungan Composite Fraud Risk Screening Index (CFRSI)
Berdasarkan paper: "Toward Data-Driven Anti-Fraud Governance: Anomaly Detection and
Composite Risk Scoring for Port-Level Oversight in Digital Maritime Services"
(Wijaya & Setyawan, 2026).

Metodologi Integrasi 3 Pendekatan:
1. Rule-Based Anomaly Engine (5 Indikator Red Flag)
2. Statistical Outlier Engine (OLS Regression Residuals & Modified Z-Score)
3. Unsupervised Machine Learning Engine (Isolation Forest)
4. Normalisasi Min-Max [0.10 - 1.00] & Equal-Weighting CFRSI
5. Klasifikasi Risiko 5-Tingkat (Percentile vs Fixed Scale)
"""

import os
import sys
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

# Ambang batas sesuai riset paper
RULE_QUICK_APPROVAL_SEC = 10        # < 10 detik
RULE_LONG_DURATION_HOURS = 8        # > 8 jam (480 menit)
RULE_LOW_OVERSIGHT_HOURS = [0, 1, 2, 3] # 00.00 - 04.00
RULE_SAME_VESSEL_WINDOW_MIN = 120   # < 2 jam lintas 2 pelabuhan
MODIFIED_Z_THRESHOLD = -2.5         # Ambang ekstrim Z-score
IF_CONTAMINATION = 0.07             # 7% kontaminasi anomali
IF_RANDOM_STATE = 42


def run_rule_based_detection(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menjalankan deteksi anomali berbasis aturan bisnis (5 Kriteria Red Flag).
    """
    data = df.copy()
    if "approval_minutes" not in data.columns:
        return data

    # 1. Quick Approval (< 10 detik = 10/60 menit)
    data["rf_quick_approval"] = data["approval_minutes"] < (RULE_QUICK_APPROVAL_SEC / 60.0)

    # 2. Long Duration (> 8 jam = 480 menit)
    data["rf_long_duration"] = data["approval_minutes"] > (RULE_LONG_DURATION_HOURS * 60.0)

    # 3. Low Oversight (00.00 - 04.00)
    data["rf_low_oversight"] = data["hour"].isin(RULE_LOW_OVERSIGHT_HOURS) if "hour" in data.columns else False

    # 4. GT Manipulation (Discrepancy GT flag / perubahan abnormal GT)
    if "gt_flag" in data.columns:
        data["rf_gt_manipulation"] = data["gt_flag"].astype(bool)
    elif "gt" in data.columns and "vessel_name" in data.columns:
        # Deteksi variasi GT untuk kapal yang sama
        gt_std = data.groupby("vessel_name")["gt"].transform("std").fillna(0)
        data["rf_gt_manipulation"] = gt_std > 0.15 * data["gt"]
    else:
        data["rf_gt_manipulation"] = False

    # 5. Same Vessel in 2 Ports (< 2 jam)
    if "vessel_name" in data.columns and "submission_time" in data.columns and "port_code" in data.columns:
        data = data.sort_values(["vessel_name", "submission_time"])
        data["prev_vessel"] = data["vessel_name"].shift(1)
        data["prev_port"] = data["port_code"].shift(1)
        data["prev_time"] = data["submission_time"].shift(1)
        
        time_diff_min = (data["submission_time"] - data["prev_time"]).dt.total_seconds() / 60.0
        same_vessel_diff_port = (
            (data["vessel_name"] == data["prev_vessel"]) &
            (data["port_code"] != data["prev_port"]) &
            (time_diff_min < RULE_SAME_VESSEL_WINDOW_MIN) &
            (time_diff_min >= 0)
        )
        data["rf_same_vessel_2ports"] = same_vessel_diff_port.fillna(False)
        data.drop(columns=["prev_vessel", "prev_port", "prev_time"], errors="ignore", inplace=True)
    else:
        data["rf_same_vessel_2ports"] = False

    # Total Red Flags per transaksi
    data["red_flag_count"] = (
        data["rf_quick_approval"].astype(int) +
        data["rf_long_duration"].astype(int) +
        data["rf_low_oversight"].astype(int) +
        data["rf_gt_manipulation"].astype(int) +
        data["rf_same_vessel_2ports"].astype(int)
    )
    data["is_red_flag"] = data["red_flag_count"] > 0
    return data


def run_statistical_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menjalankan Model Regresi OLS & Perhitungan Modified Z-Score dari Residual.
    """
    data = df.copy()
    if "approval_minutes" not in data.columns or data.empty:
        data["mod_zscore"] = 0.0
        data["is_stat_anomaly"] = False
        return data

    data["log_approval"] = np.log1p(data["approval_minutes"].clip(lower=0))
    
    # Hitung volume harian pelabuhan
    if "port_code" in data.columns and "date" in data.columns:
        daily_vol = data.groupby(["port_code", "date"]).size().reset_index(name="daily_vol")
        data = data.merge(daily_vol, on=["port_code", "date"], how="left")
    else:
        data["daily_vol"] = 100

    # Siapkan predictor OLS
    gt_val = data["gt"] if "gt" in data.columns else pd.Series(1000, index=data.index)
    gt_cat = pd.qcut(gt_val.rank(method="first"), q=4, labels=["Q1", "Q2", "Q3", "Q4"])
    
    X = pd.DataFrame({
        "const": 1.0,
        "daily_vol": data["daily_vol"].fillna(data["daily_vol"].median()),
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
        preds = model.predict(X.astype(float))
        residuals = y - preds
    except Exception:
        residuals = y - y.median()

    # Perhitungan Modified Z-Score berdasarkan Median Absolute Deviation (MAD)
    med_res = np.median(residuals)
    mad = np.median(np.abs(residuals - med_res))
    if mad == 0:
        mad = 1e-6

    mod_z = 0.6745 * (residuals - med_res) / mad
    data["mod_zscore"] = mod_z
    data["is_stat_anomaly"] = data["mod_zscore"] <= MODIFIED_Z_THRESHOLD
    return data


def run_isolation_forest(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menjalankan algoritma Isolation Forest untuk deteksi anomali multidimensi.
    """
    data = df.copy()
    if data.empty or "approval_minutes" not in data.columns:
        data["if_score"] = 0.0
        data["is_ml_anomaly"] = False
        return data

    features = []
    data["feature_app_min"] = np.log1p(data["approval_minutes"].clip(lower=0))
    features.append("feature_app_min")

    if "gt" in data.columns:
        data["feature_gt"] = np.log1p(data["gt"].clip(lower=1))
        features.append("feature_gt")

    if "daily_vol" in data.columns:
        data["feature_vol"] = np.log1p(data["daily_vol"].clip(lower=1))
        features.append("feature_vol")

    if "hour" in data.columns:
        features.append("hour")

    X_mat = data[features].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_mat)

    model = IsolationForest(
        n_estimators=100,
        max_samples=min(256, len(data)),
        max_features=1.0,
        contamination=IF_CONTAMINATION,
        random_state=IF_RANDOM_STATE,
        n_jobs=-1
    )
    
    preds = model.fit_predict(X_scaled)
    scores = model.decision_function(X_scaled)  # makin negatif = makin anomali

    data["if_score"] = scores
    data["is_ml_anomaly"] = preds == -1
    return data


def minmax_scale_port(series: pd.Series, low: float = 0.10, high: float = 1.00) -> pd.Series:
    """
    Mengubah nilai ke rentang [low, high] Min-Max scaling.
    """
    s_min = series.min()
    s_max = series.max()
    if s_max == s_min:
        return pd.Series((low + high) / 2.0, index=series.index)
    normalized = (series - s_min) / (s_max - s_min)
    return low + normalized * (high - low)


def compute_port_cfrsi(df_analyzed: pd.DataFrame) -> pd.DataFrame:
    """
    Mengagregasi indikator anomali tingkat pelabuhan menjadi CFRSI & 5 Tiers.
    """
    if df_analyzed.empty:
        return pd.DataFrame()

    group_cols = [c for c in ["port_code", "port"] if c in df_analyzed.columns]
    if not group_cols:
        return pd.DataFrame()

    port_summary = df_analyzed.groupby(group_cols).agg(
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

    # Proporsi indikator
    port_summary["rf_ratio"] = port_summary["total_red_flags"] / port_summary["volume"]
    port_summary["stat_ratio"] = port_summary["stat_anomalies"] / port_summary["volume"]
    port_summary["ml_ratio"] = port_summary["ml_anomalies"] / port_summary["volume"]

    # Sub-indeks ter-normalisasi [0.10 - 1.00]
    port_summary["rule_based_index"] = minmax_scale_port(port_summary["rf_ratio"])
    port_summary["statistical_index"] = minmax_scale_port(port_summary["stat_ratio"])
    port_summary["ml_index"] = minmax_scale_port(port_summary["ml_ratio"])

    # Composite Fraud Risk Screening Index (CFRSI) — Equal Weighting
    port_summary["cfrsi"] = (
        port_summary["rule_based_index"] +
        port_summary["statistical_index"] +
        port_summary["ml_index"]
    ) / 3.0

    # 1. Percentile-Based Approach (5 Quintiles)
    labels_5 = ["Sangat Rendah", "Rendah", "Sedang", "Tinggi", "Sangat Tinggi"]
    try:
        port_summary["risk_tier_percentile"] = pd.qcut(
            port_summary["cfrsi"].rank(method="first"),
            q=5,
            labels=labels_5
        )
    except Exception:
        port_summary["risk_tier_percentile"] = "Sedang"

    # 2. Fixed-Scale Approach
    # Very Low: 0.10 - 0.28, Low: 0.28 - 0.46, Medium: 0.46 - 0.64, High: 0.64 - 0.82, Very High: 0.82 - 1.00
    fixed_bins = [0.0, 0.28, 0.46, 0.64, 0.82, 1.01]
    port_summary["risk_tier_fixed"] = pd.cut(
        port_summary["cfrsi"],
        bins=fixed_bins,
        labels=labels_5,
        right=False
    )

    return port_summary.sort_values("cfrsi", ascending=False).reset_index(drop=True)


def main():
    print("=========================================================")
    print("INAPORTNET ANALYTICS -- CFRSI & FRAUD RISK ANALYSIS")
    print("=========================================================")

    # Contoh sampel simulasi / load data
    np.random.seed(42)
    n_records = 5000
    ports = ["IDBDJ", "IDBOA", "IDBPN", "IDBTN", "IDLBO", "IDSRI", "IDTJB", "IDTPP", "IDJAK"]
    
    sim_data = pd.DataFrame({
        "port_code": np.random.choice(ports, n_records),
        "approval_minutes": np.random.exponential(scale=30, size=n_records),
        "gt": np.random.randint(500, 30000, size=n_records),
        "hour": np.random.randint(0, 24, size=n_records),
        "day": np.random.choice(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], size=n_records),
        "vessel_name": [f"Vessel_{i}" for i in np.random.randint(1, 200, size=n_records)],
        "submission_time": pd.date_range("2025-01-01", periods=n_records, freq="h"),
        "date": pd.date_range("2025-01-01", periods=n_records, freq="h").date
    })

    print(f"Dimuat {len(sim_data):,} record PKK transaksi...")

    # Step 1: Rule-based detection
    print("\n[1/4] Mengoperasikan Rule-Based Anomaly Engine...")
    df_rule = run_rule_based_detection(sim_data)
    print(f" -> Deteksi Red Flags: {df_rule['is_red_flag'].sum():,} ({df_rule['is_red_flag'].mean()*100:.2f}%)")

    # Step 2: Statistical Modified Z-Score
    print("\n[2/4] Mengoperasikan Statistical OLS & Modified Z-Score Engine...")
    df_stat = run_statistical_zscore(df_rule)
    print(f" -> Deteksi Outlier Z <= -2.5: {df_stat['is_stat_anomaly'].sum():,} ({df_stat['is_stat_anomaly'].mean()*100:.2f}%)")

    # Step 3: Isolation Forest
    print("\n[3/4] Mengoperasikan Isolation Forest Machine Learning Engine...")
    df_ml = run_isolation_forest(df_stat)
    print(f" -> Deteksi Anomali Isolation Forest: {df_ml['is_ml_anomaly'].sum():,} ({df_ml['is_ml_anomaly'].mean()*100:.2f}%)")

    # Step 4: CFRSI Aggregation
    print("\n[4/4] Mengagregasi Composite Fraud Risk Screening Index (CFRSI)...")
    cfrsi_df = compute_port_cfrsi(df_ml)

    print("\nTop 5 Pelabuhan dengan Skor CFRSI Tertinggi:")
    cols_display = ["port_code", "volume", "rule_based_index", "statistical_index", "ml_index", "cfrsi", "risk_tier_percentile", "risk_tier_fixed"]
    print(cfrsi_df[cols_display].head(5).to_string(index=False))

    print("\nDistribusi Tingkat Risiko (Fixed Scale):")
    print(cfrsi_df["risk_tier_fixed"].value_counts())

    print("\n=========================================================")
    print("SUCCESS: Analisis CFRSI Selesai!")
    print("=========================================================")


if __name__ == "__main__":
    main()
