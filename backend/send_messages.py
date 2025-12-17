#!/usr/bin/env python3
"""Send Service Bus messages for queued documents using Azure SDK directly"""
import asyncio
from azure.identity import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
import json

NAMESPACE = "auditapp-staging-servicebus.servicebus.windows.net"
QUEUE_NAME = "document-processing"
ENGAGEMENT_ID = "dce7c233-1969-4407-aeb0-85d8a5617754"

# Document IDs from database query
QUEUED_DOCS = [
    "196509ac-b3cc-4dce-a59e-c18e0d42f7ca",
    "223c4f50-5acb-4eaf-9e4f-9088f3939998",
    "1845d7bf-afe2-45de-857b-2fd5dc5b3267",
    "3cd17e95-33bb-4e6d-a0eb-e13ebac2eb61",
    "e23fa01f-29c8-4cac-b4c8-61b13f1bffdb",
    "eddd5e66-0d6e-4c13-a9f8-44bc4b2d68e6",
    "f0e48ca6-b652-46a4-b7b3-ae23c4bd4f11",
    "02eea8bb-df88-486d-ab4e-ed8f7b5e1c75",
    "9e98f4e9-2d97-4dbb-9cf5-92f8ad97e4ad",
    "bb5e54bc-e6f7-4f61-a9fa-c45de3f15f66",
    "54ee0951-1a0e-45fc-88ce-84e5f82f9b26",
    "d7ed8aa3-b1df-4d8a-9c14-42a5ffde52b1",
    "2e5b0d2b-6f45-4bd5-8eae-bfba37b19f1f",
    "39d83036-8eec-43fc-8ce1-c9fcac84a9b4",
    "451b0638-69d7-4be2-b50f-e85ba3e70805"
]

async def send_messages():
    credential = DefaultAzureCredential()
    
    async with ServiceBusClient(NAMESPACE, credential) as client:
        sender = client.get_queue_sender(QUEUE_NAME)
        
        async with sender:
            sent = 0
            for doc_id in QUEUED_DOCS:
                try:
                    message_body = json.dumps({
                        "engagement_id": ENGAGEMENT_ID,
                        "document_id": doc_id
                    })
                    
                    message = ServiceBusMessage(message_body)
                    await sender.send_messages(message)
                    sent += 1
                    print(f"✅ Sent message {sent}/{len(QUEUED_DOCS)}: {doc_id[:8]}...")
                    
                    # Small delay to avoid throttling
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"❌ Failed for {doc_id}: {e}")
            
            print(f"\n🎉 Successfully sent {sent}/{len(QUEUED_DOCS)} messages!")
            print("\n🔍 Monitor worker logs:")
            print("   az containerapp logs show --name auditapp-staging-worker --resource-group auditapp-staging-rg --follow")

if __name__ == "__main__":
    print("📤 Sending Service Bus messages for 15 queued documents...\n")
    asyncio.run(send_messages())
