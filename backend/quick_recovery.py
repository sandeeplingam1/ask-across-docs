#!/usr/bin/env python3
"""
Quick script to reset documents and send Service Bus messages directly
"""
import asyncio
import os
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, '/home/sandeep.lingam/app-project/Audit-App/backend')

from app.database import Document
from app.config import settings

async def reset_and_queue():
    """Reset queued documents and return their IDs for manual Service Bus sending"""
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    engagement_id = "9e14e877-aeb2-40df-9d7c-a0f34a28e00b"
    
    async with AsyncSessionLocal() as session:
        # Get queued documents
        result = await session.execute(
            select(Document).where(
                Document.engagement_id == engagement_id,
                Document.status == 'queued'
            )
        )
        docs = result.scalars().all()
        
        if not docs:
            print("❌ No queued documents found")
            return []
        
        print(f"📋 Found {len(docs)} queued documents:")
        doc_ids = []
        
        for doc in docs:
            # Reset attempts
            doc.processing_attempts = 0
            doc.updated_at = datetime.utcnow()
            doc.error_message = None
            doc_ids.append((str(doc.id), doc.filename))
            print(f"  ✅ {doc.filename}: {doc.id}")
        
        await session.commit()
        print(f"\n✅ Reset {len(docs)} documents")
        
        return doc_ids
    
    await engine.dispose()

async def send_service_bus_messages(doc_ids, engagement_id):
    """Send Service Bus messages for document IDs"""
    from app.services.service_bus import get_service_bus
    
    service_bus = get_service_bus()
    if not service_bus:
        print("❌ Service Bus not configured")
        return
    
    print(f"\n📤 Sending {len(doc_ids)} messages to Service Bus...")
    
    sent = 0
    for doc_id, filename in doc_ids:
        try:
            await service_bus.send_document_message(engagement_id, doc_id)
            sent += 1
            print(f"  ✅ Sent message for: {filename}")
        except Exception as e:
            print(f"  ❌ Failed for {filename}: {e}")
    
    print(f"\n✅ Sent {sent}/{len(doc_ids)} messages successfully")

if __name__ == "__main__":
    engagement_id = "9e14e877-aeb2-40df-9d7c-a0f34a28e00b"
    
    print("🚀 Resetting documents and sending Service Bus messages...\n")
    
    # Reset documents
    doc_ids = asyncio.run(reset_and_queue())
    
    if doc_ids:
        # Send Service Bus messages
        asyncio.run(send_service_bus_messages(doc_ids, engagement_id))
        
        print("\n✅ Recovery complete!")
        print("🔍 Monitor worker logs with:")
        print("   az containerapp logs show --name auditapp-staging-worker --resource-group auditapp-staging-rg --follow")
    else:
        print("\n❌ No documents to process")
