# Document Summary API - Testing Guide

## 📋 Headers for Postman

### 1. Upload Document (POST) - Summary Generation in Background
```
POST http://localhost:8000/sessions/{session_id}/upload
Content-Type: multipart/form-data
```

**In Postman:**
- Method: **POST**
- URL: `http://localhost:8000/sessions/{session_id}/upload`
- Body → **form-data** tab
  - Key: `file` (Type: **File**)
  - Value: Select your PDF/DOCX/TXT file
- **Headers**: Postman automatically sets `Content-Type: multipart/form-data`

**Response (Instant):**
```json
{
  "document_id": "uuid",
  "session_id": "uuid",
  "file_name": "document.pdf",
  "chunks_indexed": 5,
  "used_fallback": false,
  "embed_provider": "gemini",
  "embedding_model": "text-embedding-004"
}
```
✅ **Upload returns immediately** - Summary is generated in the background!

---

### 2. Get All Summaries for a Session (GET)
```
GET http://localhost:8000/sessions/{session_id}/summaries
Content-Type: application/json
```

**In Postman:**
- Method: **GET**
- URL: `http://localhost:8000/sessions/{session_id}/summaries`
- Headers: (Optional - Postman adds `Content-Type: application/json` by default)

**Response:**
```json
{
  "session_id": "uuid",
  "summaries": [
    {
      "document_id": "uuid",
      "file_name": "document.pdf",
      "summary": "This document discusses...",
      "uploaded_at": "2026-01-15T10:30:00.000000"
    },
    {
      "document_id": "uuid",
      "file_name": "guide.docx",
      "summary": "A comprehensive guide on...",
      "uploaded_at": "2026-01-15T11:00:00.000000"
    }
  ]
}
```

---

### 3. Get Single Document Summary (GET)
```
GET http://localhost:8000/sessions/{session_id}/documents/{document_id}/summary
Content-Type: application/json
```

**In Postman:**
- Method: **GET**
- URL: `http://localhost:8000/sessions/{session_id}/documents/{document_id}/summary`
- Headers: (Optional)

**Response:**
```json
{
  "document_id": "uuid",
  "file_name": "document.pdf",
  "summary": "This document discusses key concepts about...",
  "uploaded_at": "2026-01-15T10:30:00.000000"
}
```

---

## 🔄 How Background Task Works

### Timeline:
1. **Upload API called** → Returns immediately with document_id
2. **In background** → Summary generation starts (happens asynchronously)
3. **Check logs** → See `[BACKGROUND]` prefixed messages
4. **Poll summaries endpoint** → Initially empty, then gets populated as generation completes
5. **Or wait** → Summary appears when background task finishes

### Example Flow:
```
[Step 1] POST /upload → Response returns immediately
[Step 2] GET /summaries → summary field is empty initially
[BACKGROUND] Starting summary generation...
[BACKGROUND] ✅ Summary stored for document.pdf
[Step 3] GET /summaries → summary field now populated
```

---

## 📊 Expected Performance

| Operation | Time |
|-----------|------|
| Upload & parse document | 1-2 seconds |
| Generate embeddings | 2-5 seconds |
| **API response** | **< 10 seconds** ✅ |
| Summary generation (background) | 5-20 seconds (depends on LLM) |

---

## 🔍 Monitoring Summary Generation

### Check Logs for Progress:
```
[BACKGROUND] Starting summary generation for document.pdf (doc_id: xxx)
[BACKGROUND] Trying Gemini as fallback for summary...
[BACKGROUND] ✅ Generated summary using Gemini for document.pdf
[BACKGROUND] ✅ Summary stored for document.pdf (doc_id: xxx)
```

### Empty Summary Causes:
```
[BACKGROUND] ⚠️ Summary generation failed for document.pdf
[BACKGROUND] ⚠️ Failed to generate summary - no LLM available
```

**Reason:** No API keys configured. Set them in config:
```json
{
  "gemini_api_key": "your-key",
  "chatgpt_api_key": "your-key",
  "groq_api_key": "your-key"
}
```

---

## ✅ Test Sequence (Recommended)

### 1. Create a session
```bash
POST http://localhost:8000/sessions
Content-Type: application/json

{
  "session_name": "Test Session",
  "primary_llm": "gemini"
}
```
Copy the `session_id` from response.

### 2. Upload a document
```bash
POST http://localhost:8000/sessions/{session_id}/upload
[Select file in Postman]
```
✅ Should return immediately with document_id

### 3. Check logs for background progress
Watch terminal logs for `[BACKGROUND]` messages

### 4. Retrieve summaries (after 10-30 seconds)
```bash
GET http://localhost:8000/sessions/{session_id}/summaries
```
Summary should now be populated!

### 5. Get specific summary
```bash
GET http://localhost:8000/sessions/{session_id}/documents/{document_id}/summary
```

---

## 🚨 Troubleshooting

### Q: Summary field is empty after waiting?
**A:** Check logs for errors. Likely missing API key configuration.

### Q: Still seeing timeout errors?
**A:** Upload endpoint should return in < 10 seconds. If not:
- Check internet connection
- Verify API keys in config
- Check logs for embedding errors

### Q: Can't see `[BACKGROUND]` messages in logs?
**A:** They appear in the terminal where you started the server.
Make sure you're looking at the correct terminal window.

---

## 📝 Notes

- ✅ Summary generation happens **asynchronously** (non-blocking)
- ✅ Upload returns **immediately** with document metadata
- ✅ Multiple summaries can be generated in parallel
- ✅ If LLM unavailable, document still uploads successfully
- ✅ Empty summary field until background task completes
- ✅ Works with Gemini, ChatGPT, or Groq APIs (with fallbacks)
