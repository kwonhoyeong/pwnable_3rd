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

