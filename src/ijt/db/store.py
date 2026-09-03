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
                short_hash TEXT,
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
        
        try:
            await db.execute("ALTER TABLE jobs ADD COLUMN short_hash TEXT")
        except aiosqlite.OperationalError:
            pass
            
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_short_hash ON jobs(short_hash)")
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_deadline ON jobs(deadline_year, deadline_month)")
        
        await db.commit()

async def get_db_connection(db_path: Path):
    return await aiosqlite.connect(db_path)

async def is_url_seen(db: aiosqlite.Connection, url_hash: str) -> bool:
    async with db.execute("SELECT 1 FROM seen_urls WHERE url_hash = ?", (url_hash,)) as cursor:
        return await cursor.fetchone() is not None

async def mark_url_seen(db: aiosqlite.Connection, url_hash: str, url: str, source: str):
    await db.execute(
        "INSERT OR IGNORE INTO seen_urls (url_hash, url, source) VALUES (?, ?, ?)",
        (url_hash, url, source)
    )
    await db.commit()

async def get_or_create_short_hash(db: aiosqlite.Connection, job_id: str) -> str:
    import string
    import random
    
    # Check if exists
    async with db.execute("SELECT short_hash FROM jobs WHERE id = ?", (job_id,)) as cursor:
        row = await cursor.fetchone()
        if row and row[0]:
            return row[0]
            
    chars = string.ascii_letters + string.digits
    while True:
        short_hash = "".join(random.choices(chars, k=2))
        try:
            # We don't insert here, just verify it's not taken.
            # It could theoretically race, but for a local CLI it's fine.
            async with db.execute("SELECT 1 FROM jobs WHERE short_hash = ?", (short_hash,)) as cursor:
                if not await cursor.fetchone():
                    return short_hash
        except aiosqlite.Error:
            pass

async def save_job(db: aiosqlite.Connection, job_id: str, job, folder_name: str, status: str = 'not_applied'):
    import json
    matched_keywords_json = json.dumps(job.matched_keywords) if job.matched_keywords else "[]"
    
    short_hash = await get_or_create_short_hash(db, job_id)
    job.short_hash = short_hash
    
    await db.execute("""
        INSERT OR REPLACE INTO jobs 
        (id, title, company, location, url, source, description, deadline_month, deadline_year, folder_name, short_hash, relevance_score, matched_keywords, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id, job.title, job.company, job.location, job.url, job.source, 
        job.description, job.deadline_month, job.deadline_year, folder_name, short_hash,
        job.relevance_score, matched_keywords_json, status
    ))
    await db.commit()

async def update_job_status(db: aiosqlite.Connection, job_id: str, status: str):
    await db.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    await db.commit()
