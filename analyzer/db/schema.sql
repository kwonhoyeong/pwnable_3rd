-- 분석 결과 테이블(Analysis results table)
CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL UNIQUE,
    risk_level TEXT NOT NULL,
    recommendations TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    analysis_summary TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

