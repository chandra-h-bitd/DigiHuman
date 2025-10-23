# Verification Checklist

Use this checklist to verify that everything is working correctly.

## ✅ Installation Verification

### Backend Installation
```bash
cd backend
python --version  # Should be 3.8+
pip list | grep fastapi  # Should show fastapi
pip list | grep tinydb  # Should show tinydb
pip list | grep faiss  # Should show faiss-cpu
```

- [ ] Python 3.8+ installed
- [ ] Virtual environment created
- [ ] All dependencies installed
- [ ] No import errors when running

### Frontend Installation
```bash
cd frontend
node --version  # Should be 18+
npm list --depth=0  # Should show @angular/core etc.
```

- [ ] Node.js 18+ installed
- [ ] Dependencies installed
- [ ] No npm errors

## ✅ Backend Verification

### Start Backend
```bash
cd backend
python -m app.main
```

**Expected Output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

- [ ] Backend starts without errors
- [ ] Accessible at http://localhost:8000
- [ ] /health endpoint returns 200 OK

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "storage_path": "/path/to/.rag-assistant"
}
```

- [ ] Health endpoint responds
- [ ] Storage path is correct

### Test API Documentation
Visit: `http://localhost:8000/docs`

- [ ] Swagger UI loads
- [ ] All endpoints visible
- [ ] Can test endpoints interactively

## ✅ Frontend Verification

### Start Frontend
```bash
cd frontend
npm start
```

**Expected Output:**
```
** Angular Live Development Server is listening on localhost:4200 **
✔ Compiled successfully.
```

- [ ] Frontend compiles without errors
- [ ] Browser opens automatically
- [ ] App loads at http://localhost:4200

### UI Components
- [ ] Header with title and icons visible
- [ ] Dashboard view loads
- [ ] "Create New Session" form visible
- [ ] Settings icon accessible

## ✅ Core Functionality Verification

### Session Management

#### Create Session
1. Click "Create New Session"
2. Enter name: "Test Session"
3. Select LLM: "Gemini"
4. Click "Create Session"

- [ ] Session created successfully
- [ ] Session appears in list
- [ ] Can open session
- [ ] Session view loads

#### Session List
- [ ] All sessions visible
- [ ] Sessions show metadata (docs, conversations)
- [ ] Last activity displayed
- [ ] Can click to open

#### Delete Session
1. Click delete icon on a session
2. Confirm deletion

- [ ] Confirmation dialog appears
- [ ] Session removed from list
- [ ] Data cleaned up

### Document Upload

#### Upload PDF
1. Open a session
2. Upload a PDF file
3. Wait for processing

- [ ] Upload progress shown
- [ ] Document appears in list
- [ ] Chunk count displayed
- [ ] No errors

#### Upload Multiple Formats
Test with:
- [ ] PDF (.pdf)
- [ ] Word (.docx)
- [ ] Text (.txt)
- [ ] Markdown (.md)

#### Drag and Drop
- [ ] Drag zone highlighted on hover
- [ ] Files accepted via drag-and-drop
- [ ] Upload processes correctly

### Query / Chat

#### Ask Question
1. Upload a document
2. Type question: "Summarize this document"
3. Press Enter

- [ ] Question appears in chat
- [ ] Answer generated
- [ ] Sources shown
- [ ] LLM badge displayed

#### Conversation History
- [ ] Previous questions visible
- [ ] Previous answers visible
- [ ] Sources expandable
- [ ] Timestamps shown

#### Out of Context
Ask: "What is the weather today?"

- [ ] System detects out-of-context
- [ ] Appropriate message returned

### Settings

#### API Key Management
1. Open Settings
2. Enter Gemini API key
3. Enter ChatGPT API key
4. Click Save

- [ ] Keys saved successfully
- [ ] Success message shown
- [ ] Keys persist after refresh

#### Persistence
1. Refresh browser
2. Check if keys still work

- [ ] API keys still configured
- [ ] No need to re-enter

## ✅ Persistence Verification

### Session Persistence
1. Create a session
2. Upload document
3. Ask question
4. Restart backend
5. Refresh frontend

- [ ] Session still exists
- [ ] Document still listed
- [ ] Conversation history preserved
- [ ] Can continue conversation

### FAISS Index Persistence
1. Create session with document
2. Close application
3. Restart application
4. Query same session

- [ ] FAISS index loads correctly
- [ ] Search works
- [ ] Results accurate

### Storage Location
Check: `~/.rag-assistant/`

- [ ] db.json exists
- [ ] docs/ directory exists
- [ ] faiss_*.index files exist
- [ ] faiss_*.metadata.pkl files exist

