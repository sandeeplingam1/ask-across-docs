# System Architecture

Technical architecture documentation for the Audit App Document Q&A system.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Database Design](#database-design)
5. [Vector Store Architecture](#vector-store-architecture)
6. [RAG Pipeline](#rag-pipeline)
7. [API Design](#api-design)
8. [Security Considerations](#security-considerations)

---

## System Overview

The Audit App is a full-stack RAG (Retrieval-Augmented Generation) application that enables question-answering over uploaded documents.

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Client Layer                              │
│                   (React Frontend)                            │
│                                                               │
│  Components: Engagement List, Document Upload, Q&A, History  │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP/REST
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                   API Layer                                   │
│                (FastAPI Backend)                              │
│                                                               │
│  Routes: Engagements, Documents, Questions, Files            │
└───┬──────────────┬──────────────┬───────────────────────────┘
    │              │              │
    │              │              │
┌───▼──────┐  ┌───▼────────┐  ┌──▼─────────┐
│ Business │  │  Document  │  │   Q&A      │
│  Logic   │  │ Processing │  │  Service   │
│          │  │  Service   │  │            │
└───┬──────┘  └───┬────────┘  └──┬─────────┘
    │             │               │
    │             │               │
┌───▼─────┐  ┌───▼────┐  ┌──────▼──────┐  ┌────────────┐
│SQLite   │  │Chroma  │  │   Azure     │  │   File     │
│Database │  │  DB    │  │   OpenAI    │  │  Storage   │
└─────────┘  └────────┘  └─────────────┘  └────────────┘
```

### Technology Decisions

**Backend Framework:** FastAPI
- Async support (crucial for I/O-bound operations)
- Automatic API documentation
- Type validation with Pydantic
- High performance

**Frontend Framework:** React + Vite
- Component-based architecture
- Fast development with Vite
- Modern JavaScript features
- Excellent ecosystem

**Database:** SQLite (local), PostgreSQL (production)
- SQLite: Zero-configuration, perfect for local dev
- Easy migration path to PostgreSQL

**Vector Store:** ChromaDB (local), Azure AI Search (production)
- Abstraction layer allows zero-code switching
- ChromaDB: Free, local, good for development
- Azure AI Search: Scalable, managed, production-ready

**Document Processing:** PyPDF2, python-docx
- Pure Python implementations
- No external dependencies
- Page-level extraction

---

## Component Architecture

### Backend Components

```
backend/app/
├── main.py                   # Application entry, CORS, lifespan
├── config.py                 # Environment configuration
├── database.py               # SQLAlchemy ORM models
├── db_session.py             # Database session management
├── models.py                 # Pydantic request/response models
├── routes/                   # API endpoints
│   ├── engagements.py       # CRUD for engagements
│   ├── documents.py         # Document upload/management
│   ├── questions.py         # Q&A endpoints
│   └── document_files.py    # File serving
└── services/                 # Business logic
    ├── document_processor.py # Text extraction + chunking
    ├── embedding_service.py  # Azure OpenAI embeddings
    ├── vector_store.py       # Vector DB abstraction
    └── qa_service.py         # RAG implementation
```

**Separation of Concerns:**
- Routes: HTTP handling, request validation
- Services: Business logic, core algorithms
- Models: Data validation, serialization
- Database: Data persistence

### Frontend Components

```
frontend/src/
├── main.jsx                 # Application entry
├── App.jsx                  # Root component, routing
├── api.js                   # API client (Axios)
├── components/              # Reusable UI components
│   ├── EngagementList.jsx  # Display engagements
│   ├── DocumentUpload.jsx  # File upload UI
│   ├── DocumentList.jsx    # Document management
│   ├── QuestionInput.jsx   # Question form
│   ├── AnswerDisplay.jsx   # Answer rendering
│   ├── DocumentViewer.jsx  # PDF viewer modal
│   └── QAHistory.jsx       # History display
└── pages/                   # Page-level components
    └── EngagementView.jsx  # Main engagement interface
```

**Component Hierarchy:**
```
App
├── EngagementList
│   └── CreateEngagementModal
└── EngagementView
    ├── DocumentUpload
    ├── DocumentList
    │   └── DocumentViewer (modal)
    ├── QuestionInput
    ├── AnswerDisplay
    │   └── DocumentViewer (modal)
    └── QAHistory
```

---

## Data Flow

### Document Upload Flow

```
User uploads file
        │
        ▼
Frontend validates (type, size)
        │
        ▼
POST /api/engagements/{id}/documents
        │
        ▼
Backend receives file
        │
        ▼
Save to ./data/uploads/{engagement_id}/
        │
        ▼
Extract text + page metadata
        │
        ▼
Chunk text (1000 chars, 200 overlap)
        │
        ▼
Generate embeddings (Azure OpenAI)
        │
        ▼
Store in ChromaDB
        │
        ▼
Save metadata to SQLite
        │
        ▼
Return success response
        │
        ▼
Frontend updates UI
```

### Question Answering Flow

```
User asks question
        │
        ▼
POST /api/engagements/{id}/ask
        │
        ▼
Generate question embedding
        │
        ▼
Search ChromaDB for similar chunks
        │
        ▼
Retrieve top-k chunks (default: 5)
        │
        ▼
Build context from chunks
        │
        ▼
Call Azure OpenAI GPT-4
        │
        ▼
Parse response + extract citations
        │
        ▼
Calculate confidence score
        │
        ▼
Save Q&A to database
        │
        ▼
Return answer with sources
        │
        ▼
Frontend displays with citations
```

---

## Database Design

### Entity Relationship Diagram

```
┌─────────────────┐
│   Engagements   │
│─────────────────│
│ id (PK)         │
│ name            │
│ description     │
│ client_name     │
│ start_date      │
│ end_date        │
│ created_at      │
│ updated_at      │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────▼────────┐       ┌──────────────────┐
│   Documents     │       │ QuestionAnswers  │
│─────────────────│       │──────────────────│
│ id (PK)         │       │ id (PK)          │
│ engagement_id   │◄──────┤ engagement_id    │
│ filename        │   N:1 │ question         │
│ file_type       │       │ answer           │
│ file_size       │       │ sources (JSON)   │
│ file_path       │       │ confidence       │
│ chunk_count     │       │ answered_at      │
│ status          │       └──────────────────┘
│ error_message   │
│ uploaded_at     │
└─────────────────┘
```

### Schema Details

**Engagements Table:**
- Primary entity for organizing documents
- Soft delete capability (can add deleted_at)
- Cascade delete to documents and Q&As

**Documents Table:**
- Stores file metadata, not content
- Status field tracks processing state
- file_path references local storage
- chunk_count for monitoring

**QuestionAnswers Table:**
- Complete Q&A history
- sources stored as JSON for flexibility
- confidence for answer quality tracking

---

## Vector Store Architecture

### Abstraction Layer

```python
class VectorStore(ABC):
    @abstractmethod
    async def create_collection(engagement_id): pass
    
    @abstractmethod
    async def add_documents(chunks, embeddings): pass
    
    @abstractmethod
    async def search(query_embedding, top_k): pass
    
    @abstractmethod
    async def delete_document(document_id): pass
```

### ChromaDB Implementation

**Storage Structure:**
```
./data/chromadb/
└── chroma.sqlite3          # ChromaDB metadata
└── [UUID]/                 # Collection data
    └── data_level0.bin     # Vector data
```

**Collection Naming:**
- One collection per engagement
- Format: `engagement_{engagement_id}`
- Automatic creation on first document upload

**Metadata Stored:**
- document_id
- engagement_id
- chunk_index
- page_number
- filename

### Azure AI Search Implementation

**Index Structure:**
- Single global index
- Filtered by engagement_id
- Schema:
  - id: Unique chunk ID
  - engagement_id: Filter field
  - document_id: Filter field
  - text: Searchable content
  - embedding: Vector field (1536 dimensions)
  - page_number: Stored for citations

---

## RAG Pipeline

### Embedding Generation

**Model:** text-embedding-ada-002
- Dimensionality: 1536
- Max tokens: 8191
- Cost: $0.0001 per 1K tokens

**Process:**
1. Batch chunks for efficiency (up to 16 at once)
2. Call Azure OpenAI API
3. Store embeddings with metadata
4. Handle rate limits with exponential backoff

### Retrieval

**Similarity Search:**
- Method: Cosine similarity
- Top-k: 5 chunks (configurable)
- Pre-filtered by engagement_id

**Chunk Selection:**
- Highest similarity scores
- Diversity: Prefer different documents
- Page awareness: Include page numbers

### Generation

**Model:** GPT-4 (or GPT-3.5-Turbo)
- Max tokens: 8192 (GPT-4), 4096 (GPT-3.5)
- Temperature: 0.3 (for consistency)
- Cost: $0.03/1K tokens (GPT-4)

**Prompt Structure:**
```
System: You are a precise assistant. Answer only based on provided sources.

Context:
[Source 1 - doc.pdf, Page 3]
{chunk text}

[Source 2 - doc.pdf, Page 5]
{chunk text}

Question: {user question}
```

**Response Parsing:**
- Extract answer text
- Identify cited sources
- Calculate confidence based on similarity scores

---

## API Design

### RESTful Principles

- Resource-based URLs
- HTTP verbs for actions
- JSON request/response
- Standard status codes

### Endpoint Structure

```
/api/engagements                    # Collection
/api/engagements/{id}               # Resource
/api/engagements/{id}/documents     # Sub-collection
/api/engagements/{id}/ask           # Action
```

### Response Format

**Success:**
```json
{
  "id": "uuid",
  "name": "string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Error:**
```json
{
  "detail": "Error message"
}
```

### Status Codes

- 200: Success
- 201: Created
- 204: Deleted (no content)
- 400: Bad request
- 404: Not found
- 500: Server error

---

## Security Considerations

### Current Implementation

**Environment Variables:**
- API keys stored in .env
- Not committed to git
- Loaded at runtime

**CORS:**
- Restricted to localhost origins
- Configurable via environment

**Input Validation:**
- Pydantic models validate all inputs
- File type checking
- Size limits enforced

### Production Recommendations

**Authentication:**
- Implement OAuth 2.0 or Azure AD
- JWT tokens for API access
- Role-based access control

**API Security:**
- Rate limiting
- Request signing
- HTTPS only

**Data Security:**
- Encrypt data at rest
- Encrypt data in transit
- Azure Key Vault for secrets

**File Security:**
- Virus scanning on upload
- Sandboxed processing
- Access logging

---

## Performance Considerations

### Backend Optimization

**Async Operations:**
- All I/O operations are async
- Concurrent request handling
- Non-blocking database queries

**Caching:**
- Consider Redis for embeddings cache
- Cache frequently asked questions
- Cache vector search results

### Frontend Optimization

**Bundle Size:**
- Code splitting implemented
- Tree shaking enabled
- Lazy loading for routes

**API Calls:**
- Debouncing for search
- Pagination for large lists
- Optimistic UI updates

---

## Scalability

### Horizontal Scaling

**Stateless Backend:**
- No session state
- Can run multiple instances
- Load balancer compatible

**Database:**
- Read replicas for scaling reads
- Connection pooling
- Query optimization

### Vertical Scaling

**Memory:**
- Embedding cache size
- Document processing buffer
- Vector index size

**CPU:**
- Concurrent request handling
- Background task processing
- Embedding generation

---

## Monitoring

### Recommended Metrics

**Application:**
- Request latency
- Error rates
- Active users
- Q&A per engagement

**Infrastructure:**
- CPU usage
- Memory usage
- Disk I/O
- Network throughput

**Business:**
- Documents processed
- Questions answered
- Average confidence
- User satisfaction

---

## Future Enhancements

### Short Term
- Background job processing (Celery)
- Redis caching layer
- Prometheus metrics
- Health check endpoints

### Long Term
- Multi-tenancy support
- Advanced search filters
- Document versioning
- Real-time collaboration
- Audit trail logging

---

This architecture supports the current requirements while providing a clear path for scaling and enhancement.
