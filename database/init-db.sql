-- 초기 스키마 및 샘플 데이터 초기화 스크립트(Initial schema and seed data script)
-- Postgres 컨테이너가 시작될 때 자동 실행됩니다.

-- 패키지-CVE 매핑 테이블(Package-CVE mapping table)
CREATE TABLE IF NOT EXISTS package_cve_mapping (
    id SERIAL PRIMARY KEY,
    package TEXT NOT NULL,
    version_range TEXT NOT NULL,
    cve_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (package, version_range)
);

-- 수집 대기 큐 테이블(Collection queue table)
CREATE TABLE IF NOT EXISTS package_scan_queue (
    id SERIAL PRIMARY KEY,
    package TEXT NOT NULL,
    version_range TEXT NOT NULL,
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
    recommendations TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    analysis_summary TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 샘플 데이터 삽입(Seed sample data)
INSERT INTO package_cve_mapping (package, version_range, cve_ids)
VALUES ('lodash', '<4.17.21', ARRAY['CVE-2023-1234', 'CVE-2022-5678'])
ON CONFLICT (package, version_range) DO NOTHING;

INSERT INTO package_scan_queue (package, version_range, processed)
VALUES ('lodash', '<4.17.21', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO epss_scores (cve_id, epss_score, collected_at)
VALUES ('CVE-2023-1234', 0.8700, NOW())
ON CONFLICT (cve_id) DO NOTHING;

INSERT INTO threat_cases (cve_id, package, version_range, cases)
VALUES (
    'CVE-2023-1234',
    'lodash',
    '<4.17.21',
    '[{"source": "https://example.com/exploit-detail", "title": "Exploitation of CVE-2023-1234 in lodash", "date": "2025-10-10", "summary": "Attackers chained vulnerabilities to achieve remote code execution."}]'
        ::JSONB
)
ON CONFLICT (cve_id, package, version_range) DO NOTHING;

INSERT INTO analysis_results (cve_id, risk_level, recommendations, analysis_summary, generated_at)
VALUES (
    'CVE-2023-1234',
    'High',
    ARRAY['Upgrade lodash to 4.17.21 or later', 'Review transitive dependencies for vulnerable versions'],
    'Lodash versions below 4.17.21 exhibit a high-risk vulnerability with observed exploitation cases.',
    NOW()
)
ON CONFLICT (cve_id) DO NOTHING;
