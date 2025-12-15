# Document Processing Architecture

## Overview

The Audit App uses a **separated worker architecture** for enterprise-grade reliability and performance. This ensures the API remains fast and responsive while documents are processed in the background.

## Architecture Components

### 1. API Server (`backend/app/main.py`)
- **Purpose**: Handle HTTP requests (upload, query, delete)
- **Resources**: 1 CPU, 2Gi memory
- **Scaling**: 1-3 replicas based on load
- **Responsibilities**:
  - Accept document uploads
  - Store files in Azure Blob Storage
  - Create document records with status="queued"
  - Serve document queries and Q&A
  - Delete documents from all locations

### 2. Worker Process (`backend/worker.py`)
- **Purpose**: Process queued documents in background
- **Resources**: 0.5 CPU, 1Gi memory
- **Scaling**: 1 replica (single worker)
- **Responsibilities**:
  - Poll database for queued documents
  - Download files from Blob Storage
  - Extract text and metadata
  - Generate embeddings via Azure OpenAI
  - Index in Azure AI Search
  - Update document status to "completed" or "failed"

## Why This Architecture?

### Previous Issues (In-Process Background Processor)
❌ **Resource Contention**: Background processing competed with API requests  
❌ **Event Loop Blocking**: Long-running operations blocked HTTP responses  
❌ **Connection Exhaustion**: Single pool shared between API and processing  
❌ **Timeouts**: API endpoints became slow or unresponsive  
❌ **No Isolation**: One bad document could crash entire API  

### Benefits (Separate Worker Process)
✅ **Complete Isolation**: API and worker run in separate containers  
✅ **No Contention**: Each has dedicated resources and connection pools  
✅ **Fast API**: Zero overhead from background processing  
✅ **Resilience**: Worker failures don't affect API  
✅ **Scalability**: Can scale API and worker independently  
✅ **Enterprise-Grade**: Industry standard pattern used by Celery, AWS SQS, etc.  

## How It Works

```
┌─────────────────┐
│   User Upload   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  API Server                 │
│  1. Save to Blob Storage    │───┐
│  2. Create DB record        │   │
│     status = "queued"       │   │
│  3. Return 200 OK           │   │
└─────────────────────────────┘   │
         │                         │
         │ Fast response           │
         ▼                         │
    User sees upload success       │
                                   │
                                   │ Azure Blob Storage
                                   ▼
┌─────────────────────────────────────┐
│  Worker Process (Separate)          │
│  1. Poll DB every 10s               │
│  2. Find queued documents           │
│  3. Process one at a time:          │
│     - Download from blob            │
│     - Extract text                  │
│     - Generate embeddings           │
│     - Index in AI Search            │
│  4. Update status = "completed"     │
└─────────────────────────────────────┘
         │
         ▼
    ┌────────────────────┐
    │  Azure AI Search   │
    │  (Ready for Q&A)   │
    └────────────────────┘
```

## Processing Flow

1. **Upload**: User uploads document → API saves to blob → Creates record with `status="queued"` → Returns immediately
2. **Queue**: Worker polls database every 10 seconds for documents where `status="queued"`
3. **Process**: Worker processes one document at a time with full error isolation
4. **Index**: Chunks and embeddings stored in Azure AI Search with `document_id` metadata
5. **Complete**: Document status updated to `"completed"` or `"failed"`

## Error Handling

### Stuck Document Recovery
- **Detection**: On startup, worker finds documents in "processing" state for >10 minutes
- **Recovery**: Automatically reset to "queued" for retry
- **Logging**: All resets logged for monitoring

### Per-Document Isolation
- Each document processing wrapped in try-catch
- One failure doesn't affect others in queue
- Failed documents marked with error message
- Worker continues processing remaining documents

### Timeouts
- File download: 60 seconds
- Text extraction: 120 seconds
- Embedding generation: 180 seconds
- Vector indexing: 60 seconds

## Deployment

### Deploy API (Updated)
```bash
cd backend
docker build -t auditapp-backend:latest .
# Push and deploy to Azure Container Apps
```

### Deploy Worker
```bash
chmod +x deploy-worker.sh
./deploy-worker.sh
```

