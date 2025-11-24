# Audit App - Document Q&A System

A production-ready Retrieval-Augmented Generation (RAG) application designed for audit engagements. Upload documents, ask questions, and receive AI-powered answers with precise citations.

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [API Documentation](#api-documentation)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)
11. [Contributing](#contributing)
12. [License](#license)

---

## Overview

The Audit App enables auditing teams to upload large volumes of documents (300-400 per engagement) and ask natural language questions. The system uses Azure OpenAI's GPT-4 to answer questions based solely on the uploaded documents, with full citation tracking and page references.

### Key Capabilities

- Multi-engagement support with complete data isolation
- Bulk document processing (PDF, DOCX, TXT)
- AI-powered Q&A with GPT-4
- Page-numbered citations
- Interactive document viewer
- Q&A history tracking
- Flexible vector database options (ChromaDB or Azure AI Search)

---

## Features

### Document Management
- Support for PDF, DOCX, DOC, and TXT files
- Automatic text extraction with page number tracking
- Intelligent text chunking with configurable overlap
- Upload progress tracking and status indicators
- Individual document deletion

### Question Answering
- Single question input
- Batch question processing via file upload
- AI-generated answers using GPT-4
- Source citations with exact page numbers
- Confidence scoring (high, medium, low)
- Complete Q&A history with searchable interface

### Document Viewer
- Interactive PDF viewer with zoom controls
- Automatic navigation to cited pages
- Text highlighting for referenced content
- Page navigation controls

### Data Management
- Engagement-based organization (project folders)
- Complete isolation between engagements
- Cascade deletion (delete engagement removes all associated data)
- SQLite database for metadata
- ChromaDB for vector embeddings (local)
- Optional Azure AI Search integration

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│                   http://localhost:5173                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP/REST
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│                   http://localhost:8000                      │
│                                                              │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐      │
│  │   Document   │  │  Embedding  │  │  Q&A Service │      │
│  │  Processor   │  │   Service   │  │              │      │
│  └──────────────┘  └─────────────┘  └──────────────┘      │
└────────┬──────────────┬──────────────────┬─────────────────┘
         │              │                  │
    ┌────▼────┐    ┌───▼────┐        ┌───▼────┐
    │ SQLite  │    │ChromaDB│        │ Azure  │
    │Database │    │Vector  │        │OpenAI  │
    │         │    │  Store │        │        │
    └─────────┘    └────────┘        └────────┘
```

### Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (async web framework)
- SQLAlchemy (ORM)
- Pydantic (data validation)
- ChromaDB (vector database)
- Azure OpenAI SDK
- PyPDF2, python-docx (document parsing)

**Frontend:**
- React 18
- Vite (build tool)
- TailwindCSS (styling)
- Axios (HTTP client)
- react-pdf (PDF viewing)
- Lucide React (icons)

**Infrastructure:**
- SQLite (local database)
- ChromaDB (local vector store)
- Azure OpenAI (embeddings + GPT-4)

---

## Prerequisites

### Required Software

- **Python 3.11 or higher**
  ```bash
  python3 --version  # Should show 3.11+
  ```

- **Node.js 18 or higher**
  ```bash
  node --version  # Should show v18+
  npm --version   # Should be included with Node.js
  ```

- **Homebrew** (macOS)
  ```bash
  brew --version
  ```

### Required Azure Resources

- **Azure OpenAI Service** with:
  - `text-embedding-ada-002` deployment (for embeddings)
  - `gpt-4` or `gpt-35-turbo` deployment (for chat)
  - API endpoint URL
  - API key

### How to Get Azure OpenAI

1. Go to Azure Portal (portal.azure.com)
2. Create new resource → "Azure OpenAI"
3. Deploy models:
   - text-embedding-ada-002 (name it as you wish)
   - gpt-4 (name it as you wish)
4. Get credentials from "Keys and Endpoint" section

---

## Installation

### 1. Clone or Navigate to Project

```bash
cd "/Users/sandeeplingam/VibeCoding/Audit App"
```

### 2. Backend Setup

```bash
cd backend

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### 3. Frontend Setup

```bash
cd frontend

# Install Node.js dependencies
npm install
```

### 4. Verification

Check that setup is complete:

```bash
# From project root
ls -la backend/venv          # Should exist
ls -la backend/.env          # Should exist
ls -la frontend/node_modules # Should exist
```

---

## Configuration

### Environment Variables

Edit `backend/.env` with your Azure OpenAI credentials:

```env
# Azure OpenAI Configuration (REQUIRED)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4

# Vector Database (chromadb or azure_search)
VECTOR_DB_TYPE=chromadb
CHROMADB_PATH=./data/chromadb

# Application Settings
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
MAX_UPLOAD_SIZE_MB=100
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/audit_app.db
```

### Configuration Options

**VECTOR_DB_TYPE:**
- `chromadb` - Local vector storage (default, no additional setup)
- `azure_search` - Azure AI Search (requires Azure AI Search resource)

**CHUNK_SIZE:**
- Controls size of text chunks for embedding
- Default: 1000 characters
- Larger = more context, fewer chunks
- Smaller = more granular, more chunks

**CHUNK_OVERLAP:**
- Number of characters that overlap between chunks
- Default: 200 characters
- Prevents context loss at chunk boundaries

---

## Usage

### Starting the Application

From the project root directory:

```bash
./start.sh
```

This script will:
1. Validate prerequisites
2. Start backend server (port 8000)
3. Start frontend server (port 5173)
4. Display access URLs and logs

### Accessing the Application

Open your browser to: `http://localhost:5173`

### Stopping the Application

```bash
./stop.sh
```

### Basic Workflow

1. **Create Engagement**
   - Click "New Engagement"
   - Enter engagement name and optional details
   - Click "Create"

2. **Upload Documents**
   - Select the engagement
   - Navigate to "Documents" tab
   - Drag and drop files or click to browse
   - Wait for processing to complete

3. **Ask Questions**
   - Navigate to "Q&A" tab
   - Type your question or upload a questions file
   - View AI-generated answer with citations
   - Click citations to view source documents

4. **View History**
   - Navigate to "History" tab
   - Browse all previous questions and answers
   - Click to expand details
   - Review citations and confidence scores

---

## API Documentation

### Interactive Documentation

When the backend is running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Core Endpoints

**Engagements:**
```
POST   /api/engagements              Create engagement
GET    /api/engagements              List all engagements
GET    /api/engagements/{id}         Get engagement details
DELETE /api/engagements/{id}         Delete engagement
```

**Documents:**
```
POST   /api/engagements/{id}/documents              Upload documents
GET    /api/engagements/{id}/documents              List documents
DELETE /api/engagements/{id}/documents/{doc_id}     Delete document
GET    /api/documents/{doc_id}/file                 Download document
```

**Questions:**
```
POST   /api/engagements/{id}/ask              Ask single question
POST   /api/engagements/{id}/batch-ask        Ask multiple questions
POST   /api/engagements/{id}/batch-ask-file   Upload questions file
GET    /api/engagements/{id}/history          Get Q&A history
```

---

## Deployment

### Local Development (Current Setup)

The application currently runs on your local machine:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- Access: Local only

### Production Deployment (Azure)

For multi-user access, deploy to Azure:

**Backend (Azure Container Apps):**
1. Build Docker image
2. Push to Azure Container Registry
3. Deploy to Azure Container Apps
4. Configure environment variables

**Frontend (Azure Static Web Apps):**
1. Build production bundle: `npm run build`
2. Deploy to Azure Static Web Apps
3. Configure custom domain (optional)

**Database Migration:**
- Switch from SQLite to Azure SQL Database or PostgreSQL
- Update `DATABASE_URL` environment variable

**Vector Store Migration:**
- Switch from ChromaDB to Azure AI Search
- Update `VECTOR_DB_TYPE=azure_search`
- Configure Azure AI Search credentials

---

## Troubleshooting

### Backend Won't Start

**Issue:** Module not found errors
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**Issue:** Database errors
```bash
rm -rf data/audit_app.db data/chromadb
# Restart backend (database will be recreated)
```

**Issue:** Azure OpenAI authentication fails
- Verify endpoint URL format
- Check API key is correct
- Ensure deployments exist and names match

### Frontend Won't Start

**Issue:** npm command not found
```bash
# Install Node.js
brew install node
```

**Issue:** Dependencies not installed
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Issue:** CORS errors
- Ensure backend is running on port 8000
- Check `BACKEND_CORS_ORIGINS` includes frontend URL

### Upload Failures

**Issue:** File too large
- Check MAX_UPLOAD_SIZE_MB in .env
- Default limit is 100MB

**Issue:** Unsupported file type
- Only PDF, DOCX, DOC, TXT supported
- Check file extension

**Issue:** Processing fails
- Check Azure OpenAI deployment names
- Verify API key has permissions
- Review backend logs for detailed error

---

## Contributing

### Code Structure

```
backend/
├── app/
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # Database models
│   ├── db_session.py        # Session management
│   ├── models.py            # API request/response models
│   ├── routes/              # API route handlers
│   │   ├── engagements.py
│   │   ├── documents.py
│   │   ├── questions.py
│   │   └── document_files.py
│   └── services/            # Business logic
│       ├── document_processor.py
│       ├── embedding_service.py
│       ├── vector_store.py
│       └── qa_service.py
├── requirements.txt
└── .env

frontend/
├── src/
│   ├── components/          # React components
│   ├── pages/              # Page components
│   ├── api.js              # API client
│   ├── App.jsx             # Main application
│   └── main.jsx            # Entry point
├── package.json
└── vite.config.js
```

### Development Guidelines

1. Follow PEP 8 for Python code
2. Use ESLint configuration for JavaScript
3. Write descriptive commit messages
4. Add comments for complex logic
5. Update documentation for new features

---

## License

Proprietary - Internal Use Only

---

## Support

For technical support or questions:
- Review documentation in `/docs` directory
- Check API documentation at http://localhost:8000/docs
- Review troubleshooting section above

---

## Additional Resources

- **Setup Details:** See `SETUP.md` for detailed installation steps
- **Architecture:** See `SETUP_VERIFICATION.md` for system architecture
- **Deployment:** See `DEPLOYMENT_INFO.md` for production deployment guide
