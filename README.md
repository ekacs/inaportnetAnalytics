# 🚢 Inaportnet Analytics — Platform Analisis Operasional & Deteksi Risiko Fraud Pelabuhan Indonesia 2025

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B.svg)](https://streamlit.io/)
[![Plotly](<https://img.shields.io/badge/Plotly-Interactive%20Charts-3F4F75.svg>)](https://plotly.com/)
[![Database](<https://img.shields.io/badge/Database-SQLite%20%7C%20Supabase-green.svg>)](https://supabase.com/)
[![Machine Learning](<https://img.shields.io/badge/ML-Isolation%20Forest%20%7C%20OLS-orange.svg>)](https://scikit-learn.org/)
[![Version](https://img.shields.io/badge/Version-v3.0--CFRSI-purple.svg)](https://github.com/ekacs/inaportnetAnalytics)

Platform analitik data dan *Early Warning System* (EWS) terintegrasi untuk mengevaluasi kinerja operasional layanan kapal **Persetujuan Kedatangan Kapal (PKK)** pada 259 pelabuhan di seluruh Indonesia selama periode 2025.

Proyek ini menggabungkan evaluasi kepatuhan *Service Level Agreement* (SLA), klasifikasi efisiensi 4-kuadran, kontrol kualitas data (*Data Quality Control*), serta kerangka kerja deteksi anomali multi-lapis: **Composite Fraud Risk Screening Index (CFRSI)** guna mendukung tata kelola anti-fraud kemaritiman berbasis data.

Data dikumpulkan melalui *web scraping* otomatis dari portal resmi Kementerian Perhubungan Republik Indonesia:
🌐 **[Portal Monitoring Inaportnet Dephub](https://monitoring-inaportnet.dephub.go.id/)**

---

## 📑 Daftar Isi

- [Struktur Repositori](#-struktur-repositori)
- [Landasan Riset &amp; Kerangka Kerja CFRSI](#-landasan-riset--kerangka-kerja-cfrsi)
- [Fitur Utama Dashboard (v3.0)](#-fitur-utama-dashboard-v30)
- [Panduan Instalasi &amp; Persiapan Lingkungan](#-panduan-instalasi--persiapan-lingkungan)
- [Panduan Penggunaan Dashboard (Langkah demi Langkah)](#-panduan-penggunaan-dashboard-langkah-demi-langkah)
- [Menjalankan Skrip Pipeline Riset (Standalone)](#-menjalankan-skrip-pipeline-riset-standalone)
- [Konfigurasi Database (Dual-Mode)](#-konfigurasi-database-dual-mode)
- [Tech Stack &amp; Dependensi](#-tech-stack--dependensi)
- [Authors &amp; Kontributor](#-authors--kontributor)

---

## 📂 Struktur Repositori

```text
inaportnetAnalytics/
│
├── data/                                 # Data referensi master pelabuhan
│   └── port_code.xlsx                    # Pemetaan kode dan nama pelabuhan se-Indonesia
│
├── scripts/                              # Pipeline riset ilmiah (Standalone Scripts)
│   ├── 00_data_collection.py             # Script scraper mandiri
│   ├── 01_data_preprocessing.py          # Pembersihan data & ekstraksi durasi
│   ├── 02_descriptive_stats.py           # Analisis statistik deskriptif
│   ├── 03_port_performance_calculation.py # Komputasi metrik performa & SLA
│   ├── 04_quadrant_analysis.py           # Klasifikasi 4-kuadran (Winsorized Min-Max)
│   ├── 05_fraud_risk_analysis.py         # Engine CFRSI (Rule, OLS Z-Score, Isolation Forest)
│   ├── port_classification.py            # Modul analisis klasifikasi pelabuhan
│   ├── service_level.py                  # Modul kalkulasi kepatuhan SLA
│   ├── service_performance.py            # Modul agregasi performa operasional
│   ├── traffic_analysis.py               # Modul eksplorasi lalu lintas kapal
│   └── workload_capacity.py              # Analisis beban kerja harian
│
├── outputs/                              # Visualisasi & chart hasil analisis statis (PNG)
│
├── papers/                               # Literatur akademik, publikasi, dan presentasi
│   ├── Inaportnet-update.pdf             # Paper CFRSI (Wijaya & Setyawan, 2026)
│   ├── PPT - paper NAFC 2026 - Rifki Eka.pptx # Materi presentasi konferensi NAFC 2026
│   └── ...                               # Laporan pendukung dan studi terkait
│
├── inaportnetDashboard/                  # Aplikasi Web Dashboard Interaktif (Streamlit)
│   ├── app.py                            # Halaman Beranda (Executive KPI, status DB, navigasi)
│   ├── requirements.txt                  # Daftar pustaka dependensi Python
│   ├── supabase_schema.sql               # Skema tabel PostgreSQL Supabase Cloud
│   │
│   ├── .streamlit/
│   │   ├── config.toml                   # Konfigurasi tema & limit upload (500 MB)
│   │   └── secrets.toml                  # Kredensial Supabase (opsional, bisa via UI)
│   │
│   ├── modules/                          # Modul inti backend aplikasi
│   │   ├── database.py                   # Dual-mode storage (SQLite lokal & Supabase Cloud)
│   │   ├── scraper.py                    # Scraper anti-deteksi (2-stage: list + detail)
│   │   ├── preprocessing.py              # Pipeline datetime parsing, durasi, & time features
│   │   ├── analysis.py                   # Engine analitik, CPI, Winsorized, dan CFRSI
│   │   ├── visualization.py              # Builder grafik interaktif Plotly
│   │   └── theme.py                      # Selector tema (Light / Dark mode)
│   │
│   ├── pages/                            # Halaman antarmuka Streamlit
│   │   ├── 1_📊_Data_Collection.py       # Scraping, upload, QC data, scan folder data
│   │   ├── 2_🗄️_Database_Viewer.py       # (Arsip/Internal inspector database)
│   │   ├── 3_🚦_Traffic_Overview.py      # Volume nasional, share, dan tren multi-dimensi
│   │   ├── 4_📋_Service_Performance.py   # Kepatuhan SLA, histogram respons, top bottleneck
│   │   ├── 5_🗺️_Port_Classification.py   # Matriks 4-kuadran, 4 sub-indeks CPI, pemeringkatan
│   │   └── 6_🛡️_Fraud_Risk_Screening.py  # Model CFRSI, deteksi anomali 3 lapis, ekspor audit
│   │
│   └── data/                             # Penyimpanan data lokal dashboard
│       ├── inaportnet_local.db           # Basis data SQLite lokal (terintegrasi otomatis)
│       ├── df_redflag_ml.parquet         # Dataset teranotasi Red Flag & hasil komputasi ML
│       └── port_code.xlsx                # Salinan referensi kode pelabuhan
│
├── workflow.md                           # Dokumentasi teknis alur arsitektur data & Mermaid
└── README.md                             # Dokumentasi utama proyek
```



---

## 🔬 Landasan Riset & Kerangka Kerja CFRSI

Dashboard ini mengimplementasikan model riset yang telah dipublikasikan pada:

> **"Toward Data-Driven Anti-Fraud Governance: Anomaly Detection and Composite Fraud Risk Scoring for Port-Level Oversight in Digital Maritime Services"**
> *Rifki Wijaya & Eka C. Setyawan (2026)*

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│               COMPOSITE FRAUD RISK SCREENING INDEX (CFRSI)                      │
├───────────────────────┬─────────────────────────┬───────────────────────────────┤
│   1. RULE-BASED       │   2. STATISTICAL        │   3. MACHINE LEARNING         │
│      SUB-INDEX        │      SUB-INDEX          │      SUB-INDEX                │
├───────────────────────┼─────────────────────────┼───────────────────────────────┤
│  • Quick Approval     │  • Regresi OLS Waktu vs │  • Unsupervised               │
│    (< 10 detik)       │    Volume, GT, Hari, Jam│    Isolation Forest           │
│  • Long Duration      │  • Modified Z-Score     │  • 100 Trees, 256 Samples     │
│    (> 8 jam)          │    Residual (|Z| ≥ 3.5) │  • 7% Contamination Target    │
│  • Low Oversight      │  • Deteksi persetujuan  │  • Deteksi anomali            │
│    (00.00 - 04.00)    │    abnormal ekstrem     │    multidimensi non-linear    │
│  • GT Manipulation    │                         │                               │
│  • Same Vessel < 2 jam│                         │                               │
└───────────────────────┴─────────────────────────┴───────────────────────────────┘
                                       │
                                       ▼
             Normalisasi Winsorized Min-Max [0.10, 1.00] & Equal Weighting
                                       │
                                       ▼
       5-Tier Ordinal Risk Classification: Sangat Rendah ──► Sangat Tinggi
                                       │
                                       ▼
               Implementasi 4 Pilar Strategi Anti-Fraud (OJK / Kemenhub)
```

### 5 Aturan Operasional Red Flag (Dasar Regulasi)

1. **Quick Approval (< 10 detik):** Berdasarkan *PM 93/2013*, petugas wajib memverifikasi kelaiklautan dan kelengkapan dokumen. Persetujuan dalam hitungan detik mengindikasikan risiko *rubber-stamping* tanpa pemeriksaan substantif.
2. **Long Duration (> 8 jam):** Persetujuan yang melampaui jam kerja normal memicu risiko hambatan birokrasi sengaja atau potensi permintaan imbalan (*rent-seeking*).
3. **Low Oversight (00.00 – 04.00):** Pengajuan dan persetujuan di dini hari dengan supervisi minim rentan digunakan untuk menghindari pemantauan berjenjang.
4. **GT Manipulation:** Anomali deviasi tonase kotor (*Gross Tonnage*) kapal berisiko mengindikasikan upaya pengecilan ukuran kapal guna menurunkan tarif PNBP labuh/tambat.
5. **Same Vessel in 2 Ports (< 2 jam):** Berdasarkan *PP 61/2009*, kapal fisik yang sama tercatat selesai diproses di dua pelabuhan berbeda dalam waktu kurang dari 2 jam tidak masuk akal secara operasional navigasi maritim.

---

## ✨ Fitur Utama Dashboard (v3.0)

### 1. Ingestion Data & Quality Control (`1_📊_Data_Collection.py`)

- **2-Stage Web Scraping**: Mengambil daftar transaksi PKK per pelabuhan/jenis angkutan, dilanjutkan penarikan rincian stempel waktu *submission* dan *response*.
- **Anti-Deteksi**: Rotasi User-Agent, jeda waktu acak (0.8–3.0 detik), mekanisme *exponential backoff retry*, serta persistensi sesi cookie.
- **Kendali Scraping Interaktif**: Tombol **Jeda (Pause)**, **Lanjut (Resume)**, dan **Hentikan (Stop)** lengkap dengan indikator waktu berjalan, estimasi ETA, dan penghitung galat.
- **Penyimpanan Otomatis ke `./data/`**: Setiap file yang diunggah (CSV/Excel/Parquet) secara otomatis dicadangkan sebagai file fisik di folder `./data/` untuk keperluan jejak audit (*audit trail*).
- **Pemindai Berkas Lokal**: Menampilkan inventaris file di folder `./data/` lengkap dengan ukuran dan waktu modifikasi terakhir.
- **Data Quality Control (QC) Inspector**:
  - Deteksi transaksi galat (stempel waktu tidak valid atau durasi negatif).
  - Deteksi data *null* pada kolom-kolom kritis (`submission`, `response`, `port_code`, `pkk_number`, `vessel_name`).
  - Deteksi dan penyaringan nomor PKK duplikat.
  - Tombol inspeksi tabel dan pengunduhan file CSV untuk data error, null, atau duplikat.

### 2. Analisis Lalu Lintas Kapal (`3_🚦_Traffic_Overview.py`)

- **KPI Nasional**: Volume agregat PKK, jumlah pelabuhan aktif, rata-rata transaksi, bulan puncak (*peak month*), hari tersibuk, dan jam tersibuk.
- **Volume Share**: Visualisasi grafik donat persentase kontribusi muatan kapal antar pelabuhan.
- **Tren Multi-Dimensi**: Pola transaksi berbasis Kuartal (Q1–Q4), Bulan (Jan–Des), Hari dalam seminggu, dan Jam harian (dengan penanda zona jam operasional 08.00–17.00).
- **Filter Fleksibel**: Pemilahan data per pelabuhan spesifik atau agregat nasional.

### 3. Evaluasi Kinerja Layanan & SLA (`4_📋_Service_Performance.py`)

- **Kepatuhan SLA Dinamis**: Slider ambang batas SLA interaktif (default: **$\le 30$ menit** sesuai standar pelayanan kepelabuhanan).
- **Distribusi Waktu Persetujuan**: Histogram dan pie chart dalam 7 interval durasi (`<30 mnt`, `30-60 mnt`, `1-2 jam`, `2-6 jam`, `6-12 jam`, `12-24 jam`, `>24 jam`).
- **Analisis Bottleneck**: Identifikasi peringkat Top 10 pelabuhan dengan rata-rata waktu persetujuan terlama.

### 4. Klasifikasi Pelabuhan & Indeks Komposit (`5_🗺️_Port_Classification.py`)

- **Matriks 4-Kuadran**: Pemetaan kuadran berbasis Volume Pelayanan vs Waktu Persetujuan:
  - **Kuadran I (Benchmark / Prima):** Volume tinggi, waktu pemrosesan sangat cepat.
  - **Kuadran II (Efisien / Potensial):** Volume rendah/sedang, operasional sangat cepat.
  - **Kuadran III (Berkembang / Perlu Pembinaan):** Volume rendah, durasi layanan lambat.
  - **Kuadran IV (Padat / Perhatian Khusus):** Volume padat, durasi layanan lambat (*congested*).
- **Composite Performance Index (CPI)**: Agregasi 4 sub-indeks dengan normalisasi Winsorized Min-Max ($P_5 - P_{95}$): Kepatuhan ($I_{\text{comp}}$), Efisiensi ($I_{\text{eff}}$), Konsistensi ($I_{\text{cons}}$), dan Ketahanan ($I_{\text{rob}}$).

### 5. Deteksi Anomali & EWS Fraud (`6_🛡️_Fraud_Risk_Screening.py`)

- **Tampilan Metrik Utama**: Total PKK dievaluasi, % Red Flag, % Outlier Statistik, % Anomali ML, dan jumlah pelabuhan berkategori risiko tinggi.
- **Top-N CFRSI Ranking**: Visualisasi bar chart pelabuhan paling berisiko beserta perbandingan 3 sub-indeks penyusunnya.
- **Filter Kategori Risiko**: Penyaringan tabel interaktif berdasarkan 5 tingkat risiko (*Sangat Rendah* hingga *Sangat Tinggi*).
- **Unduh Data Hasil Audit**: Tombol langsung untuk mengekspor data transaksi outlier statistik dan anomali multidimensi Machine Learning ke format CSV.
- **Simulasi / Demo Cepat**: Tombol *Generate Benchmark Dataset (257 Pelabuhan)* untuk mencoba fitur analisis tanpa memerlukan data riil awal.
- **Integrasi 4 Pilar Anti-Fraud**: Pedoman tata kelola operasional (Pencegahan, Deteksi, Investigasi, Evaluasi) sesuai rekomendasi OJK 2024 / Ditjen Hubla.

### 6. Arsitektur Basis Data Ganda (Dual-Mode)

- **SQLite Lokal (Default)**: Otomatis diinisialisasi pada `./data/inaportnet_local.db` tanpa setup tambahan.
- **Supabase Cloud (PostgreSQL)**: Sinkronisasi data terpusat ke cloud dengan konfigurasi instan via GUI modal dashboard atau `secrets.toml`.
- **Ekspor Format Lengkap**: Dukungan unduh basis data ke CSV, Excel multi-sheet, JSON, dan SQL Dump.

---

## 💻 Panduan Instalasi & Persiapan Lingkungan

### Prasyarat Sistem

- **Sistem Operasi**: Windows 10/11, macOS, atau Linux
- **Python**: Versi `3.10`, `3.11`, `3.12`, atau yang lebih baru
- **Git**: Untuk kloning repositori

---

### Langkah 1: Kloning Repositori

Buka terminal (PowerShell, Command Prompt, atau Bash), lalu jalankan:

```bash
git clone https://github.com/ekacs/inaportnetAnalytics.git
cd inaportnetAnalytics
```

---

### Langkah 2: Buat dan Aktifkan Virtual Environment

Sangat disarankan menggunakan virtual environment agar dependensi proyek terisolasi:

#### Di Windows (PowerShell):

```powershell
python -m venv inaportnetDashboard\venv
.\inaportnetDashboard\venv\Scripts\Activate.ps1
```

> [!TIP]
> Jika muncul pesan *execution policy error* di PowerShell, jalankan perintah ini sekali:
>
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### Di Windows (Command Prompt `cmd`):

```cmd
python -m venv inaportnetDashboard\venv
inaportnetDashboard\venv\Scripts\activate.bat
```

#### Di Linux / macOS (Bash / Zsh):

```bash
python3 -m venv inaportnetDashboard/venv
source inaportnetDashboard/venv/bin/activate
```

---

### Langkah 3: Pasang Pustaka Dependensi

Pastikan virtual environment telah aktif, lalu pasang paket dependensi dari file `requirements.txt`:

```bash
cd inaportnetDashboard
pip install --upgrade pip
pip install -r requirements.txt
```

> [!NOTE]
> Dependensi utama yang dipasang mencakup: `streamlit`, `pandas`, `plotly`, `requests`, `supabase`, `openpyxl`, `lxml`, `scipy`, `numpy`, `scikit-learn`, `statsmodels`, dan `python-dotenv`.

---

## 🚀 Panduan Penggunaan Dashboard (Langkah demi Langkah)

### 1. Menjalankan Server Dashboard

Pastikan terminal berada di direktori `inaportnetDashboard`, lalu ketik:

```powershell
python -m streamlit run app.py
```

Setelah perintah dijalankan, browser Anda akan otomatis membuka alamat:
🌐 **`http://localhost:8501`**

---

### 2. Alur Kerja Penggunaan Aplikasi

```
  [ Beranda ] ──► Status Sistem & Ringkasan Eksekutif
       │
       ▼
 [ 1. Data Collection ] ──► Scraping Portal / Upload Data / Cek Kualitas Data (QC)
       │
       ├─────────────────────────┬─────────────────────────┬─────────────────────────┐
       ▼                         ▼                         ▼                         ▼
[ 3. Traffic ]           [ 4. Performance ]       [ 5. Classification ]      [ 6. Fraud Screening ]
Pola & Tren Volume      Kepatuhan Ambang SLA     Matriks 4 Kuadran & CPI    Model CFRSI & EWS Audit
```

#### Tahap A: Halaman Beranda (`app.py`)

- Memeriksa status koneksi database (SQLite lokal aktif secara otomatis).
- Melihat ringkasan eksekutif capaian transaksi nasional.
- Menavigasi ke fitur-fitur analisis melalui menu sidebar atau kartu navigasi di halaman utama.

#### Tahap B: Pengumpulan & Validasi Data (`1_📊_Data_Collection.py`)

Anda dapat menyediakan data ke dalam sistem melalui salah satu dari cara berikut:

1. **Scraping Portal Inaportnet**:
   - Buka tab **Scraping Data**.
   - Pilih kode pelabuhan, jenis angkutan (Dalam Negeri / Luar Negeri), serta rentang bulan.
   - Klik **Mulai Scraping**. Anda dapat memanfaatkan tombol **Jeda (Pause)** atau **Stop** sewaktu-waktu.
2. **Unggah File Lokal**:
   - Buka tab **Upload File**.
   - Unggah file berekstensi `.csv`, `.xlsx`, atau `.parquet`.
   - File fisik akan langsung dicadangkan secara otomatis ke folder `./data/`.
3. **Memuat dari Database**:
   - Buka tab **Load dari Database** untuk memuat transaksi yang tersimpan di SQLite atau Supabase.
4. **Inspeksi Kualitas Data (Data Quality QC)**:
   - Gulir ke bawah pada halaman Data Collection untuk melihat ringkasan kualitas data: *Error*, *Null*, dan *Duplikat*.
   - Klik tombol **🚨 Lihat Transaksi Error**, **🚫 Lihat Transaksi Null**, atau **🔄 Lihat Duplikat** untuk meninjau baris data bermasalah dan mengunduhnya dalam format `.csv`.

#### Tahap C: Analisis Pola Lalu Lintas (`3_🚦_Traffic_Overview.py`)

- Gunakan dropdown pelabuhan di bilah sisi kiri (*sidebar*) jika ingin memfokuskan analisis pada satu pelabuhan.
- Telaah kontribusi volume pelabuhan pada grafik donat persentase nasional.
- Pantau dinamika tren waktu pada grafik Kuartalan, Bulanan, Harian, dan 24 Jam harian.

#### Tahap D: Evaluasi SLA & Kinerja Layanan (`4_📋_Service_Performance.py`)

- Sesuaikan slider **Target SLA (menit)** (misalnya 15 mnt, 30 mnt, atau 60 mnt) untuk melihat persentase kepatuhan secara *real-time*.
- Amati sebaran distribusi waktu layanan pada bagan histogram.
- Periksa daftar pelabuhan pada tabel **Top 10 Pelabuhan Terlama** sebagai bahan audit perbaikan alur pelayanan.

#### Tahap E: Pemetaan Kuadran Pelabuhan (`5_🗺️_Port_Classification.py`)

- Amati posisi kuadran operasional masing-masing pelabuhan pada grafik scatter interaktif.
- Pelajari rincian 4 sub-indeks performa: Kepatuhan, Efisiensi, Konsistensi, dan Ketahanan.
- Manfaatkan tabel pemeringkatan **Composite Performance Index (CPI)** untuk pembandingan kinerja antar pelabuhan se-Indonesia.

#### Tahap F: Skrining Risiko Fraud & EWS (`6_🛡️_Fraud_Risk_Screening.py`)

- Jika belum memuat data, klik tombol **🎲 Generate Benchmark Dataset (257 Pelabuhan)** untuk langsung menyimulasikan data nasional.
- **Tab 1 (CFRSI)**: Periksa peringkat pelabuhan dengan risiko tertinggi dan tinjau penerapan 4 Pilar Anti-Fraud.
- **Tab 2 (Rule-Based Red Flags)**: Telusuri porsi pelanggaran terhadap 5 kriteria regulasi (persetujuan kilat, durasi panjang, minim pengawasan, manipulasi GT, kapal ganda).
- **Tab 3 (Statistical & ML Anomalies)**: Telaah hasil deteksi outlier regresi OLS (Z-score residual ekstrem) dan model *Isolation Forest*.
- Klik **💾 Download Transaksi Outlier Statistik** atau **💾 Download Transaksi Anomali Multidimensi** untuk mengunduh daftar transaksi berindikasi anomali sebagai berkas kerja audit kepatuhan.

---

## 📜 Menjalankan Skrip Pipeline Riset (Standalone)

Selain antarmuka web dashboard, repositori ini menyediakan skrip Python mandiri pada folder `scripts/` untuk mereproduksi tahapan riset ilmiah:

```powershell
# Kembali ke direktori akar proyek
cd d:\Documents\inaportnetAnalytics

# 1. Menjalankan preprocessing dan perhitungan waktu persetujuan
python scripts/01_data_preprocessing.py

# 2. Menjalankan analisis statistik deskriptif
python scripts/02_descriptive_stats.py

# 3. Menghitung indeks kinerja layanan & tingkat kepatuhan SLA
python scripts/03_port_performance_calculation.py

# 4. Melakukan normalisasi Winsorized dan analisis 4 kuadran
python scripts/04_quadrant_analysis.py

# 5. Menjalankan engine CFRSI lengkap (Rule, Stat Z-Score, & Isolation Forest)
python scripts/05_fraud_risk_analysis.py
```

Hasil kalkulasi skrip akan disimpan dalam format grafik gambar pada folder `outputs/`.

---

## 🗄️ Konfigurasi Database (Dual-Mode)

### Mode 1: SQLite Lokal (Bawaan / Default)

Dashboard dikonfigurasi menggunakan SQLite lokal secara *out-of-the-box*. Berkas database tersimpan di:
`inaportnetDashboard/data/inaportnet_local.db`
Tidak diperlukan konfigurasi akun atau jaringan internet untuk menjalankan mode ini.

### Mode 2: Supabase Cloud PostgreSQL (Opsional)

Jika Anda ingin menyinkronkan data antar anggota tim di cloud:

1. Daftarkan proyek baru di [Supabase](https://supabase.com/).
2. Buka menu **SQL Editor** pada dashboard Supabase Anda, lalu eksekusi isi berkas `inaportnetDashboard/supabase_schema.sql`.
3. Hubungkan ke dashboard dengan salah satu opsi:
   - **Melalui Tampilan UI (Rekomendasi):** Buka dashboard Streamlit, klik tombol **Konfigurasi Supabase** pada sidebar, masukkan URL dan Anon Key proyek Anda, lalu klik **Hubungkan**.
   - **Melalui Berkas Rahasia:** Buat berkas `inaportnetDashboard/.streamlit/secrets.toml`:
     ```toml
     SUPABASE_URL = "https://your-project-id.supabase.co"
     SUPABASE_KEY = "your-anon-api-key"
     ```

---

## 🛠️ Tech Stack & Dependensi

| Lapisan / Komponen           | Teknologi                      | Deskripsi                                            |
| :--------------------------- | :----------------------------- | :--------------------------------------------------- |
| **Framework UI**       | Streamlit                      | Antarmuka interaktif berbasis Python                 |
| **Visualisasi Data**   | Plotly Express & Graph Objects | Grafik interaktif (donut, line, bar, scatter matrix) |
| **Pengolahan Data**    | Pandas & NumPy                 | Manipulasi matriks, pembersihan data, & agregasi     |
| **Machine Learning**   | Scikit-Learn                   | Deteksi anomali multidimensi*Isolation Forest*     |
| **Analisis Statistik** | Statsmodels & SciPy            | Regresi OLS, estimasi MAD, & Modified Z-Score        |
| **Penyimpanan Lokal**  | SQLite3                        | Database lokal dengan dukungan indeksasi             |
| **Penyimpanan Cloud**  | Supabase (PostgreSQL)          | Layanan cloud database terdistribusi                 |
| **Web Scraping**       | Requests & LXML                | Penarikan data portal Inaportnet anti-deteksi        |

---

## 👥 Authors & Kontributor

Dikembangkan dengan dedikasi tinggi untuk modernisasi analitik logistik kemaritiman dan transparansi pelabuhan Indonesia:

* **Eka C. Setyawan** — [@ekacs](https://github.com/ekacs)
* **Rifki Wijaya** — [@rifkiwijaya12](https://github.com/rifkiwijaya12)

---

### ☕ Dukungan & Kontribusi

Jika platform atau publikasi riset ini bermanfaat bagi studi, pekerjaan, atau penelitian Anda:

- Berikan bintang (⭐) pada repositori ini di GitHub.
- Silakan ajukan *Issue* atau *Pull Request* untuk saran perbaikan dan penambahan fitur.
- Dukung penulis melalui tautan donasi / traktir kopi pada profil kontributor agar kami semakin semangat memperbarui dan mengembangkan inovasi analitik maritim Indonesia!
