-- 초기 스키마 및 샘플 데이터 초기화 스크립트(Initial schema and seed data script)
-- Postgres 컨테이너가 시작될 때 자동 실행됩니다.

-- 패키지-CVE 매핑 테이블(Package-CVE mapping table)
CREATE TABLE IF NOT EXISTS package_cve_mapping (
    id SERIAL PRIMARY KEY,
    package TEXT NOT NULL,
    version_range TEXT NOT NULL,
    ecosystem TEXT NOT NULL DEFAULT 'npm',
    cve_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (package, version_range, ecosystem)
);

-- 수집 대기 큐 테이블(Collection queue table)
CREATE TABLE IF NOT EXISTS package_scan_queue (
    id SERIAL PRIMARY KEY,
    package TEXT NOT NULL,
    version_range TEXT NOT NULL,
    ecosystem TEXT NOT NULL DEFAULT 'npm',
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- EPSS 점수 테이블(EPSS score table)
CREATE TABLE IF NOT EXISTS epss_scores (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL UNIQUE,
    epss_score NUMERIC(5,4),
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- CVSS 점수 테이블(CVSS score table)
CREATE TABLE IF NOT EXISTS cvss_scores (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL UNIQUE,
    cvss_score NUMERIC(4,1),
    vector TEXT,
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

-- 분석 결과 테이블(Analysis results table)
CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    cve_id TEXT NOT NULL UNIQUE,
    risk_level TEXT NOT NULL,
    risk_score NUMERIC(4,1) NOT NULL,
    recommendations TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    analysis_summary TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
