#!/usr/bin/env python3
"""Manually send Service Bus messages for all queued documents"""
import asyncio
import sys
sys.path.insert(0, '/home/sandeep.lingam/app-project/Audit-App/backend')

from app.services.service_bus import get_service_bus
from app.db_session import get_session
from app.database import Document
from sqlalchemy import select

async def queue_all_documents(engagement_id: str):
    service_bus = get_service_bus()
    if not service_bus:
        print("ERROR: Service Bus not configured!")
        return
    
    session = next(get_session())
    
    try:
        # Get all queued documents
        result = await session.execute(
            select(Document).where(
                Document.engagement_id == engagement_id,
                Document.status == 'queued'
            )
        )
        queued_docs = result.scalars().all()
        
        print(f"Found {len(queued_docs)} queued documents")
        
        for doc in queued_docs:
            try:
                await service_bus.send_document_message(str(doc.engagement_id), str(doc.id))
                print(f"✅ Queued: {doc.filename}")
            except Exception as e:
                print(f"❌ Failed: {doc.filename} - {e}")
        
        print(f"\n✅ Successfully queued {len(queued_docs)} documents")
        
    finally:
        session.close()

if __name__ == "__main__":
    engagement_id = sys.argv[1] if len(sys.argv) > 1 else "dce7c233-1969-4407-aeb0-85d8a5617754"
    asyncio.run(queue_all_documents(engagement_id))
