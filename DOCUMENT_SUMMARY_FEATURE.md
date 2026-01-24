# Document Summary Feature

## Overview
Added automatic document summarization functionality to the DigiHuman backend. When documents are uploaded, summaries are automatically generated using LLM APIs and stored with the document metadata. Users can retrieve summaries via new API endpoints.

## Implementation Details

### 1. Database Schema Updates (`db.py`)
- Added `summary` field to document storage
- New methods:
  - `add_document()` - now accepts optional `summary` parameter
  - `update_document_summary()` - update summary for existing document
  - `get_document()` - retrieve a specific document by ID
  - `get_document_summary()` - get summary for a document
  - `get_summaries_by_session()` - retrieve all documents with summaries for a session

### 2. Summarization Functions (`main.py`)
Created a set of summarization functions with multi-provider support:

#### Primary Functions:
- `generate_summary_with_gemini()` - Uses Gemini API
- `generate_summary_with_chatgpt()` - Uses ChatGPT/OpenAI API
- `generate_summary_with_groq()` - Uses Groq API (fast & free fallback)

#### Main Orchestrator:
- `generate_document_summary()` - Generates summary with intelligent fallback strategy:
  1. Tries primary LLM from session config
  2. Falls back to alternative provider
  3. Falls back to Groq (if configured)
  4. Returns `None` if all LLMs unavailable

**Features:**
- Limits input text to 5000 characters to avoid token limits
- Generates 200-300 word summaries
- Focuses on key points and main concepts
- Handles all document types (PDF, DOCX, TXT, MD, HTML)
- Uses same API keys configured for document embeddings

### 3. Updated Upload Endpoint
The `/sessions/{session_id}/upload` endpoint now:
1. Parses and chunks the document (as before)
2. Generates embeddings (as before)
3. **NEW:** Generates document summary using `generate_document_summary()`
4. **NEW:** Stores summary in database when adding document
5. Returns success message in logs

### 4. New API Endpoints

#### Get All Summaries for a Session
```
GET /sessions/{session_id}/summaries
```
**Response:**
```json
{
  "session_id": "uuid",
  "summaries": [
    {
      "document_id": "uuid",
      "file_name": "document.pdf",
      "summary": "...",
      "uploaded_at": "2026-01-15T..."
    }
  ]
}
```

#### Get Summary for Specific Document
```
GET /sessions/{session_id}/documents/{document_id}/summary
```
**Response:**
```json
{
  "document_id": "uuid",
  "file_name": "document.pdf",
  "summary": "...",
  "uploaded_at": "2026-01-15T..."
}
```

### 5. Pydantic Models
Added response models:
- `SummaryResponse` - Single document summary
- `SessionSummariesResponse` - Collection of summaries for a session

## Key Features

✅ **Session-based** - Summaries are tied to session_id like everything else
✅ **LLM Agnostic** - Works with Gemini, ChatGPT, or Groq
✅ **Intelligent Fallbacks** - Automatically tries alternative providers if primary LLM fails
✅ **Efficient** - Limits text to 5000 chars to avoid excessive token usage
✅ **Integrated** - Uses existing API key configuration from database
✅ **Non-blocking** - If summary generation fails, document upload still succeeds
✅ **RESTful** - Clear API endpoints for retrieving summaries

## Usage Example

### 1. Upload document (summary generated automatically)
```bash
POST /sessions/{session_id}/upload
Content-Type: multipart/form-data
file: document.pdf
```

### 2. Get all summaries in session
```bash
GET /sessions/{session_id}/summaries
```

### 3. Get specific document summary
```bash
GET /sessions/{session_id}/documents/{document_id}/summary
```

## Error Handling
- If all LLM providers fail, summary field is empty string
- Document upload succeeds even if summary generation fails
- Proper HTTP error codes for invalid sessions/documents
- Detailed logging for debugging summary generation issues

## Configuration
Uses existing config from `~/.rag-assistant/db.json`:
- `gemini_api_key` - Gemini API key
- `chatgpt_api_key` - OpenAI/ChatGPT API key
- `groq_api_key` - Groq API key

All are optional. If no keys are configured, summaries will not be generated.

## File Changes
- **backend/app/db.py** - Added summary storage and retrieval methods
- **backend/app/main.py** - Added summarization functions and new API endpoints
