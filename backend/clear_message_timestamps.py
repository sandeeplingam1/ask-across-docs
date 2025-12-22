#!/usr/bin/env python3
"""Clear message_enqueued_at timestamps to allow re-triggering"""
import asyncio
from sqlalchemy import update
from app.database import Document
from app.db_session import AsyncSessionLocal, init_db

async def clear_timestamps(engagement_id):
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(Document)
            .where(Document.engagement_id == engagement_id)
            .where(Document.status == 'queued')
            .values(message_enqueued_at=None)
        )
        await session.commit()
        print(f"Cleared message_enqueued_at for {result.rowcount} documents")

if __name__ == "__main__":
    import sys
    engagement_id = sys.argv[1] if len(sys.argv) > 1 else "dce7c233-1969-4407-aeb0-85d8a5617754"
    asyncio.run(clear_timestamps(engagement_id))
