import asyncio
from sqlalchemy import text
from common_lib.db import get_engine

async def migrate():
    print("Starting migration...")
    engine = await get_engine()
    if not engine:
        print("Failed to get database engine.")
        return

    async with engine.begin() as conn:
        print("Adding risk_score column to analysis_results table...")
        try:
            # Add column if it doesn't exist
            await conn.execute(text(
                "ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS risk_score NUMERIC(4,1) DEFAULT 0.0"
            ))
            print("Migration successful.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
