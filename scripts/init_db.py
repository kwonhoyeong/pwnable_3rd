#!/usr/bin/env python3
"""SQLite 데이터베이스 초기화 스크립트(SQLite database initialization script)."""
import asyncio
import sqlite3
from pathlib import Path

from common_lib.config import get_settings


async def init_database() -> None:
    """데이터베이스 초기화(Initialize database)."""
    settings = get_settings()
    db_url = settings.postgres_dsn

    # sqlite+aiosqlite:///./data/threatdb.sqlite -> ./data/threatdb.sqlite
    if "sqlite" in db_url:
        db_path = db_url.split("///", 1)[1] if "///" in db_url else "data/threatdb.sqlite"
    else:
        raise ValueError(f"Unsupported database URL: {db_url}")

    # 데이터베이스 디렉토리 생성
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # SQL 스크립트 읽기
    sql_file = Path(__file__).parent.parent / "database" / "init-db.sqlite.sql"
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL initialization script not found: {sql_file}")

    with open(sql_file, "r", encoding="utf-8") as f:
        sql_script = f.read()

    # SQLite 데이터베이스 초기화
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql_script)
        conn.commit()
        print(f"✓ Database initialized successfully: {db_path}")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(init_database())
