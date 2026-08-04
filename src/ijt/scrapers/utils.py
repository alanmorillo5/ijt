import asyncio
import hashlib
import random
from pathlib import Path

from ijt.db.store import get_db_connection

async def rate_limit(min_delay: float = 3.0, max_delay: float = 10.0):
    """Wait for a random duration between min_delay and max_delay seconds."""
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)

def get_url_hash(url: str) -> str:
    """Generate SHA-256 hash for a URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

async def is_url_seen(db_path: Path, url: str) -> bool:
    """Check if a URL has already been processed."""
    url_hash = get_url_hash(url)
    db = await get_db_connection(db_path)
    try:
        async with db.execute("SELECT 1 FROM seen_urls WHERE url_hash = ?", (url_hash,)) as cursor:
            result = await cursor.fetchone()
            return result is not None
    finally:
        await db.close()

async def mark_url_seen(db_path: Path, url: str, source: str):
    """Mark a URL as processed."""
    url_hash = get_url_hash(url)
    db = await get_db_connection(db_path)
    try:
        await db.execute(
            "INSERT OR IGNORE INTO seen_urls (url_hash, url, source) VALUES (?, ?, ?)",
            (url_hash, url, source)
        )
        await db.commit()
    finally:
        await db.close()
