# Inaportnet Analytics - Indonesian Port 2025

This project was conducted to analyze one of all port services across 259 ports in Indonesia during 2025.
The objective is to evaluate service performance based on service level agreement compliance and classify the port efficiency according to operational workload and average approval time.

The analysis begins with data collection through web-scraping from the Inaportnet monitoring portal:
https://monitoring-inaportnet.dephub.go.id/
The data collection script is included in this repository.
The dataset covers PKK (Ship Arrival Approval) records collected throughout 2025.
Prior to analysis, data preprocessing was conducted to examine the dataset structure and calculate approval time based on the time difference between request submission and the approval response.

---

## Project Structure

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
│   ├── 05_fraud_risk_analysis.py  # CFRSI & Multi-layer Fraud Risk Screening
│   ├── port_classification.py
│   ├── service_level.py
│   ├── service_performance.py
│   ├── traffic_analysis.py
│   └── workload_capacity.py
│
├── outputs/                       # Generated charts and visualizations
│
├── papers/                        # Research papers and reports
│   └── Inaportnet-update.pdf      # Wijaya & Setyawan (2026) CFRSI Paper
│
├── inaportnetDashboard/           # Interactive Streamlit Web Dashboard
│   ├── app.py                     # Main home page + Supabase connection modal
│   ├── requirements.txt
│   ├── supabase_schema.sql        # Database schema (run in Supabase SQL Editor)
│   ├── .streamlit/
│   │   └── secrets.toml           # Supabase credentials (optional, can use UI)
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── database.py            # Dual-mode CRUD (Supabase Cloud + SQLite Local)
│   │   ├── scraper.py             # Anti-detection web scraping (2-stage)
│   │   ├── preprocessing.py       # Data preprocessing pipeline
│   │   ├── analysis.py            # Performance index & CFRSI calculations
│   │   ├── visualization.py       # Plotly interactive charts & CFRSI plots
│   │   └── theme.py               # Light/Dark mode theme selector
│   ├── pages/
│   │   ├── 1_📊_Data_Collection.py    # Scraping, upload, DB load, export + pause/stop
│   │   ├── 2_🚦_Traffic_Overview.py   # Volume & trend analysis
│   │   ├── 3_📋_Service_Performance.py # SLA compliance & histograms
│   │   ├── 4_🗺️_Port_Classification.py # 4-quadrant classification & ranking
│   │   ├── 5_🗄️_Database_Viewer.py    # Live DB inspector & multi-format export
│   │   └── 6_🛡️_Fraud_Risk_Screening.py # CFRSI & Anti-Fraud Governance EWS
│   └── data/
│       └── inaportnet_local.db    # SQLite local database (auto-created)
│
└── README.md
```

---

## Research Paper & CFRSI Framework

This project integrates the research framework from:

> **"Toward Data-Driven Anti-Fraud Governance: Anomaly Detection and Composite Fraud Risk Scoring for Port-Level Oversight in Digital Maritime Services"**
> *Rifki Wijaya & Eka C. Setyawan (2026)*

### Composite Fraud Risk Screening Index (CFRSI)

The framework integrates 3 complementary analytical perspectives:

1. **Rule-Based Engine**: 5 Red Flag rules (Quick Approval <10s, Long Duration >8h, Low Oversight 00-04, GT Manipulation, Same Vessel across 2 ports <2h).
2. **Statistical Engine**: OLS Regression & Modified Z-Score residual threshold (Z_i <= -2.5).
3. **Machine Learning Engine**: Unsupervised Isolation Forest multidimensional anomaly detection.
4. **CFRSI Aggregation**: Equal-weighted composite score normalized with Min-Max scaling [0.10, 1.00].
5. **5-Tier Risk Classification**: Percentile-based & Fixed-scale ordinal risk levels (Sangat Rendah to Sangat Tinggi).

---

## Key Features (v3.0)

### Data Collection

- **2-Stage Web Scraping**: PKK list retrieval + approval detail extraction
- **Anti-Detection**: Browser-like User-Agent rotation, random delays (0.8-3s), exponential backoff retry (max 3 attempts), persistent session cookies
- **Pause / Resume / Stop**: Real-time control buttons during scraping with progress bar, elapsed time, ETA, and error count
- **Multi-Source Input**: Web scraping, file upload (CSV/Excel/Zip/Parquet), database load
- **Database Source Selector**: Choose between Supabase Cloud, SQLite Local, or Auto-detect

### Analysis

- **Traffic Analytics**: Volume share per port, quarterly/monthly/daily/hourly trends
- **Service Performance**: SLA compliance (<=30 min threshold), response time distribution, top 10 worst performers
- **Port Classification**: 4-quadrant matrix (Benchmark/Efficient/Developing/Congested) with Composite Performance Index
- **CFRSI Fraud Risk Screening**: 3-layer anomaly detection with 5-tier risk classification

### Database

- **Dual-Mode Storage**: Supabase Cloud (PostgreSQL) + SQLite Local (fallback, auto-created)
- **Manual Connection UI**: Connect to Supabase directly from the dashboard (no secrets.toml required)
- **Auto-Fallback**: Falls back to SQLite if Supabase is unavailable
- **Multi-Format Export**: CSV, Excel, JSON, SQL dump

### UI/UX

- **Light/Dark Mode**: Theme selector in sidebar
- **Interactive Charts**: Plotly-based donut, bar, line, scatter, histogram plots
- **Responsive Layout**: Wide layout with metric cards and navigation grid

---

## Running the Dashboard

```powershell
# Navigate to dashboard folder
cd d:\Documents\inaportnetAnalytics\inaportnetDashboard

