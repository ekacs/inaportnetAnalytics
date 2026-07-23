# 🚢 Inaportnet Analytics — Workflow & Arsitektur Aplikasi

Dokumen ini menjelaskan alur kerja (*workflow*), aliran data (*data flow*), arsitektur modul, dan metodologi analisis pada aplikasi **Inaportnet Analytics Dashboard**.

---

## 📐 1. Diagram Alur Kerja Aplikasi (Mermaid Workflow)

```mermaid
flowchart TD
    %% Node Sumber Data
    subgraph DataSources ["1. Sumber Data (Data Sources)"]
        A1["🌐 Portal Monitoring Inaportnet<br>(Web Scraping 2-Stage)"]
        A2["📁 File Lokal Eksternal<br>(CSV / Excel Upload)"]
        A3["🗄️ Database Supabase<br>(PostgreSQL Cloud Storage)"]
    end

    %% Node Engine Preprocessing
    subgraph PreprocessingEngine ["2. Engine Preprocessing Data"]
        B1["Parsing Datetime & Filter Tahun 2025"]
        B2["Hitung Approval Time & Approval Minutes"]
        B3["Ekstraksi Komponen Waktu<br>(Kuartal, Bulan, Hari, Jam)"]
        B4["Deteksi & Handling Data Outlier / Bug"]
    end

    %% Node Session & Storage
    subgraph StorageLayer ["3. Manajemen Sesi & Penyimpanan"]
        C1[("st.session_state<br>(In-Memory Session Data)")]
        C2[("Supabase Database<br>(Tabel: pkk_records)")]
    end

    %% Node Analytical Engines
    subgraph AnalyticsEngine ["4. Engine Analisis & Komputasi Indeks"]
        D1["📊 Traffic Analysis Engine<br>- Share Volume PKK per Pelabuhan<br>- Tren Kuartal, Bulan, Hari, Jam"]
        D2["📋 Service Performance Engine<br>- SLA Compliance Rate (≤ 30 menit)<br>- Distribusi Kategori Waktu Response<br>- Identification Top 10 Terlama"]
        D3["🗺️ Port Classification Engine<br>- Normalisasi Winsorized Min-Max (P5-P95)<br>- Hitung 4 Sub-Indeks Performa<br>- Composite Performance Index (CPI)<br>- 4-Quadrant Classification Matrix"]
    end

    %% Node Halaman Interface User
    subgraph UserInterface ["5. Antarmuka Streamlit (UI/UX Pages)"]
        E0["🏠 Beranda (app.py)<br>Executive Summary & System Status"]
        E1["📊 Data Collection Page<br>Scraping, Upload, Supabase, Export"]
        E2["🚦 Traffic Overview Page<br>KPI Cards & Multi-Dimension Trends"]
        E3["📋 Service Performance Page<br>SLA Threshold Slider & Histograms"]
        E4["🗺️ Port Classification Page<br>Interactive Scatter Plot & Rankings"]
    end

    %% Alur Hubungan Data
    A1 -->|Raw PKK Data| B1
    A2 -->|Uploaded Data| B1
    A3 -->|Fetched Data| B1

    B1 --> B2 --> B3 --> B4
    B4 -->|Clean Data| C1
    C1 -->|Upsert Sync| C2

    C1 --> D1
    C1 --> D2
    C1 --> D3

    D1 --> E2
    D2 --> E3
    D3 --> E4
    C1 --> E0
    A1 & A2 & A3 --> E1

    classDef primary fill:#1a4a7a,color:#fff,stroke:#0f2d52,stroke-width:2px;
    classDef secondary fill:#2471a3,color:#fff,stroke:#1a4a7a,stroke-width:1px;
    classDef accent fill:#f39c12,color:#fff,stroke:#d68910,stroke-width:1px;
    classDef success fill:#27ae60,color:#fff,stroke:#1e8449,stroke-width:1px;

    class E0,E1,E2,E3,E4 primary;
    class D1,D2,D3 secondary;
    class C1,C2 success;
    class A1,A2,A3 accent;
```

