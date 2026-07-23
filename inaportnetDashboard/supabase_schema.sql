-- ============================================================
-- INAPORTNET ANALYTICS — Supabase Schema
-- Jalankan script ini di Supabase SQL Editor
-- ============================================================

-- Tabel utama data PKK
CREATE TABLE IF NOT EXISTS pkk_records (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    port_code       TEXT NOT NULL,
    port            TEXT NOT NULL,
    pkk_number      TEXT UNIQUE NOT NULL,
    vessel_name     TEXT,
    service         TEXT,
    submission      TIMESTAMPTZ,
    response        TIMESTAMPTZ,
    simpadu         TEXT,
    gmt             TEXT,
    approval_hours  FLOAT,
    approval_minutes FLOAT,
    year            INTEGER,
    quarter         TEXT,
    month           INTEGER,
    date            DATE,
    day             TEXT,
    hour            INTEGER,
    angkutan        TEXT,   -- 'dn' (domestik) atau 'ln' (luar negeri)
    scraped_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index untuk performa query
CREATE INDEX IF NOT EXISTS idx_pkk_port_code  ON pkk_records(port_code);
CREATE INDEX IF NOT EXISTS idx_pkk_year       ON pkk_records(year);
CREATE INDEX IF NOT EXISTS idx_pkk_month      ON pkk_records(month);
CREATE INDEX IF NOT EXISTS idx_pkk_angkutan   ON pkk_records(angkutan);

-- Log sesi scraping
CREATE TABLE IF NOT EXISTS scraping_log (
    id             UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    port_codes     TEXT[],
    angkutan       TEXT[],
    year           INTEGER,
    months         INTEGER[],
    started_at     TIMESTAMPTZ DEFAULT NOW(),
    completed_at   TIMESTAMPTZ,
    records_count  INTEGER DEFAULT 0,
    status         TEXT DEFAULT 'running'  -- 'running', 'completed', 'failed'
);

-- View: ringkasan per pelabuhan (opsional, untuk query cepat)
CREATE OR REPLACE VIEW port_summary_view AS
SELECT
    port_code,
    port,
    COUNT(*)                                            AS volume,
    AVG(approval_minutes)                              AS mean_approval_minutes,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY approval_minutes) AS median_approval_minutes,
    SUM(CASE WHEN approval_minutes < 31 THEN 1 ELSE 0 END)        AS sla_compliant,
    ROUND(
        SUM(CASE WHEN approval_minutes < 31 THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) * 100,
        2
    )                                                  AS sla_compliance_pct,
    MIN(year)                                          AS year_min,
    MAX(year)                                          AS year_max
FROM pkk_records
GROUP BY port_code, port;
