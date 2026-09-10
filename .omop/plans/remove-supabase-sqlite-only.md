# Plan: Hapus Supabase, SQLite-Only + Renumber Pages

## Summary
Refactor seluruh aplikasi Inaportnet Analytics Dashboard untuk menghapus semua integrasi Supabase. Default dan satu-satunya database adalah SQLite lokal. Renumber halaman sesuai urutan baru.

## Outcome
- Tidak ada kode Supabase tersisa di codebase
- Database = SQLite lokal saja
- Database Viewer berfungsi: tampilkan data lokal, bersihkan duplikat lokal, muat ke sesi analisis
- Urutan halaman: 1-Data Collection, 2-Database Viewer, 3-Traffic Overview, 4-Service Performance, 5-Port Classification, 6-Fraud Risk Screening

---

## Step 1: Rename Files — Urutan Halaman Baru

Rename file agar sesuai urutan yang diminta. Streamlit menampilkan halaman berdasarkan nama file (alphabetical/numbered prefix).

| File Lama | File Baru |
|-----------|-----------|
| `1_📊_Data_Collection.py` | `1_📊_Data_Collection.py` (tetap) |
| `5_🗄️_Database_Viewer.py` | `2_🗄️_Database_Viewer.py` |
| `2_🚦_Traffic_Overview.py` | `3_🚦_Traffic_Overview.py` |
| `3_📋_Service_Performance.py` | `4_📋_Service_Performance.py` |
| `4_🗺️_Port_Classification.py` | `5_🗺️_Port_Classification.py` |
| `6_🛡️_Fraud_Risk_Screening.py` | `6_🛡️_Fraud_Risk_Screening.py` (tetap) |

**Tools**: `git mv` via PowerShell.

---

## Step 2: `modules/database.py` — Hapus Semua Supabase

Hapus/barikan fungsi/fungsi berikut:

| Fungsi/Variabel | Aksi |
|-----------------|------|
| `set_supabase_credentials()` (line 70) | **HAPUS** |
| `clear_supabase_credentials()` (line 89) | **HAPUS** |
| `get_supabase_client()` (line 96) | **HAPUS** |
| `is_supabase_connected()` (line 118) | **HAPUS** |
| `is_connected()` (line 130) | **SIMPLIFY**: selalu return `True` |
| `insert_pkk_records()` (line 370) | **SIMPLIFY**: hapus branch supabase, hanya panggil `_insert_pkk_records_sqlite()` |
| `_insert_pkk_records_supabase()` (line 571) | **HAPUS** |
| `_fetch_pkk_records_supabase()` (line 462) | **HAPUS** |
| `fetch_pkk_records_paginated()` | **SIMPLIFY**: hapus branch supabase, hanya panggil SQLite |
| `delete_all_supabase_records()` (line 653) | **HAPUS** |
| `delete_pkk_records()` | **SIMPLIFY**: hapus branch supabase |
| `get_database_stats()` | **SIMPLIFY**: hapus branch supabase |
| `get_available_ports_from_db()` | **SIMPLIFY**: hapus branch supabase |
| `fetch_pkk_records()` | **SIMPLIFY**: hapus branch supabase |
| `source` param di semua fungsi | **HAPUS** — tidak perlu lagi |

Setelah bersih, ubah docstring `modules/database.py` dari "Supabase atau SQLite" menjadi hanya "SQLite lokal".

**Import**: Hapus `streamlit` dari import database.py jika tidak dibutuhkan lagi.

---

## Step 3: `app.py` — Hapus Supabase dari Homepage & Sidebar

| Item | Aksi |
|------|------|
| Import `is_supabase_connected`, `get_db_status_info`, `clear_supabase_credentials` | Hapus semua kecuali `is_connected`, `get_database_stats` |
| Settings modal Supabase (URL + API Key + tombol test koneksi) | **HAPUS** seluruhnya |
| Sidebar navigation — update path ke file baru | Update path: `2_🗄️_Database_Viewer.py`, `3_🚦_Traffic_Overview.py`, `4_📋_Service_Performance.py`, `5_🗺️_Port_Classification.py` |
| Status "Database Aktif" | Tampilkan "SQLite Lokal" saja (tidak perlu deteksi Supabase) |
| Auto-clear session jika database kosong | Pertahankan (sudah benar) |

---

## Step 4: `pages/1_📊_Data_Collection.py` — Hapus Supabase

