---
slug: upload-save-to-data-dir
status: approved
intent: clear
classification: trivial
created: 2026-09-12
---

# Upload Save to Data Dir Work Plan

## TL;DR (For humans)

**Apa:** Tombol upload di halaman Data Collection saat ini hanya memasukkan data ke SQLite — file asli tidak disimpan ke disk. Rencana ini menambahkan penyimpanan file asli ke folder `./data/` sebagai backup lokal.

**Mengapa:** User ingin file hasil upload tetap tersimpan secara fisik di lokal, bukan hanya datanya di database. Ini penting untuk audit trail, re-upload, dan troubleshooting.

**Cara:** Tambahkan blok kode ~10 baris setelah parsing berhasil (sebelum section Preview) yang menyimpan file asli ke `./data/` menggunakan `open(..., "wb")`. Non-fatal — error hanya warning, tidak menggagalkan proses insert database.

**Tidak untuk:** Tidak mengubah scraping tab. Tidak mengubah insert database logic. Tidak menghapus atau memodifikasi flow yang ada.

**Effort:** ~5 menit, 1 file, ~10 baris kode baru.

**Risk:** Sangat rendah. Code addition-only, tidak ada yang berubah. `./data/` directory sudah ada.

---

## Scope

### In Scope
- `pages/1_📊_Data_Collection.py` — tambahkan file-save logic setelah parsing berhasil

### Out of Scope
- Scraping tab (tidak diubah)
- Supabase upload flow (tidak diubah)
- Database insert logic (tidak diubah)
- File dedup/naming conflict handling (N+1 enhancement, tidak diminta)

---

## Verification strategy

1. `py_compile` syntax check setelah edit
2. Manual review kode — pastikan `uploaded_file.seek(0)` dipanggil sebelum `getvalue()` (buffer safety)
3. Pastikan error handling non-fatal (try/except → warning, bukan error)

---

## Execution strategy

Single wave — 1 file, 1 edit, langsung ke verification.

---

## Todos

- [ ] 1. Tambahkan file-save block di Data Collection upload tab

**File:** `D:\Documents\inaportnetAnalytics\inaportnetDashboard\pages\1_📊_Data_Collection.py`

**Lokasi insert:** Setelah baris 403 (`st.success(...)` yang menampilkan "File berhasil dibaca") dan sebelum baris 405 (`Preview` section). Tepatnya sebelum `\n    Preview` yang merupakan expander preview.

**Kode yang ditambahkan (sisip sebelum baris 405):**

```python
        # ── Simpan file asli ke ./data untuk backup lokal ──
        try:
            _page_dir = os.path.dirname(os.path.abspath(__file__))
            _data_dir = os.path.join(_page_dir, "data")
            os.makedirs(_data_dir, exist_ok=True)
            _save_path = os.path.join(_data_dir, uploaded_file.name)
            uploaded_file.seek(0)
            with open(_save_path, "wb") as _f:
                _f.write(uploaded_file.getvalue())
            st.caption(f"💾 File tersimpan: `{_save_path}`")
        except Exception as _e:
            st.warning(f"⚠️ Gagal menyimpan file ke folder data: {_e}")
```

**Catatan path resolution:**
- File berada di `pages/1_📊_Data_Collection.py`
- `__file__` → `pages/1_📊_Data_Collection.py`
- `os.path.dirname(os.path.abspath(__file__))` → `pages/`
- `os.path.join(pages/, "data")` → `pages/data/` ← SALAH

**Perlu diperbaiki path:** harus `os.path.dirname` DUA kali untuk naik ke root project:
```python
            _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            _data_dir = os.path.join(_project_root, "data")
```
→ `pages/../../data` → `D:\Documents\inaportnetAnalytics\inaportnetDashboard\data` ✅

**Acceptance criteria:**
- [ ] `import os` sudah ada di file (sudah ditambahkan di fix sebelumnya)
- [ ] Setelah upload CSV/Excel/Parquet yang valid, file fisik muncul di `./data/<nama_file_upload>`
- [ ] Path yang ditampilkan di caption (`st.caption`) benar dan bisa diakses
- [ ] Jika terjadi error (permission, disk full), hanya muncul warning — insert database tetap berjalan
- [ ] `py_compile` passed tanpa error

**Happy path:** Upload file → parse sukses → file tersimpan di `./data/` → caption muncul → preview tampil → insert database berjalan.

**Failure path:** Upload file → parse sukses → gagal simpan disk (permission/disk full) → warning muncul → preview tetap tampil → insert database tetap berjalan (tidak terganggu).

**Commit:** `fix(upload): save uploaded file to ./data for local backup`

---

## Final verification wave

- [ ] F1. `python -m py_compile pages/1_📊_Data_Collection.py` — syntax OK
- [ ] F2. Review kode — pastikan `_project_root` menggunakan dua kali `dirname` (bukan satu)
- [ ] F3. Review kode — pastikan `try/except` bersifat non-fatal (warning saja, tidak raise/exit)

---

## Commit strategy

Single commit: `fix(upload): save uploaded file to ./data for local backup`

---

## Success criteria

- File yang di-upload via halaman Data Collection tersimpan secara fisik di `./data/<filename>`
- Proses insert database tidak terganggu oleh kegagalan penyimpanan file
- Tidak ada perubahan behavior existing (preview, validation, insert tetap sama)
