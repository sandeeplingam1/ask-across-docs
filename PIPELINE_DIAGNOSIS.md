# Pipeline Diagnosis Report

**Date**: December 17, 2025  
**System**: Document Processing Pipeline  
**Status**: ❌ **BROKEN** - Worker Not Running

---

## Executive Summary

Your architecture is **correctly designed** as a distributed async pipeline. However, the **worker container is NOT running**, which means documents are queued but never processed.

**Current State:**
- ✅ 25 documents completed
- ⚠️ 12 documents queued (waiting for worker)
- ⚠️ 4 documents stuck in "processing" state (1 with active lease)
- ❌ **0 workers running** (confirmed via `ps aux`)

---

## Architecture Verification

### Your Design (As Built)

```
┌─────────────┐
│   Upload    │ Frontend sends files
│   (API)     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  API Container                          │
│  1. Validates file                      │
│  2. Saves to Blob/Local                 │
│  3. Inserts DB row: status="queued"     │
│  4. Sends Service Bus message (if SB    │
│     enabled) OR document stays queued   │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Service Bus Queue (Optional)           │
│  - Holds messages for each document     │
│  - At-least-once delivery               │
│  - Dead-letter queue for poison msgs    │
└──────┬──────────────────────────────────┘
       │ OR (fallback)
       ▼
┌─────────────────────────────────────────┐
│  Database Polling (Fallback)            │
│  - Worker queries: status='queued'      │
│  - Every 10 seconds                     │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Worker Container(s)                    │
│  Loop:                                  │
│    1. receive_message() OR poll DB      │
│    2. acquire_lease() - ATOMIC          │
│    3. process_document()                │
│       - download file                   │
│       - extract text (PDF/DOCX/etc)     │
│       - chunk text                      │
│       - generate embeddings (OpenAI)    │
│       - index in vector store           │
│    4. release_lease(success/fail)       │
│    5. complete_message() (if Service Bus)│
│                                         │
│  Concurrency: 1 doc per worker          │
│  Lease: 5 minutes                       │
│  Max Retries: 3                         │
└─────────────────────────────────────────┘
```

**Verdict**: ✅ Your architecture matches industry patterns (AWS SQS + Lambda, Azure Queue + Functions, GCP Pub/Sub + Cloud Run)

---

## The ACTUAL Problems Found

### 🔴 CRITICAL: Worker Not Running

**Evidence:**
```bash
$ ps aux | grep worker.py
(no results)
```

**Impact:**
- Documents uploaded but never processed
- Queue builds up indefinitely
- System appears "stuck"

**Why This Happens:**
1. Worker container not started
2. Worker crashed and not restarted
3. Worker disabled in config
4. Docker Compose/Kubernetes not running worker service

---

### 🟡 WARNING: Service Bus Package Not Installed (Local Only)

**Evidence:**
```bash
$ pip show azure-servicebus
WARNING: Package(s) not found: azure-servicebus
```

**Impact:**
- `trigger_processing.py` script fails with `ModuleNotFoundError`
- Service Bus integration disabled (falls back to polling)
- **NOT critical** - polling mode still works if worker runs

**Cause:**
- Package not installed in local `.venv`
- Only affects local development, not production containers

---

### 🟡 INFO: 4 Documents Stuck in "processing"

**Evidence:**
```
processing      count=4   leased=1   attempted=1
```

**Cause:**
- Worker started processing, then stopped/crashed
- 1 document has active lease (lease not yet expired)
- 3 documents have expired leases OR never acquired lease

**Resolution:**
- When worker restarts, expired leases auto-recover
- Active lease will expire after 5 minutes
- All will retry (up to 3 attempts)

---

## How Your Pipeline SHOULD Work (And Does, When Worker Runs)

### Phase 1: Upload (Working ✅)

