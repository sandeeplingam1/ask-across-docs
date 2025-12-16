# Document Processing Pipeline

## Complete Document Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCUMENT UPLOAD FLOW                          │
└─────────────────────────────────────────────────────────────────┘

1. USER UPLOADS DOCUMENT
   │
   ├─► Frontend (DocumentUpload.jsx)
   │   └─► POST /api/engagements/{engagement_id}/documents
   │
   ├─► Backend API (documents.py)
   │   ├─► Validates file type (PDF, DOCX, TXT, XLSX, PNG, JPG)
   │   ├─► Validates file size (max 100MB)
   │   ├─► Saves to Azure Blob Storage (file_storage.py)
   │   │   └─► Azure Blob: stobghpsbi63abq/audit-documents/{engagement_id}/{filename}
   │   │
   │   └─► Creates Database Record
   │       ├─► Table: documents
   │       ├─► Status: "queued"
   │       ├─► Metadata: filename, file_type, file_size, file_path
   │       └─► Timestamps: uploaded_at
   │
   └─► Returns: Upload status to user


┌─────────────────────────────────────────────────────────────────┐
│                 BACKGROUND PROCESSING (Worker)                   │
└─────────────────────────────────────────────────────────────────┘

2. WORKER PICKS UP DOCUMENT
   │
   ├─► Worker Container (worker.py)
   │   ├─► Polls database every 10 seconds
   │   ├─► Finds documents with status="queued"
   │   ├─► Processes 1 document at a time (batch_size=1)
   │   └─► Updates status to "processing"
   │
   ├─► STEP 1: Download Document
   │   ├─► Downloads from Azure Blob Storage
   │   ├─► Timeout: 60 seconds
   │   └─► Progress: 10%
   │
   ├─► STEP 2: Extract Text
   │   ├─► document_processor.py
   │   ├─► PDF: PyPDF2 extracts text per page
   │   ├─► DOCX: python-docx extracts paragraphs
   │   ├─► TXT: Direct text read
   │   ├─► XLSX: pandas extracts sheets/cells
   │   ├─► Images: pytesseract OCR (with resize to prevent OOM)
   │   ├─► Timeout: 120 seconds
   │   ├─► Memory cleanup: GC after every 10 pages
   │   └─► Progress: 25%
   │
   ├─► STEP 3: Chunk Text
   │   ├─► document_processor.py
   │   ├─► Chunk size: 1000 characters
   │   ├─► Chunk overlap: 200 characters
   │   ├─► Metadata: document_id, filename, engagement_id, page_num
   │   └─► Progress: 50%
   │
   ├─► STEP 4: Generate Embeddings
   │   ├─► embedding_service.py
   │   ├─► Azure OpenAI: text-embedding-3-large
   │   ├─► Batch processing: 16 texts per API call
   │   ├─► Authentication: Managed Identity (Azure AD)
   │   ├─► Timeout: 180 seconds
   │   └─► Progress: 70%
   │
   ├─► STEP 5: Index in Vector Store
   │   ├─► vector_store.py → Azure AI Search
   │   ├─► Index: documents (gptkb-obghpsbi63abq)
   │   ├─► Stores: text, embeddings, metadata
   │   ├─► Filter fields: engagement_id, document_id
   │   ├─► Timeout: 60 seconds
   │   └─► Progress: 90%
   │
   └─► STEP 6: Mark Complete
       ├─► Updates database: status="completed"
       ├─► Sets: chunk_count, completed timestamp
       ├─► Progress: 100%
       └─► Garbage collection: Frees memory


┌─────────────────────────────────────────────────────────────────┐
│                    QUERY/SEARCH FLOW                             │
└─────────────────────────────────────────────────────────────────┘

3. USER ASKS QUESTION
   │
   ├─► Frontend (QuestionInput.jsx)
   │   └─► POST /api/engagements/{engagement_id}/questions
   │
   ├─► Backend API (questions.py)
   │   │
   │   ├─► STEP 1: Generate Query Embedding
   │   │   ├─► embedding_service.py
   │   │   └─► Azure OpenAI: text-embedding-3-large
   │   │
   │   ├─► STEP 2: Vector Search
   │   │   ├─► vector_store.py → Azure AI Search
   │   │   ├─► Filters by: engagement_id
   │   │   ├─► Returns: Top 5 most relevant chunks
   │   │   └─► Includes: text, metadata, similarity score
   │   │
   │   ├─► STEP 3: Build Context
   │   │   └─► Combines retrieved chunks into context
   │   │
   │   ├─► STEP 4: Generate Answer
   │   │   ├─► qa_service.py → Azure OpenAI
   │   │   ├─► Model: gpt-4
   │   │   ├─► Prompt: Question + Context + Instructions
   │   │   └─► Returns: Answer with citations
   │   │
   │   └─► STEP 5: Save Q&A History
   │       ├─► Table: questions
   │       ├─► Stores: question, answer, sources
   │       └─► Timestamp: created_at
   │
   └─► Returns: Answer to user


