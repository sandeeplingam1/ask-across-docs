# Fix 1 + Fix 2 Implementation Summary

## Problem Diagnosis
**Root Cause:** Two independent problems causing document processing to hang:
1. **Duplicate Service Bus Messages**: Backend sends multiple messages for same document → workers receive duplicates → DB lease collision → abandon/retry loop → dead letter queue
2. **Stuck DB Leases**: Documents stuck in "processing" status with expired leases never get reset automatically → block progress forever

## Solutions Implemented

### Fix 1: Prevent Duplicate Service Bus Messages ✅
**Files Modified:**
- `backend/app/database.py`: Added `message_enqueued_at` column to track if message already sent
- `backend/app/routes/documents.py`: Modified `trigger_processing()` to only send messages if `message_enqueued_at == None`
- `backend/worker.py`: Clear `message_enqueued_at` flag in `release_lease()` when processing completes

**Logic:**
```python
# In trigger_processing():
# Only send message if no message already in queue
result = await session.execute(
    select(Document).where(
        Document.status == 'queued',
        Document.message_enqueued_at == None  # NEW: No duplicate tickets!
    )
)

for doc in queued_docs:
    await service_bus.send_document_message(...)
    doc.message_enqueued_at = datetime.utcnow()  # Mark sent
    
await session.commit()

# In worker release_lease():
# Clear flag when processing finishes
doc.message_enqueued_at = None
await session.commit()
```

### Fix 2: Janitor Auto-Reset Stuck Leases ✅
**Files Modified:**
- `backend/worker.py`: Added `janitor_clean_stuck_leases()` function and `janitor_loop()` background task

**Logic:**
```python
async def janitor_clean_stuck_leases(self):
    """Runs every 60 seconds to reset stuck documents"""
    now = datetime.utcnow()
    ten_minutes_ago = now - timedelta(minutes=10)
    
    for doc in processing_docs:
        # Rule 1: Lease expired
        if doc.lease_expires_at and doc.lease_expires_at < now:
            reset_to_queued()
        # Rule 2: Processing too long (>10 minutes)
        elif doc.processing_started_at and doc.processing_started_at < ten_minutes_ago:
            reset_to_queued()
```

## Database Migration Required

**File:** `backend/migrations/003_add_message_enqueued_at.sql`

```sql
ALTER TABLE documents ADD message_enqueued_at DATETIME NULL;
CREATE INDEX idx_documents_message_enqueued ON documents(message_enqueued_at);
```

**Run migration:**
```bash
export DB_PASSWORD="<get from Azure Key Vault>"
./run-migration.sh
```

## Deployment Instructions

### 1. Wait for ACR Builds to Complete
```bash
az acr task list-runs --registry auditappstagingacrwgjuafflp2o4o --top 2
```

### 2. Run Deployment Script
```bash
./deploy-fixes.sh
```

This will:
- Deploy backend with Fix 1 (prevent duplicate tickets)
- Deploy worker with Fix 1 + Fix 2 (janitor)

### 3. Run Database Migration
```bash
export DB_PASSWORD="<password>"
./run-migration.sh
```

### 4. Reset & Trigger Processing
```bash
BACKEND_URL="https://auditapp-staging-backend.graydune-dadabae1.eastus.azurecontainerapps.io"
ENGAGEMENT_ID="3706871a-d3fb-4c11-8e69-5347f14b572f"

# Reset stuck documents
curl -X POST "$BACKEND_URL/api/engagements/$ENGAGEMENT_ID/documents/reset-stuck"

# Trigger processing
curl -X POST "$BACKEND_URL/api/engagements/$ENGAGEMENT_ID/documents/trigger-processing"
```

### 5. Monitor Progress
```bash
# Watch worker logs
az containerapp logs show --name auditapp-staging-worker -g auditapp-staging-rg --follow

# Check document status
curl -s "$BACKEND_URL/api/engagements/$ENGAGEMENT_ID/documents" | jq '[.[] | {filename, status, attempts: .processing_attempts}]'
```

## Expected Behavior After Fixes

**Fix 1 Results:**
- ✅ No more duplicate Service Bus messages for same document
- ✅ Workers won't receive duplicate messages → no more lease collisions
- ✅ No more dead letter queue accumulation from lease collisions

**Fix 2 Results:**
- ✅ Stuck leases auto-reset every 60 seconds
- ✅ Documents with expired leases automatically return to "queued" status
- ✅ Processing continues automatically without manual intervention
- 🧹 Janitor logs: "🧹 Janitor: Resetting stuck doc <filename> (reason)"

**Overall:**
- Documents should progress from **24/41 → 41/41** completed
- No manual "reset-stuck" or "trigger-processing" calls needed after initial setup
- System self-heals automatically

## Validation Checklist

After deployment:
- [ ] Database migration successful (message_enqueued_at column exists)
- [ ] Backend revision deployed (check with `az containerapp revision list`)
- [ ] Worker revision deployed (check with `az containerapp revision list`)
- [ ] Worker logs show "🧹 Janitor loop started (runs every 60 seconds)"
- [ ] Reset stuck documents successful
- [ ] Trigger processing successful
- [ ] Documents progressing (24 → 25 → 26 → ... → 41)
- [ ] No dead letters accumulating (check `az servicebus queue show`)
- [ ] Worker logs show processing success: "✅ Completed processing"
- [ ] Janitor logs show stuck resets (if any): "🧹 Janitor: Reset N stuck documents"

## Rollback Plan (If Needed)

```bash
# List previous revisions
az containerapp revision list --name auditapp-staging-backend -g auditapp-staging-rg --query "[].name" -o tsv
az containerapp revision list --name auditapp-staging-worker -g auditapp-staging-rg --query "[].name" -o tsv

# Activate previous revision
az containerapp revision activate --name auditapp-staging-backend -g auditapp-staging-rg --revision <previous-revision>
az containerapp revision activate --name auditapp-staging-worker -g auditapp-staging-rg --revision <previous-revision>
```

## Status
- **Code Changes:** ✅ Complete
- **Database Migration:** ⏳ Ready to run (needs DB password)
- **ACR Builds:** ⏳ In progress
- **Deployment:** ⏳ Waiting for builds
- **Testing:** ⏳ Pending deployment

**Current Document Status:**
- Completed: 24/41 (59%)
- Processing: 3 (stuck)
- Queued: 14
- Service Bus: 5 active messages, 0 dead letters
