-- CVSS 점수 테이블(CVSS score table)
CREATE TABLE IF NOT EXISTS cvss_scores (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL UNIQUE,
    cvss_score NUMERIC(4,1),
    vector TEXT,
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