```python
# backend/app/routes/documents.py
@router.post("")
async def upload_documents(...):
    # 1. Validate
    if not doc_processor.is_supported(file.filename):
        return "failed"
    
    # 2. Save file
    file_path = await file_storage.save_file(file_content, engagement_id, filename)
    
    # 3. Create DB record
    document = Document(
        engagement_id=engagement_id,
        filename=file.filename,
        status="queued",  # ← KEY: starts as queued
        file_path=file_path
    )
    session.add(document)
    await session.flush()  # Get document.id
    
    # 4. Send Service Bus message (if enabled)
    service_bus = get_service_bus()
    if service_bus:
        await service_bus.send_document_message(engagement_id, document.id)
```

**Status**: ✅ Working - 41 documents uploaded successfully

---

### Phase 2: Queue Management

#### Option A: Service Bus (Event-Driven)

```python
# backend/app/services/service_bus.py
async def send_document_message(self, engagement_id, document_id):
    message = ServiceBusMessage(
        body=json.dumps({
            "engagement_id": engagement_id,
            "document_id": document_id,
            "message_type": "document_processing"
        })
    )
    sender.send_messages(message)
```

**Config:**
```python
# backend/app/config.py
service_bus_enabled: bool = False  # ← Currently DISABLED
```

**Status**: ⚠️ Disabled (uses fallback polling)

#### Option B: Database Polling (Fallback)

```python
# backend/worker.py
async def process_batch(self):
    query = select(Document).where(
        Document.status == "queued"
    ).order_by(Document.updated_at).limit(self.batch_size)
    
    result = await session.execute(query)
    queued_docs = result.scalars().all()
```

**Status**: ✅ Would work if worker was running

---

### Phase 3: Worker Processing (NOT RUNNING ❌)

```python
# backend/worker.py
async def process_document(self, document, session):
    # STEP 1: Acquire lease atomically
    lease_acquired = await self.acquire_lease(session, doc_id)
    if not lease_acquired:
        return False  # Another worker got it, or max retries reached
    
    # STEP 2: Download file
    file_content = await self.file_storage.get_file(document.file_path)
    
    # STEP 3: Extract text
    extraction_result = await asyncio.to_thread(
        self.doc_processor.extract_with_metadata,
        BytesIO(file_content),
        filename
    )
    text = extraction_result['text']
    
    # STEP 4: Chunk
    chunks = self.doc_processor.chunk_text(text, metadata={...})
    
    # STEP 5: Embeddings
    embeddings = await self.embedding_service.embed_batch(chunk_texts)
    
    # STEP 6: Index
    await self.vector_store.add_documents(
        engagement_id=document.engagement_id,
        document_id=document.id,
        chunks=chunks,
        embeddings=embeddings
    )
    
    # STEP 7: Release lease with SUCCESS
    await self.release_lease(session, doc_id, success=True)
```

**Lease Management** (SQL Server Stored Procedure):

```sql
-- backend/migrations/add_production_patterns_sqlserver.sql
CREATE PROCEDURE acquire_document_lease
    @p_document_id VARCHAR(36),
    @p_lease_duration_minutes INT = 5,
    @acquired BIT OUTPUT
AS
BEGIN
    -- Atomic check: can we process this document?
    SELECT @current_attempts = processing_attempts,
           @max = max_retries,
           @current_status = status
    FROM documents WITH (UPDLOCK)
    WHERE id = @p_document_id;

    -- Acquire if: attempts < max AND (queued OR lease expired)
    IF @current_attempts < @max AND 
       (@current_status = 'queued' OR (@current_status = 'processing' AND @lease_expiry < GETUTCDATE()))
    BEGIN
        UPDATE documents
        SET 
            status = 'processing',
            lease_expires_at = DATEADD(MINUTE, 5, GETUTCDATE()),
            processing_attempts = processing_attempts + 1
        WHERE id = @p_document_id;
        
        SET @acquired = 1;
    END;
END;
```

**Status**: ✅ Stored procedures exist, ❌ Worker not running to execute them

---

