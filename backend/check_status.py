#!/usr/bin/env python3
"""Check document status"""
import asyncio
import sys
sys.path.insert(0, '/home/sandeep.lingam/app-project/Audit-App/backend')

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Document
from app.config import settings

async def check_status():
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    engagement_id = "9e14e877-aeb2-40df-9d7c-a0f34a28e00b"
    
    async with AsyncSessionLocal() as session:
        # Count by status
        result = await session.execute(
            select(Document.status, func.count(Document.id))
            .where(Document.engagement_id == engagement_id)
            .group_by(Document.status)
        )
        print("\n📊 Document Status:")
        for status, count in result:
            print(f"  {status}: {count}")
        
        # Show failed documents
        result = await session.execute(
            select(Document.filename, Document.status, Document.processing_attempts, Document.error_message)
            .where(Document.engagement_id == engagement_id, Document.status == 'failed')
            .limit(5)
        )
        docs = result.all()
        if docs:
            print("\n❌ Failed Documents:")
            for filename, status, attempts, error in docs:
                print(f"  {filename[:50]}: attempts={attempts}")
                if error:
                    print(f"    Error: {error[:100]}")
    
    await engine.dispose()

asyncio.run(check_status())
