-- 초기 스키마 및 샘플 데이터 초기화 스크립트(Initial schema and seed data script)
-- SQLite용 데이터베이스 초기화 스크립트

-- 패키지-CVE 매핑 테이블(Package-CVE mapping table)
CREATE TABLE IF NOT EXISTS package_cve_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package TEXT NOT NULL,
    version_range TEXT NOT NULL,
    ecosystem TEXT NOT NULL DEFAULT 'npm',
    cve_ids TEXT NOT NULL DEFAULT '[]',  -- JSON array
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (package, version_range, ecosystem)
);

-- 수집 대기 큐 테이블(Collection queue table)
CREATE TABLE IF NOT EXISTS package_scan_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package TEXT NOT NULL,
    version_range TEXT NOT NULL,
    ecosystem TEXT NOT NULL DEFAULT 'npm',
    processed INTEGER NOT NULL DEFAULT 0,  -- BOOLEAN -> INTEGER (0/1)
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- EPSS 점수 테이블(EPSS score table)
CREATE TABLE IF NOT EXISTS epss_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cve_id TEXT NOT NULL UNIQUE,
    epss_score REAL,
    collected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CVSS 점수 테이블(CVSS score table)
CREATE TABLE IF NOT EXISTS cvss_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cve_id TEXT NOT NULL UNIQUE,
    cvss_score REAL,
    severity TEXT,
    collected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 위협 사례 테이블(Threat cases table)
CREATE TABLE IF NOT EXISTS threat_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cve_id TEXT NOT NULL,
    package TEXT NOT NULL,
    version_range TEXT NOT NULL,
    cases TEXT NOT NULL DEFAULT '[]',  -- JSON
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cve_id, package, version_range)
);

-- 분석 결과 테이블(Analysis results table)
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cve_id TEXT NOT NULL UNIQUE,
    risk_level TEXT NOT NULL,
    risk_score REAL,
    recommendations TEXT NOT NULL DEFAULT '[]',  -- JSON array
    analysis_summary TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 샘플 데이터 삽입(Seed sample data)
INSERT OR IGNORE INTO package_cve_mapping (package, version_range, ecosystem, cve_ids)
VALUES ('lodash', '<4.17.21', 'npm', '["CVE-2023-1234", "CVE-2022-5678"]');

INSERT OR IGNORE INTO package_scan_queue (package, version_range, ecosystem, processed)
VALUES ('lodash', '<4.17.21', 'npm', 1);

INSERT OR IGNORE INTO epss_scores (cve_id, epss_score, collected_at)
VALUES ('CVE-2023-1234', 0.8700, datetime('now'));

INSERT OR IGNORE INTO threat_cases (cve_id, package, version_range, cases)
VALUES (
    'CVE-2023-1234',
    'lodash',
    '<4.17.21',
    '[{"source": "https://example.com/exploit-detail", "title": "Exploitation of CVE-2023-1234 in lodash", "date": "2025-10-10", "summary": "Attackers chained vulnerabilities to achieve remote code execution."}]'
);

INSERT OR IGNORE INTO analysis_results (cve_id, risk_level, recommendations, analysis_summary, generated_at)
VALUES (
    'CVE-2023-1234',
    'High',
    '["Upgrade lodash to 4.17.21 or later", "Review transitive dependencies for vulnerable versions"]',
    'Lodash versions below 4.17.21 exhibit a high-risk vulnerability with observed exploitation cases.',
    datetime('now')
);
