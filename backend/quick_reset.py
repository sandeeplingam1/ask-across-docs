#!/usr/bin/env python3
"""
Quick script to reset stuck documents via API
Uses direct HTTP calls to reset documents
"""
import requests
import json

BACKEND_URL = "https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io"
ENGAGEMENT_ID = "dce7c233-1969-4407-aeb0-85d8a5617754"

def main():
    print("=== RESETTING STUCK DOCUMENTS ===")
    print(f"Engagement: {ENGAGEMENT_ID}")
    print()
    
    # Get current document status
    print("Current status:")
    response = requests.get(f"{BACKEND_URL}/api/engagements/{ENGAGEMENT_ID}/documents")
    docs = response.json()
    
    status_counts = {}
    for doc in docs:
        status = doc.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(json.dumps(status_counts, indent=2))
    print()
    
    # Call reset endpoint
    print("Calling reset endpoint...")
    response = requests.post(
        f"{BACKEND_URL}/api/engagements/{ENGAGEMENT_ID}/reset-stuck?hours_stuck=1"
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS!")
        print(json.dumps(result, indent=2))
    else:
        print(f"❌ ERROR {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    main()
