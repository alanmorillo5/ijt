import aiosqlite
from pathlib import Path

async def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                url TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                description TEXT,
                deadline_month INTEGER,
                deadline_year INTEGER,
                date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_tailored TIMESTAMP,
                status TEXT DEFAULT 'not_applied',
                folder_name TEXT,
                relevance_score REAL,
                matched_keywords TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seen_urls (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                source TEXT NOT NULL,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_deadline ON jobs(deadline_year, deadline_month)")
        
        await db.commit()

async def get_db_connection(db_path: Path):
    return await aiosqlite.connect(db_path)
