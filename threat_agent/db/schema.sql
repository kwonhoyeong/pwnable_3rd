-- 위협 사례 테이블(Threat cases table)
CREATE TABLE IF NOT EXISTS threat_cases (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL,
    package TEXT NOT NULL,
    version_range TEXT NOT NULL,
    cases JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cve_id, package, version_range)
);

