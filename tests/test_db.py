import pytest
import asyncio
from pathlib import Path
from ijt.db.store import init_db, get_db_connection, is_url_seen, mark_url_seen, save_job
from ijt.scrapers.base import ScrapedJob

@pytest.mark.asyncio
async def test_db_operations(tmp_path):
    db_path = tmp_path / "data" / "ijt.db"
    await init_db(db_path)
    
    db = await get_db_connection(db_path)
    try:
        # Test seen URLs
        url = "https://example.com/job"
        hash_val = "12345"
        
        assert not await is_url_seen(db, hash_val)
        await mark_url_seen(db, hash_val, url, "linkedin")
        assert await is_url_seen(db, hash_val)
        
        # Test jobs
        job = ScrapedJob(
            title="SWE", company="Google", location="Remote", url=url,
            source="linkedin", description="Desc", posted_date=None,
            deadline_month=12, deadline_year=2026, requirements=[]
        )
        job.relevance_score = 0.95
        job.matched_keywords = ["Python"]
        
        await save_job(db, "job123", job, "Google_SWE_2026", "not_applied")
        
        async with db.execute("SELECT status, relevance_score FROM jobs WHERE id=?", ("job123",)) as cursor:
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "not_applied"
            assert row[1] == 0.95
    finally:
        await db.close()