---

## 🔄 2. Detail Alur Kerja Per Tahap

### Tahap 1: Pengumpulan & Penginputan Data (*Data Collection*)
Aplikasi mendukung 3 mode penginputan data pada halaman **`1_📊_Data_Collection.py`**:

1. **Web Scraping Direct (Inaportnet Portal)**
   - **Stage 1 (PKK List):** Mengambil daftar PKK berdasarkan kombinasi Kode Pelabuhan $\times$ Jenis Angkutan (`dn`/`ln`) $\times$ Bulan.
   - **Stage 2 (Approval Detail):** Mengambil detail waktu permohonan (*submission*) dan waktu persetujuan (*response*) untuk setiap nomor PKK.
   - Tampilan interaktif dengan *Progress Bar* 2-stage real-time.
2. **Upload File Eksternal**
   - User dapat mengunggah file CSV atau Excel hasil analisis/scraping sebelumnya.
   - Memiliki engine **Validasi Kolom Otomatis** untuk mendeteksi apakah data mentah atau sudah preprocessed.
3. **Load dari Supabase Database**
   - Mengambil data histori dari tabel `pkk_records` di PostgreSQL Cloud Supabase dengan fitur pagination otomatis dan filter pelabuhan.

---

### Tahap 2: Pemrosesan Data (*Preprocessing Engine*)
Modul [`modules/preprocessing.py`](file:///d:/Documents/inaportnetAnalytics/inaportnetDashboard/modules/preprocessing.py) secara otomatis mengeksekusi pipeline berikut:

$$\text{approval\_time} = \text{response\_time} - \text{submission\_time}$$

$$\text{approval\_minutes} = \frac{\text{total\_seconds}(\text{approval\_time})}{60}$$

- **Ekstraksi Komponen Waktu:** Tahun, Kuartal (`Q1`–`Q4`), Bulan (`1`–`12`), Nama Hari (`Monday`–`Sunday`), dan Jam (`00`–`23`).
- **Filtering Scope:** Otomatis membatasi analisis pada scope tahun 2025.
- **Handling Outlier / Data Bug:** Mendeteksi selisih waktu negatif ($\text{approval\_time} < 0$) dan menandainya agar tidak merusak perhitungan statistik.

---

### Tahap 3: Analisis & Komputasi Indeks (*Analytics Engine*)

Modul [`modules/analysis.py`](file:///d:/Documents/inaportnetAnalytics/inaportnetDashboard/modules/analysis.py) menjalankan 3 cabang analisis utama:

#### A. Traffic Analytics
- Menghitung **National Traffic Share (%)** per pelabuhan.
- Mengelompokkan tren transaksi per Kuartal, Bulan, Hari dalam seminggu, dan Jam dalam sehari (dengan *highlight* jam kerja 08:00–17:00).

#### B. Service Performance & SLA Analytics
- Target SLA standar: **$\le 30$ menit** per persetujuan PKK.
- Kategorisasi distribusi waktu respons:
  - `< 30 mnt`, `30-60 mnt`, `1-2 jam`, `2-6 jam`, `6-12 jam`, `12-24 jam`, `> 24 jam`.
- Identifikasi Top 10 pelabuhan dengan waktu approval terlama.

#### C. Port Classification & Composite Index Engine
Setiap pelabuhan diukur menggunakan 4 sub-indeks yang dinormalisasi dengan **Winsorized Min-Max (P5 - P95)**:

1. **Compliance Index ($I_{\text{comp}}$):** % PKK yang memenuhi SLA ($\le 30$ mnt). *(Higher is better)*
2. **Efficiency Index ($I_{\text{eff}}$):** Rata-rata waktu persetujuan. *(Lower is better)*
3. **Consistency Index ($I_{\text{cons}}$):** Koefisien Variasi ($CV = \frac{SD}{\text{Mean}}$). *(Lower is better)*
4. **Robustness Index ($I_{\text{rob}}$):** Proporsi keterlambatan ekstrem ($> 102$ mnt). *(Lower is better)*

**Rumus Composite Performance Index (CPI):**

$$\text{CPI} = \frac{I_{\text{comp}} + I_{\text{eff}} + I_{\text{cons}} + I_{\text{rob}}}{4}$$

**Matrix Klasifikasi 4 Kuadran (Median Threshold):**

```mermaid
quadrantChart
    title Matriks Klasifikasi Pelabuhan 4 Kuadran
    x-axis Volume PKK Rendah --> Volume PKK Tinggi
    y-axis Composite Index Rendah --> Composite Index Tinggi
    quadrant-1 Benchmark Port
    quadrant-2 Efficient Port
    quadrant-3 Developing Port
    quadrant-4 Congested Port
```

| Nama Kuadran | Kriteria Volume | Kriteria Indeks (CPI) | Karakteristik Operasional |
| :--- | :--- | :--- | :--- |
| 🟢 **Benchmark Port** | $\ge \text{Median Volume}$ | $\ge \text{Median CPI}$ | Pelabuhan terbaik: volume tinggi dan performa sangat efisien. |
| 🔵 **Efficient Port** | $< \text{Median Volume}$ | $\ge \text{Median CPI}$ | Pelabuhan efisien dengan beban kerja relatif kecil. |
| 🟠 **Developing Port** | $< \text{Median Volume}$ | $< \text{Median CPI}$ | Perlu pengembangan kapasitas & efisiensi layanan. |
| 🔴 **Congested Port** | $\ge \text{Median Volume}$ | $< \text{Median CPI}$ | Padat transaksi namun terjadi bottleneck persetujuan. |

---

### Tahap 4: Antarmuka & Ekspor (*UI & Export*)
- Visualisasi dibuat secara interaktif menggunakan **Plotly** di modul [`modules/visualization.py`](file:///d:/Documents/inaportnetAnalytics/inaportnetDashboard/modules/visualization.py).
- Pengguna dapat mengekspor data mentah maupun data hasil agregasi/klasifikasi ke format **CSV** dan **Excel (.xlsx)**.

---

## 🛠️ 3. Arsitektur File & Fungsi Modul

```
inaportnetAnalytics/
└── inaportnetDashboard/
    ├── app.py                      # Entry point, status koneksi DB, metric cards
    ├── requirements.txt            # Daftar library Python
    ├── supabase_schema.sql         # SQL DDL untuk pembuatan tabel PostgreSQL
    ├── .streamlit/secrets.toml     # Kredensial SUPABASE_URL & SUPABASE_KEY
    │
    ├── modules/
    │   ├── database.py             # CRUD Supabase (insert_pkk_records, fetch_pkk_records)
    │   ├── scraper.py              # Web Scraper 2-stage (scrape_pkk_list, scrape_approval_times)
    │   ├── preprocessing.py        # Pipeline data cleaning & validasi upload
    │   ├── analysis.py             # Perhitungan statistik, SLA, CPI, & kuadran
    │   └── visualization.py        # Chart Plotly (Donut, Bar, Line, Quadrant Scatter)
    │
    └── pages/
        ├── 1_📊_Data_Collection.py # Scraping, Upload, Supabase, Export
        ├── 2_🚦_Traffic_Overview.py # Visualisasi tren & volume
        ├── 3_📋_Service_Performance.py # SLA threshold & histogram
        └── 4_🗺️_Port_Classification.py # Scatter plot kuadran & ranking
```

---

## 🚀 4. Cara Menjalankan Aplikasi

Buka PowerShell di lokasi project dan jalankan command berikut:

```powershell
# Masuk ke folder dashboard
cd d:\Documents\inaportnetAnalytics\inaportnetDashboard

# Jalankan Streamlit
.\inaportnetdashboard-env\Scripts\python.exe -m streamlit run app.py
```

Aplikasi akan otomatis terbuka di browser pada alamat **`http://localhost:8501`**.