┌─────────────────────────────────────────────────────────────────┐
│                    DELETION FLOW                                 │
└─────────────────────────────────────────────────────────────────┘

4. DELETE SINGLE DOCUMENT
   │
   ├─► DELETE /api/engagements/{engagement_id}/documents/{document_id}
   │
   ├─► STEP 1: Delete from Vector Store
   │   ├─► Azure AI Search
   │   ├─► Filters: document_id AND engagement_id
   │   └─► Removes: All chunks/embeddings for this document
   │
   ├─► STEP 2: Delete from Blob Storage
   │   ├─► Azure Blob Storage
   │   └─► Deletes: audit-documents/{engagement_id}/{filename}
   │
   └─► STEP 3: Delete from Database
       ├─► Table: documents
       └─► Cascade deletes: Associated Q&A history


5. DELETE ENTIRE ENGAGEMENT
   │
   ├─► DELETE /api/engagements/{engagement_id}
   │
   ├─► STEP 1: Get All Documents
   │   └─► Query: SELECT * FROM documents WHERE engagement_id = ?
   │
   ├─► STEP 2: Delete All Files from Blob Storage
   │   ├─► Loops through all documents
   │   └─► Deletes: Each file_path from Azure Blob Storage
   │
   ├─► STEP 3: Delete from Vector Store
   │   ├─► Azure AI Search
   │   ├─► Filters: engagement_id
   │   └─► Removes: ALL chunks/embeddings for engagement
   │
   └─► STEP 4: Delete from Database
       ├─► Table: engagements (CASCADE)
       ├─► Auto-deletes: documents
       └─► Auto-deletes: questions/answers


┌─────────────────────────────────────────────────────────────────┐
│                     STORAGE LOCATIONS                            │
└─────────────────────────────────────────────────────────────────┘

1. Azure SQL Database (Azure)
   ├─► Tables: engagements, documents, questions
   ├─► Connection: ODBC Driver 18 for SQL Server
   └─► Tier: Standard S0 (30 connections, 10 DTU)

2. Azure Blob Storage (Azure)
   ├─► Account: stobghpsbi63abq
   ├─► Container: audit-documents
   ├─► Structure: /{engagement_id}/{filename}
   └─► Authentication: Managed Identity

3. Azure AI Search (Azure)
   ├─► Service: gptkb-obghpsbi63abq
   ├─► Index: documents
   ├─► Contents: chunks, embeddings, metadata
   └─► Authentication: Managed Identity

4. Azure OpenAI (Azure)
   ├─► Service: cog-obghpsbi63abq
   ├─► Embedding Model: text-embedding-3-large
   ├─► Chat Model: gpt-4
   └─► Authentication: Managed Identity (Azure AD)


┌─────────────────────────────────────────────────────────────────┐
│                    ERROR HANDLING                                │
└─────────────────────────────────────────────────────────────────┘

Worker Error Scenarios:
├─► Out of Memory (OOMKilled)
│   ├─► Detection: Container exits with code 137
│   ├─► Action: Worker auto-restarts
│   ├─► Reset: Stuck documents reset after 10 minutes
│   └─► Mitigation: Batch size=1, GC after each doc
│
├─► Permission Denied (401)
│   ├─► Cause: Missing Azure AD role assignments
│   ├─► Required Roles:
│   │   ├─► Cognitive Services OpenAI User
│   │   └─► Search Index Data Contributor
│   └─► Fix: Grant roles to worker's Managed Identity
│
├─► Timeout Errors
│   ├─► Download: 60s timeout
│   ├─► Text extraction: 120s timeout
│   ├─► Embeddings: 180s timeout
│   └─► Vector indexing: 60s timeout
│
└─► Document Stuck in Processing
    ├─► Detection: processing_started_at > 10 minutes
    ├─► Auto-reset: Worker checks on startup
    └─► Manual reset: POST /api/admin/documents/reset-stuck


┌─────────────────────────────────────────────────────────────────┐
│                    CLEANUP SUMMARY                               │
└─────────────────────────────────────────────────────────────────┘

✅ WHEN YOU DELETE AN ENGAGEMENT:
   ├─► ✅ All document files deleted from Azure Blob Storage
   ├─► ✅ All embeddings/chunks deleted from Azure AI Search
   ├─► ✅ All database records deleted (cascade)
   └─► ✅ All Q&A history deleted (cascade)

✅ WHEN YOU DELETE A SINGLE DOCUMENT:
   ├─► ✅ Document file deleted from Azure Blob Storage
   ├─► ✅ All chunks/embeddings deleted from Azure AI Search
   └─► ✅ Database record deleted

⚠️  IMPORTANT NOTES:
   ├─► Deletion is permanent (no soft delete)
   ├─► Azure Blob Storage: Files are immediately deleted
   ├─► Azure AI Search: Index updates within seconds
   ├─► Database: Cascade deletes ensure referential integrity
   └─► No orphaned data remains in any service