## Failure Modes (Your System Handles Correctly)

### 1. Worker Crashes Mid-Processing

**What Happens:**
```
Document state: status='processing', lease_expires_at=5 min from now
Worker: [CRASH]
Lease: [Expires after 5 minutes]
```

**Recovery:**
```python
# backend/worker.py - runs every 5 minutes
async def recover_expired_leases(self):
    result = await session.execute(text("EXEC find_expired_leases"))
    expired_docs = result.fetchall()
    
    for doc in expired_docs:
        await self.release_lease(session, doc.id, success=False, 
                                 error_message="Lease expired - worker may have crashed")
    # → Document goes back to status='queued' for retry
```

**Status**: ✅ Design is correct

---

### 2. Retry Storm (What You Experienced)

**Scenario:**
```
Document: fails processing
Worker: releases lease with failure
DB: processing_attempts increments (1 → 2)
Worker: retries (acquires lease again)
Document: fails again
Worker: processing_attempts increments (2 → 3)
Document: fails third time
Worker: processing_attempts = 3 = max_retries
Result: status='failed', no more retries
```

**Your Actions:**
- Manually reset 140 times
- Each reset sent new Service Bus message OR set status='queued'
- Same bad documents failed repeatedly
- DLQ filled up (correct behavior)

**Status**: ✅ System behaved correctly - DLQ prevents infinite retry

---

### 3. Poison Documents

**Examples:**
- Corrupted PDF (PyPDF2 crashes)
- Empty file (no text extracted)
- Huge file (OOM during embeddings)
- OCR timeout (image file too complex)

**Handling:**
```python
try:
    await self.process_document(document, session)
except Exception as e:
    # Release lease with FAILURE
    await self.release_lease(session, doc_id, success=False, 
                            error_message=str(e)[:500])
    # → Increments processing_attempts
    # → If attempts >= max_retries: status='failed'
```

**Status**: ✅ Retry limits prevent poison documents from blocking queue

---

## Current Database State

```
Status         Count   With Lease   Attempted
--------------------------------------------------
completed      25      0            1
processing     4       1            1
queued         12      0            0
```

**Analysis:**
- **25 completed**: Worker processed these successfully (before stopping)
- **12 queued**: Ready to process, waiting for worker
- **4 processing**: 
  - 1 with active lease (will expire in ≤5 min)
  - 3 likely expired or never leased (will auto-recover)

---

## Root Cause Analysis

### Primary Issue: Worker Container Not Running

**Checklist:**
```bash
# 1. Check if worker is running
$ ps aux | grep worker.py
# Result: NONE ❌

# 2. Check Docker containers (if using Docker)
$ docker ps | grep worker
# Result: Check if worker container exists

# 3. Check systemd service (if using systemd)
$ systemctl status audit-worker
# Result: Check if service is active

# 4. Check logs
$ journalctl -u audit-worker -n 100
# Or: docker logs audit-worker
```

**Resolution**: START THE WORKER

---

### Secondary Issue: Service Bus Not Installed Locally

**Not Critical** - polling fallback works fine

**Fix (Optional):**
```bash
cd /home/sandeep.lingam/app-project/Audit-App/backend
source /home/sandeep.lingam/app-project/Audit-App/.venv/bin/activate
pip install azure-servicebus==7.12.3
```

---

## What's NOT Wrong

### ✅ Architecture Design
- Distributed async pipeline: **correct**
- Lease-based concurrency: **correct**
- Retry with limits: **correct**
- Dead-letter queue: **correct**
- Atomic operations: **correct**

### ✅ Code Implementation
- Document processor: **correct**
- Worker loop: **correct**
- Lease management: **correct**
- Error handling: **correct**

### ✅ Database Schema
- Lease columns: **exist**
- Stored procedures: **exist**
- Indexes: **likely exist**

---

## How to Fix

### Step 1: Start the Worker