# Activate virtual environment (PowerShell)
.\venv\Scripts\Activate.ps1

# Run Streamlit
python -m streamlit run app.py

# App available at: http://localhost:8501
```

---

## Setup Supabase (Optional)

### Option A: secrets.toml (Traditional)

1. Create a project at https://supabase.com
2. Run `supabase_schema.sql` in Supabase SQL Editor
3. Fill credentials in `inaportnetDashboard/.streamlit/secrets.toml`:
   ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "your-anon-key"
   ```

### Option B: Dashboard UI (Recommended)

1. Run the dashboard
2. Click **"Konfigurasi Supabase"** button in the sidebar
3. Enter your Supabase URL and Anon Key
4. Click **"Hubungkan"** — connection is stored in session (no file needed)

---

## Tech Stack

| Layer         | Technology                                           |
| ------------- | ---------------------------------------------------- |
| Frontend      | Streamlit (multi-page app)                           |
| Backend       | Python (pandas, numpy, scipy, scikit-learn)          |
| Database      | Supabase (PostgreSQL Cloud) + SQLite Local           |
| Visualization | Plotly (interactive charts)                          |
| Data Source   | Web scraping from monitoring-inaportnet.dephub.go.id |

---

## Dependencies

```
streamlit>=1.35.0
pandas>=2.0.0
plotly>=5.18.0
requests>=2.31.0
supabase>=2.4.0
openpyxl>=3.1.0
lxml>=5.0.0
scipy>=1.11.0
numpy>=1.24.0
scikit-learn>=1.3.0
statsmodels>=0.14.0
python-dotenv>=1.0.0
```

---

## Potential Insight

This analytical framework provides traffic classification based on performance index and service volume.

## Future Improvement

This project can be further enhanced by developing an interactive dashboard visualization and applying predictive service demand modelling to forecast and estimate workforce requirements.

---

## Authors & Contributors

Crafted with passion & precision for Indonesian Maritime Logistics Analytics:

* **Eka** — [@ekacs](https://github.com/ekacs)
* **Rifki** — [@rifkiw](https://github.com/rifkiwijaya12)

---

### Support & Buy Us a Coffee

Jika platform ini membantu pekerjaan atau riset Anda, dukung kami dengan traktir kopi agar makin semangat memperbarui & menambah fitur-fitur baru!