The deploy script:
1. Builds worker Docker image using `Dockerfile.worker`
2. Pushes to Azure Container Registry
3. Creates/updates worker container app
4. Copies all environment variables from API container
5. Configures with 1 replica, 0.5 CPU, 1Gi memory

## Monitoring

### Check Worker Status
```bash
az containerapp show \
  --name auditapp-staging-worker \
  --resource-group auditapp-staging-rg \
  --query 'properties.runningStatus'
```

### View Worker Logs
```bash
az containerapp logs show \
  --name auditapp-staging-worker \
  --resource-group auditapp-staging-rg \
  --follow
```

### Monitor Document Processing
```bash
# Check queued documents
curl https://auditapp-staging-backend.../api/engagements/{id}/documents | jq '[.[] | select(.status=="queued")] | length'

# Check processing documents
curl https://auditapp-staging-backend.../api/engagements/{id}/documents | jq '[.[] | select(.status=="processing")] | length'

# Check completed documents
curl https://auditapp-staging-backend.../api/engagements/{id}/documents | jq '[.[] | select(.status=="completed")] | length'
```

## Configuration

### Worker Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WORKER_BATCH_SIZE` | Documents to process in parallel | 1 |
| `WORKER_POLL_INTERVAL` | Seconds between queue checks | 10 |
| `WORKER_ENABLE` | Enable/disable worker | true |

### Resource Allocation

| Component | CPU | Memory | Replicas | Purpose |
|-----------|-----|--------|----------|---------|
| API Server | 1.0 | 2.0Gi | 1-3 | Handle HTTP requests |
| Worker | 0.5 | 1.0Gi | 1 | Process documents |
| SQL Database | 10 DTU | 2GB | - | Store metadata |

## Comparison with In-Process Design

| Aspect | In-Process (Old) | Separate Worker (New) |
|--------|------------------|----------------------|
| API Response Time | Slow (2+ min) | Fast (<1 sec) |
| Resource Isolation | ❌ Shared | ✅ Dedicated |
| Failure Impact | Crashes API | Isolated to worker |
| Scalability | Limited | Independent |
| Monitoring | Mixed logs | Clear separation |
| Enterprise-Ready | ❌ No | ✅ Yes |

## Cost Impact

**Before**: 1 container @ 1 CPU, 2Gi = ~$30/month  
**After**: API (1 CPU, 2Gi) + Worker (0.5 CPU, 1Gi) = ~$45/month  

**Additional Cost**: ~$15/month  
**Value**: 100% API uptime, professional architecture, no more timeout issues

## Troubleshooting

### Worker Not Processing Documents

1. **Check worker is running**:
   ```bash
   az containerapp replica list --name auditapp-staging-worker -g auditapp-staging-rg
   ```

2. **Check worker logs for errors**:
   ```bash
   az containerapp logs show --name auditapp-staging-worker -g auditapp-staging-rg --tail 100
   ```

3. **Verify database connectivity**:
   Worker logs should show "Database initialized" on startup

4. **Check for stuck documents**:
   Worker resets stuck documents on startup and logs the count

### Documents Stuck in "Processing"

- Worker automatically resets documents stuck for >10 minutes on startup
- Manual reset: Restart worker container
  ```bash
  az containerapp revision restart --name auditapp-staging-worker -g auditapp-staging-rg
  ```

### High Memory Usage

- Worker processes 1 document at a time to limit memory
- Large PDFs (>50MB) may cause memory spikes
- Consider increasing worker memory to 1.5Gi if needed

## Future Enhancements

1. **Azure Service Bus Queue**: Replace database polling with message queue
2. **Multiple Workers**: Scale to multiple worker replicas for high throughput
3. **Priority Queue**: Process certain documents first (e.g., small files)
4. **Retry Logic**: Exponential backoff for failed documents
5. **Metrics Dashboard**: Prometheus/Grafana for monitoring

## References

- Azure Container Apps: https://learn.microsoft.com/azure/container-apps/
- Worker Pattern: https://microservices.io/patterns/data/saga.html
- Celery (similar architecture): https://docs.celeryq.dev/