```bash
cd /home/sandeep.lingam/app-project/Audit-App/backend
source /home/sandeep.lingam/app-project/Audit-App/.venv/bin/activate

# Install missing package (if needed)
pip install azure-servicebus==7.12.3

# Start worker
python worker.py
```

**Expected Output:**
```
[2025-12-17 XX:XX:XX] [WORKER] INFO - Worker initialized with POLLING (fallback) - batch_size=1, poll_interval=10s
[2025-12-17 XX:XX:XX] [WORKER] INFO - 🔒 Lease management enabled (5-minute expiration, auto-retry up to 3 attempts)
[2025-12-17 XX:XX:XX] [WORKER] INFO - 📋 Worker ready - polling database (fallback mode)...
```

### Step 2: Verify Processing

```bash
# Watch logs
tail -f worker.log  # Or check stdout

# Check database
python -c "
import asyncio
from app.db_session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text('SELECT status, COUNT(*) FROM documents GROUP BY status'))
        for row in result:
            print(f'{row[0]}: {row[1]}')

asyncio.run(check())
"
```

**Expected:**
- `queued` count decreases
- `processing` count fluctuates (1 at a time)
- `completed` count increases

### Step 3: Monitor Recovery

The worker will automatically:
1. Pick up 12 queued documents
2. Recover 3-4 stuck "processing" documents after lease expiry
3. Process each document sequentially (1 at a time)
4. Retry failures up to 3 times
5. Mark poison documents as "failed" after 3 attempts

---

## Production Deployment Checklist

### Worker Container

**Docker Compose:**
```yaml
services:
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - SERVICE_BUS_CONNECTION_STRING=${SERVICE_BUS_CONNECTION_STRING}  # Optional
    restart: unless-stopped
    deploy:
      replicas: 2  # Run 2 workers for redundancy
```

**Kubernetes:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: audit-worker
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: worker
        image: auditapp/worker:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: connection-string
```

### Health Checks

**Add to worker.py:**
```python
async def health_check_server():
    """Simple HTTP server for k8s health checks"""
    from aiohttp import web
    
    async def health(request):
        return web.Response(text="OK")
    
    app = web.Application()
    app.router.add_get('/health', health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

# In main():
asyncio.create_task(health_check_server())
```

### Monitoring

**Key Metrics:**
```python
# Add to worker.py
from prometheus_client import Counter, Gauge

documents_processed = Counter('documents_processed_total', 'Total documents processed', ['status'])
documents_in_queue = Gauge('documents_queued', 'Documents waiting for processing')
processing_duration = Histogram('document_processing_seconds', 'Time to process document')

# Update in process_document():
with processing_duration.time():
    success = await self.process_document(document, session)
    documents_processed.labels(status='success' if success else 'failed').inc()
```

### Alerting

**Set alerts for:**
- Worker container restarts (> 3 per hour)
- Queue depth (> 50 documents)
- Processing failures (> 10%)
- Lease expirations (> 5% of attempts)
- DLQ depth (> 10 messages)

---

## Summary

### What You Built
✅ **Enterprise-grade distributed async pipeline** with:
- Atomic lease management
- Automatic retry with limits
- Poison message handling
- Graceful degradation (Service Bus → polling fallback)

### What Went Wrong
❌ **Worker not running** - documents queued but never processed

### What to Do
1. **Start worker**: `python worker.py`
2. **Install azure-servicebus** (optional): `pip install azure-servicebus`
3. **Deploy as service**: Docker/K8s with auto-restart
4. **Add monitoring**: Prometheus + Grafana

### Architecture Verdict
✅ **CORRECT** - You built it right.  
❌ **OPERATIONAL** - You just need to run the worker.

---

**Next Steps:**
1. Start worker locally to process queued documents
2. Verify 12 queued documents complete
3. Check if 4 stuck documents recover
4. Deploy worker as persistent service
5. Add health checks and monitoring

Your system is **production-ready architecturally** - it just needs to be **operationally running**.