## ✅ LLM Provider Verification

### Gemini API
1. Enter Gemini API key in Settings
2. Create session with Gemini as primary
3. Upload document
4. Ask question

- [ ] Embeddings work
- [ ] Answers generated
- [ ] No API errors

### ChatGPT API
1. Enter ChatGPT API key in Settings
2. Create session with ChatGPT as primary
3. Upload document
4. Ask question

- [ ] Embeddings work
- [ ] Answers generated
- [ ] No API errors

### Fallback to Local
1. Don't enter API keys
2. Create session
3. Upload document
4. Ask question

- [ ] SBERT embeddings used
- [ ] Local LLM or heuristic answer
- [ ] "Fallback" indicated in UI

## ✅ Advanced Features Verification

### Large Document Handling
Upload a PDF with 50+ pages

- [ ] Document processes successfully
- [ ] Chunking works correctly
- [ ] Search is fast
- [ ] Answers are accurate

### Multiple Documents
1. Upload 3-5 documents to one session
2. Ask questions spanning documents

- [ ] All documents indexed
- [ ] Cross-document search works
- [ ] Sources from different documents

### Source Citations
1. Ask a specific question
2. Check answer for citations
3. Expand source details

- [ ] Citations include [Source N]
- [ ] Can expand to see full text
- [ ] Correct document referenced

### Multi-Session Isolation
1. Create Session A with Document A
2. Create Session B with Document B
3. Ask about Document A in Session A
4. Ask about Document A in Session B

- [ ] Session A finds Document A
- [ ] Session B doesn't find Document A
- [ ] Sessions are isolated

## ✅ UI/UX Verification

### Responsive Design
Test on different screen sizes:

- [ ] Desktop (1920x1080)
- [ ] Laptop (1366x768)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

### Animations
- [ ] Smooth page transitions
- [ ] Message animations
- [ ] Progress indicators
- [ ] Hover effects

### Accessibility
- [ ] Icons have tooltips
- [ ] Buttons have labels
- [ ] Forms have proper labels
- [ ] Error messages clear

## ✅ Error Handling Verification

### Backend Errors
1. Stop backend
2. Try to create session from frontend

- [ ] Error message shown
- [ ] UI doesn't crash
- [ ] Can retry when backend restarts

### Invalid File Upload
Upload an invalid file (e.g., .exe)

- [ ] Upload rejected
- [ ] Error message shown
- [ ] Can upload valid file after

### Invalid API Key
Enter invalid API key and query

- [ ] Falls back to local LLM
- [ ] Doesn't crash
- [ ] User notified of fallback

### Empty Document
Upload an empty text file

- [ ] Error message shown
- [ ] Can try different file
- [ ] Session not corrupted

## ✅ Performance Verification

### Upload Performance
- [ ] Small files (< 1MB): < 5 seconds
- [ ] Medium files (1-5MB): < 30 seconds
- [ ] Large files (5-20MB): < 2 minutes

### Query Performance
- [ ] First query: < 10 seconds (model loading)
- [ ] Subsequent queries: < 5 seconds
- [ ] FAISS search: < 1 second

### UI Performance
- [ ] Dashboard loads instantly
- [ ] Session switching is smooth
- [ ] No lag when typing

## ✅ Documentation Verification

### Documentation Files
- [ ] README.md is comprehensive
- [ ] QUICK_START.md is clear
- [ ] SYSTEM_ARCHITECTURE.md is detailed
- [ ] DEPLOYMENT.md covers options
- [ ] All docs have correct info

### Code Comments
- [ ] Backend code is commented
- [ ] Frontend code is commented
- [ ] Complex logic explained

## 🎯 Final Verification

### Complete Workflow Test
1. [ ] Start backend
2. [ ] Start frontend
3. [ ] Configure API keys
4. [ ] Create session
5. [ ] Upload document
6. [ ] Ask multiple questions
7. [ ] Create another session
8. [ ] Upload different document
9. [ ] Switch between sessions
10. [ ] Delete a session
11. [ ] Restart backend
12. [ ] Refresh frontend
13. [ ] Verify data persisted
14. [ ] Continue conversation

### Production Readiness
- [ ] No console errors
- [ ] No Python exceptions
- [ ] Clean logs
- [ ] All features work
- [ ] Performance acceptable
- [ ] UI is polished

## ✅ Sign Off

Once all items are checked:

- [ ] System is fully functional
- [ ] All features implemented
- [ ] Documentation complete
- [ ] Ready for production use

---

**If any item fails, refer to the relevant documentation or troubleshooting section.**

