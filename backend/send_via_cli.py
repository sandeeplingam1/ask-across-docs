"""
Send Service Bus messages using Azure CLI (works from authenticated shell)
This creates messages that trigger the workers with lock renewal
"""
import json
import subprocess

ENGAGEMENT_ID = "dce7c233-1969-4407-aeb0-85d8a5617754"
NAMESPACE = "auditapp-staging-servicebus"
QUEUE = "document-processing"
RESOURCE_GROUP = "auditapp-staging-rg"

# Document IDs from DB (16 documents we just reset)
DOC_IDS = [
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
    "451b0638-69d7-4be2-b50f-e85ba3e70805",
    "9c59b2ce-eab9-4bde-9f6c-70bdf4d1b47f"
]

def send_message(doc_id):
    """Send a single Service Bus message using Azure CLI"""
    message_body = json.dumps({
        "engagement_id": ENGAGEMENT_ID,
        "document_id": doc_id
    })
    
    cmd = [
        "az", "servicebus", "queue", "send",
        "--namespace-name", NAMESPACE,
        "--name", QUEUE,
        "--resource-group", RESOURCE_GROUP,
        "--messages", message_body
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

if __name__ == "__main__":
    print(f"📤 Sending {len(DOC_IDS)} Service Bus messages via Azure CLI...\n")
    
    sent = 0
    failed = 0
    
    for i, doc_id in enumerate(DOC_IDS, 1):
        try:
            if send_message(doc_id):
                sent += 1
                print(f"  ✅ {i}/{len(DOC_IDS)}: {doc_id[:8]}...")
            else:
                failed += 1
                print(f"  ❌ {i}/{len(DOC_IDS)}: {doc_id[:8]}...")
        except Exception as e:
            failed += 1
            print(f"  ❌ {i}/{len(DOC_IDS)}: {e}")
    
    print(f"\n🎉 Sent {sent}/{len(DOC_IDS)} messages")
    
    if sent > 0:
        print("\n🔍 Monitor workers:")
        print("   az containerapp logs show --name auditapp-staging-worker --resource-group auditapp-staging-rg --follow")
