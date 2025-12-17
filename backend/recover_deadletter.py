#!/usr/bin/env python3
"""
Recover messages from Service Bus dead letter queue back to main queue
"""
import asyncio
from azure.identity import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage
import json

NAMESPACE = "auditapp-staging-servicebus.servicebus.windows.net"
QUEUE_NAME = "document-processing"

async def recover_deadletter_messages():
    credential = DefaultAzureCredential()
    
    async with ServiceBusClient(
        fully_qualified_namespace=NAMESPACE,
        credential=credential
    ) as client:
        # Get dead letter queue receiver
        dlq_receiver = client.get_queue_receiver(
            queue_name=QUEUE_NAME,
            sub_queue="deadletter",
            max_wait_time=10
        )
        
        # Get main queue sender
        sender = client.get_queue_sender(queue_name=QUEUE_NAME)
        
        recovered_count = 0
        failed_count = 0
        
        print("🔍 Fetching messages from dead letter queue...")
        
        async with dlq_receiver, sender:
            messages = await dlq_receiver.receive_messages(max_message_count=100, max_wait_time=10)
            
            print(f"📬 Found {len(messages)} messages in dead letter queue")
            
            for msg in messages:
                try:
                    # Get message body
                    body_str = str(msg)
                    body = json.loads(body_str)
                    
                    print(f"  📄 Document: {body.get('document_id')}")
                    
                    # Create new message with same content
                    new_message = ServiceBusMessage(body_str)
                    
                    # Send to main queue
                    await sender.send_messages(new_message)
                    
                    # Complete (remove) from dead letter queue
                    await dlq_receiver.complete_message(msg)
                    
                    recovered_count += 1
                    print(f"    ✅ Recovered successfully")
                    
                except Exception as e:
                    print(f"    ❌ Error recovering message: {str(e)}")
                    failed_count += 1
                    # Abandon message in DLQ so it can be retried
                    try:
                        await dlq_receiver.abandon_message(msg)
                    except:
                        pass
        
        print(f"\n📊 Recovery Summary:")
        print(f"  ✅ Recovered: {recovered_count}")
        print(f"  ❌ Failed: {failed_count}")

if __name__ == "__main__":
    asyncio.run(recover_deadletter_messages())
