#!/usr/bin/env python3
"""
Clean reset: Update DB + send Service Bus messages using sync SDK
This runs locally but sends messages that workers in Azure will process
"""
import sys
sys.path.insert(0, '/home/sandeep.lingam/app-project/Audit-App/backend')

import asyncio
from datetime import datetime, UTC
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.identity import DefaultAzureCredential
import json
from app.database import Document
from app.config import settings

ENGAGEMENT_ID = "dce7c233-1969-4407-aeb0-85d8a5617754"
NAMESPACE = "auditapp-staging-servicebus.servicebus.windows.net"
QUEUE = "document-processing"

async def reset_and_queue():
    """Reset stuck documents and send Service Bus messages"""
    
    # 1. Reset DB to clean state
    engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    print("🔧 Step 1: Resetting stuck documents in database...")
    
    async with AsyncSessionLocal() as session:
        # Get stuck documents (processing or queued)
        result = await session.execute(
            select(Document).where(
                Document.engagement_id == ENGAGEMENT_ID,
                Document.status.in_(['processing', 'queued'])
            )
        )
        docs = result.scalars().all()
        
        if not docs:
            print("  ℹ️  No documents to reset")
            await engine.dispose()
            return []
        
        print(f"  Found {len(docs)} documents to reset")
        
        doc_ids = []
        for doc in docs:
            # Clean reset
            doc.status = 'queued'
            doc.processing_attempts = 0
            doc.lease_expires_at = None
            doc.error_message = None
            doc.updated_at = datetime.now(UTC)
            doc_ids.append((str(doc.id), doc.filename))
            print(f"    ✅ {doc.filename}")
        
        await session.commit()
        print(f"  ✅ Reset {len(docs)} documents to clean queued state")
    
    await engine.dispose()
    
    # 2. Send Service Bus messages using SYNC SDK (works with managed identity from local)
    print(f"\n📤 Step 2: Sending {len(doc_ids)} Service Bus messages...")
    
    credential = DefaultAzureCredential()
    
    # Use sync client (async has issues with managed identity locally)
    with ServiceBusClient(NAMESPACE, credential) as client:
        sender = client.get_queue_sender(QUEUE)
        
        with sender:
            sent = 0
            for doc_id, filename in doc_ids:
                try:
                    message_body = json.dumps({
                        "engagement_id": ENGAGEMENT_ID,
                        "document_id": doc_id
                    })
                    
                    message = ServiceBusMessage(message_body)
                    sender.send_messages(message)
                    sent += 1
                    print(f"    ✅ {sent}/{len(doc_ids)}: {filename}")
                    
                except Exception as e:
                    print(f"    ❌ {filename}: {e}")
            
            print(f"\n🎉 Successfully sent {sent}/{len(doc_ids)} messages!")
            
    return doc_ids

if __name__ == "__main__":
    print("🚀 Clean Reset & Queue\n")
    print(f"Engagement: {ENGAGEMENT_ID}")
    print(f"Target: All processing/queued documents\n")
    
    doc_ids = asyncio.run(reset_and_queue())
    
    if doc_ids:
        print("\n" + "="*60)
        print("✅ COMPLETE")
        print("="*60)
        print(f"\nReset {len(doc_ids)} documents and sent Service Bus messages")
        print("\n🔍 Monitor worker processing:")
        print("   az containerapp logs show \\")
        print("     --name auditapp-staging-worker \\")
        print("     --resource-group auditapp-staging-rg \\")
        print("     --follow")
        print("\n⏱️  Expected completion: ~15-30 minutes for all documents")
    else:
        print("\n✅ All documents already completed!")
