import asyncio
import aiosqlite
import string
import random

async def main():
    try:
        async with aiosqlite.connect("data/ijt.db") as db:
            async with db.execute("SELECT id FROM jobs WHERE short_hash IS NULL") as cursor:
                rows = await cursor.fetchall()
            
            chars = string.ascii_letters + string.digits
            for row in rows:
                job_id = row[0]
                while True:
                    short_hash = "".join(random.choices(chars, k=2))
                    async with db.execute("SELECT 1 FROM jobs WHERE short_hash = ?", (short_hash,)) as c:
                        if not await c.fetchone():
                            await db.execute("UPDATE jobs SET short_hash = ? WHERE id = ?", (short_hash, job_id))
                            break
            await db.commit()
            print(f"Updated {len(rows)} jobs.")
    except Exception as e:
        print(e)
asyncio.run(main())