| Item | Aksi |
|------|------|
| Import Supabase functions | Hapus semua kecuali `is_connected`, `insert_pkk_records` |
| Settings modal Supabase | **HAPUS** |
| Radio "Simpan ke Supabase / SQLite" saat upload | **HAPUS** — selalu SQLite |
| Radio "Sumber Data" saat load dari DB | **HAPUS** — selalu SQLite |
| Branch `source="supabase"` di semua panggilan | **HAPUS** |
| Tombol "Muat Sesi Analisis" | Pertahankan, tetap berfungsi |
| Delete section — hapus branch Supabase | **HAPUS** |
| Sidebar navigation — update path | Update ke file baru |
| Auto-clear session | Pertahankan |

---

## Step 5: `pages/2_🗄️_Database_Viewer.py` (baru) — SQLite Only

| Item | Aksi |
|------|------|
| Import Supabase functions | Hapus semua kecuali `is_connected`, `get_database_stats`, `fetch_pkk_records_paginated`, `check_and_clean_db_duplicates`, `get_available_ports_from_db` |
| Radio "Sumber Data" (SQLite/Supabase) | **HAPUS** — selalu SQLite |
| Sidebar navigation — update path | Update ke file baru |
| "Muat Sesi Analisis" button | Pertahankan — load data ke `st.session_state["df"]` |
| "Bersihkan Duplikat" button | Pertahankan — panggil `check_and_clean_db_duplicates()` (SQLite only) |
| Download section | Pertahankan — selalu dari SQLite |
| Update label "Supabase" → "SQLite Lokal" di semua teks | ✅ |
| Update `db_server_label` | Selalu "SQLite Lokal" |
| Auto-clear session jika database kosong | Pertahankan |

---

## Step 6: Pages 3-6 — Update Navigation & Hapus Supabase Refs

Untuk setiap halaman (`3_🚦_Traffic_Overview.py`, `4_📋_Service_Performance.py`, `5_🗺️_Port_Classification.py`, `6_🛡️_Fraud_Risk_Screening.py`):

| Item | Aksi |
|------|------|
| Sidebar navigation `page_link` paths | Update ke file baru |
| Auto-clear session jika database kosong | Pertahankan |
| Teks referensi "Supabase" | Ganti ke "SQLite Lokal" |
| Import Supabase functions | Hapus jika ada |

---

## Step 7: Bersihkan Sisa-Sisa

| Item | Aksi |
|------|------|
| `modules/database.py` docstring | Update deskripsi |
| `get_db_status_info()` | Hapus atau simplify — selalu "SQLite Lokal" |
| `.streamlit/secrets.toml` template | Hapus referensi Supabase jika ada |
| Import `streamlit` di `database.py` | Cek apakah masih dibutuhkan |

---

## Step 8: Verifikasi

1. **Syntax check**: `python -m py_compile` semua file `.py` yang diubah
2. **AppTest**: Jalankan `st.testing.AppTest` pada halaman 1 (upload+save) dan halaman 2 (view+delete)
3. **Manual check**: Pastikan tidak ada referensi "Supabase" tersisa (grep)

---

## File yang Berubah

| File | Estimasi Perubahan |
|------|-------------------|
| `modules/database.py` | **BESAR** — hapus ~400 baris kode Supabase |
| `app.py` | **SEDANG** — hapus settings modal, update nav |
| `pages/1_📊_Data_Collection.py` | **BESAR** — hapus radio Supabase, auto-save SQLite |
| `pages/2_🗄️_Database_Viewer.py` | **BARU** (rename dari 5) + **SEDANG** |
| `pages/3_🚦_Traffic_Overview.py` | **KECIL** — update nav paths |
| `pages/4_📋_Service_Performance.py` | **KECIL** — update nav paths |
| `pages/5_🗺️_Port_Classification.py` | **KECIL** — update nav paths |
| `pages/6_🛡️_Fraud_Risk_Screening.py` | **KECIL** — update nav paths |

## Risiko

- **Tidak ada data loss**: SQLite lokal tidak terpengaruh oleh penghapusan kode Supabase
- **File rename**: Streamlit cache mungkin perlu clear (`st.cache_resource` invalidation)
- **Sidebar navigation**: Semua page_link harus diupdate secara konsisten

## Catatan Penting

- **TIDAK** menghapus file database SQLite yang ada
- **TIDAK** mengubah struktur tabel `pkk_records`
- **TIDAK** mengubah algoritma analisis fraud (CFRSI)
- File `port_code.xlsx` tetap dipertahankan
