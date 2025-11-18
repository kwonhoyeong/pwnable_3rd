-- EPSS 점수 테이블(EPSS score table)
CREATE TABLE IF NOT EXISTS epss_scores (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL UNIQUE,
    epss_score NUMERIC(5,4),
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
