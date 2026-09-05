# Inaportnet analytics - Indonesian Port 2025

This project was conducted to analyze one of all port services across 259 ports in Indonesia during 2025.
The objective is to evaluate service performance based on service level agreement compliance and classify the port efficiency according to operational workload and average approval time.

The analysis begins with data collection through web-scraping from the Inaportnet monitoring portal:
https://monitoring-inaportnet.dephub.go.id/
The data collection script is included in this repository.
The dataset covers PKK (Ship Arrival Approval) records collected throughout 2025.
Prior to analysis, data preprocessing was conducted to examine the dataset structure and calculate approval time based on the time difference between request submission and the approval response.


# Project Structure

```text
inaportnetAnalytics/
│
├── data/                          # Port reference data
│   └── port_code.xlsx
│
├── scripts/                       # Analysis scripts (research pipeline)
│   ├── 00_data_collection.py
│   ├── 01_data_preprocessing.py
│   ├── 02_descriptive_stats.py
│   ├── 03_port_performance_calculation.py
│   ├── 04_quadrant_analysis.py
│   └── 05_fraud_risk_analysis.py  # CFRSI & Multi-layer Fraud Risk Screening
│
├── outputs/                       # Generated charts and visualizations
│
├── papers/                        # Research papers and reports
│   └── Inaportnet-update.pdf      # Wijaya & Setyawan (2026) CFRSI Paper
│
├── inaportnetDashboard/           # Interactive Streamlit Web Dashboard
│   ├── app.py                     # Main home page
│   ├── requirements.txt
│   ├── supabase_schema.sql        # Database schema (run in Supabase SQL Editor)
│   ├── .streamlit/
│   │   └── secrets.toml           # Supabase credentials
│   ├── modules/
│   │   ├── database.py            # Supabase CRUD operations
│   │   ├── scraper.py             # Web scraping functions
│   │   ├── preprocessing.py       # Data preprocessing
│   │   ├── analysis.py            # Performance index & CFRSI calculations
│   │   └── visualization.py       # Plotly interactive charts & CFRSI plots
│   ├── pages/
│   │   ├── 1_📊_Data_Collection.py
│   │   ├── 2_🚦_Traffic_Overview.py
│   │   ├── 3_📋_Service_Performance.py
│   │   ├── 4_🗺️_Port_Classification.py
│   │   ├── 5_🗄️_Database_Viewer.py
│   │   └── 6_🛡️_Fraud_Risk_Screening.py  # CFRSI & Anti-Fraud Governance EWS
│   └── venv/                      # Python virtual environment
│
└── README.md
```

# Research Paper & CFRSI Framework

This project integrates the research framework from:
> **"Toward Data-Driven Anti-Fraud Governance: Anomaly Detection and Composite Risk Scoring for Port-Level Oversight in Digital Maritime Services"**
> *Rifki Wijaya & Eka C. Setyawan (2026)*

### 🛡️ Composite Fraud Risk Screening Index (CFRSI)
The framework integrates 3 complementary analytical perspectives:
1. **Rule-Based Engine**: 5 Red Flag rules (Quick Approval $<10$s, Long Duration $>8$h, Low Oversight `00-04`, GT Manipulation, Same Vessel across 2 ports $<2$h).
2. **Statistical Engine**: OLS Regression & Modified Z-Score residual threshold ($Z_i \le -2.5$).
3. **Machine Learning Engine**: Unsupervised Isolation Forest multidimensional anomaly detection.
4. **CFRSI Aggregation**: Equal-weighted composite score normalized with Min-Max scaling `[0.10, 1.00]`.
5. **5-Tier Risk Classification**: Percentile-based & Fixed-scale ordinal risk levels (Sangat Rendah to Sangat Tinggi).

# Running the Dashboard

```powershell
# Masuk ke folder dashboard
cd d:\Documents\inaportnetAnalytics\inaportnetDashboard

# Aktifkan virtual environment (PowerShell)
. .\venv\Scripts\Activate.ps1

# Jalankan Streamlit
python -m streamlit run app.py

# App tersedia di: http://localhost:8501
```

# Setup Supabase (Opsional)

1. Buat project di https://supabase.com
2. Jalankan `supabase_schema.sql` di SQL Editor Supabase
3. Isi kredensial di `inaportnetDashboard/.streamlit/secrets.toml`:
   ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "your-anon-key"
   ```

# Potential Insight

This analytical framework provides traffic classification based on performance index and service volume.

# Future Improvement

This project can be further enhanced by developing an interactive dashboard visualization and applying predictive service demand modelling to forecast and estimate workforce requirements.

---

# 🚀 Authors & Contributors

Crafted with passion & precision for Indonesian Maritime Logistics Analytics:

* **Eka** — [@ekacs](https://github.com/ekacs)
* **Rifki** — [@rifkiw](https://github.com/rifkiwijaya12)

---

### ☕ Support & Buy Us a Coffee

Jika platform ini membantu pekerjaan atau riset Anda, dukung kami dengan traktir kopi agar makin semangat memperbarui & menambah fitur-fitur baru! ☕🚀
