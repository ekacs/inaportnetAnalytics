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
│   └── 04_quadrant_analysis.py
│
├── outputs/                       # Generated charts and visualizations
│
├── papers/                        # Research papers and reports
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
│   │   ├── analysis.py            # Performance index calculations
│   │   └── visualization.py       # Plotly interactive charts
│   ├── pages/
│   │   ├── 1_📊_Data_Collection.py
│   │   ├── 2_🚦_Traffic_Overview.py
│   │   ├── 3_📋_Service_Performance.py
│   │   ├── 4_🗺️_Port_Classification.py
│   │   └── 5_🗄️_Database_Viewer.py
│   └── venv/                      # Python virtual environment
│
└── README.md
```

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
