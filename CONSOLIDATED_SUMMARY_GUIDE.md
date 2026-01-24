# Consolidated Session Summary Feature

## Overview
The system now generates a **single consolidated summary for the entire session** that includes all uploaded documents. When new documents are uploaded, the session summary is automatically regenerated to include the new content.

## How It Works

### Upload Flow:
1. **Upload Document 1** → Background task generates session summary from Doc1
2. **Upload Document 2** → Background task regenerates session summary from Doc1 + Doc2 combined
3. **Upload Document 3** → Background task regenerates session summary from Doc1 + Doc2 + Doc3 combined

Each upload triggers a new consolidated summary that encompasses all documents in the session.

## API Endpoints

### Get Consolidated Session Summary
```
GET /sessions/{session_id}/summary
```

**Response:**
```json
{
  "session_id": "uuid",
  "summary": "Comprehensive summary of all documents in the session...",
  "status": "ready"
}
```

**Status values:**
- `ready` - Summary is available
- `generating` - Summary is still being generated in the background

### List Documents in Session
```
GET /sessions/{session_id}/documents
```

Returns list of all documents (for reference; they no longer have individual summaries).

## Example Workflow in Postman

### Step 1: Create Session
```
POST http://localhost:8000/sessions
Body (JSON):
{
  "session_name": "My Analysis",
  "primary_llm": "gemini"
}
```
Save the `session_id` from response.

### Step 2: Upload First Document
```
POST http://localhost:8000/sessions/{session_id}/upload
Body: form-data
Key: file
Value: [select document1.pdf]
```
Response returns immediately. Background task generates initial session summary.

### Step 3: Check Summary Status (after 10-30 seconds)
```
GET http://localhost:8000/sessions/{session_id}/summary
```
Should return the summary generated from Document 1.

### Step 4: Upload Second Document
```
POST http://localhost:8000/sessions/{session_id}/upload
Body: form-data
Key: file
Value: [select document2.pdf]
```
Response returns immediately. Background task regenerates session summary with both documents.

### Step 5: Check Updated Summary (after 10-30 seconds)
```
GET http://localhost:8000/sessions/{session_id}/summary
```
Summary now includes content from both Document 1 and Document 2.

### Step 6: Upload More Documents (Optional)
Repeat steps 4-5 for any additional documents. Each upload updates the consolidated summary.

## Key Changes from Previous Version

| Aspect | Previous | Current |
|--------|----------|---------|
| Summary Scope | Per-document | Session-wide |
| When Generated | Per document upload | Per session (all docs combined) |
| Update Behavior | Each doc has own summary | One summary regenerated with each upload |
| Endpoint | `/summaries` (list all docs) | `/summary` (single consolidated) |
| Multiple Docs | Multiple separate summaries | One summary covering all |

## Background Processing

### Timeline for Each Upload:
1. **0-5 seconds** - File parsed, embeddings generated
2. **5-10 seconds** - Upload API returns with success
3. **10-30 seconds** - Background task reads all documents
4. **20-40 seconds** - LLM generates consolidated summary
5. **40-45 seconds** - Summary stored in database

You can check status anytime:
```bash
GET /sessions/{session_id}/summary
# Returns: "status": "ready" if done, or empty summary if still generating
```

## Logging

Watch the terminal logs for progress:

```
[BACKGROUND] Starting session summary generation...
[BACKGROUND] Generating consolidated summary for session with 2 document(s)
[BACKGROUND] ✅ Generated consolidated session summary using Gemini
[BACKGROUND] ✅ Session summary stored for session {session_id}
```

## Notes

✅ **Non-blocking** - Upload returns immediately, summary generated in background
✅ **Comprehensive** - Summary includes key points from all documents
✅ **Updated** - Each new upload automatically updates the consolidated summary
✅ **Session-based** - One summary per session, not per document
✅ **Smart Limits** - Limits total input to ~10,000 chars to avoid token limits
✅ **Fallback Support** - Uses primary LLM with fallbacks (Gemini → ChatGPT → Groq)

## Troubleshooting

### Q: Summary field is empty?
**A:** Summary is still being generated. Wait 20-40 seconds and check again. Check logs for errors.

### Q: Summary hasn't updated after uploading new doc?
**A:** Background task is running. Wait 30-40 seconds and retry the GET request.

### Q: Want individual document summaries?
**A:** The legacy endpoint `/sessions/{session_id}/summaries` still exists but returns empty per-document summaries. The focus is now on the consolidated session summary via `/summary`.

## Database Changes

New table: `session_summaries`
- `session_id` - Link to session
- `summary` - The consolidated summary text
- `updated_at` - Last time summary was generated

Removed: Individual document summaries (summary field in documents table is deprecated)
