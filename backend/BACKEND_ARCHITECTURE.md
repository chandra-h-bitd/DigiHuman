# Backend Architecture & Mechanism

## 📚 Core Libraries & Technologies

### **Web Framework**
- **FastAPI** - Modern, fast Python web framework for building APIs
- **Uvicorn** - ASGI server for running FastAPI
- **Pydantic** - Data validation using Python type annotations

### **Vector Search & Embeddings**
- **FAISS (Facebook AI Similarity Search)** - Efficient similarity search and clustering of dense vectors
  - Uses `IndexFlatIP` for cosine similarity (inner product on normalized vectors)
  - Per-session indexes stored on disk
- **Sentence Transformers (SBERT)** - Local embedding model fallback
  - Model: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
  - Used when API keys are unavailable

### **LLM Providers**
- **Google Gemini API** - Primary LLM option
  - Embedding: `text-embedding-004` (768 dimensions)
  - Generation: `gemini-2.0-flash-exp`
- **OpenAI ChatGPT API** - Primary LLM option
  - Embedding: `text-embedding-3-small` (1536 dimensions)
  - Generation: `gpt-4o-mini`
- **Groq API** - Fast fallback LLM (FREE tier available)
  - Generation: `llama-3.1-8b-instant`
  - Extremely fast (3-4 second responses)

### **Document Processing**
- **PyMuPDF (fitz)** - PDF parsing
- **python-docx** - DOCX parsing
- **markdown** - Markdown to text conversion
- **NLTK** - Text tokenization and sentence splitting

### **Storage & Persistence**
- **TinyDB** - Lightweight JSON database for sessions, documents, conversations, and config
- **FAISS** - Vector index persistence on disk
- **File System** - Document storage in `~/.rag-assistant/documents/`

### **HTTP Clients**
- **requests** - Synchronous HTTP requests for API calls
- **aiohttp** - Async HTTP client (available but not heavily used)

---

## 🔄 Fallback Mechanism

### **Embedding Fallback Chain**

```
1. Primary LLM Embedding (Gemini or ChatGPT)
   ↓ (if API key missing/invalid)
2. SBERT (Local) - sentence-transformers/all-MiniLM-L6-v2
   ↓ (if model fails to load)
3. ERROR - Cannot proceed without embeddings
```

**Current Implementation:**
- **Gemini**: 768D embeddings (`text-embedding-004`)
- **ChatGPT**: 1536D embeddings (`text-embedding-3-small`)
- **SBERT Fallback**: 384D embeddings (dimension mismatch warning if switching)

### **Generation (LLM) Fallback Chain**

```
1. Primary LLM (Gemini or ChatGPT based on session)
   ↓ (if API key missing/invalid/error)
2. Groq API (Llama 3.1 8B Instant) - FAST & FREE
   ↓ (if Groq API key missing/fails)
3. Heuristic (Rule-based text extraction)
```

**Current Implementation:**
- **Primary**: Gemini 2.0 Flash or GPT-4o-mini
- **Groq Fallback**: Llama 3.1 8B Instant (3-4 sec response time)
- **Heuristic**: Extracts relevant sentences from top chunks with source citations

---

## 🎯 Better Fallback Options

### **1. Embedding Fallback Improvements**

#### **Current Issue:**
- SBERT (384D) doesn't match Gemini (768D) or ChatGPT (1536D) dimensions
- Requires re-uploading documents when switching models

#### **Recommended Solutions:**

**Option A: Unified Embedding Dimension**
```python
# Use consistent 768D embeddings across all providers
- Gemini: text-embedding-004 (768D) ✅
- OpenAI: text-embedding-3-small with dimensions=768 parameter
- SBERT: Use larger model like all-mpnet-base-v2 (768D)
```

**Option B: Multiple Embedding Models**
```python
# Support multiple embedding dimensions per session
# Store which embedding model was used per chunk
# Route queries to correct index based on model
```

**Option C: Embedding Dimension Conversion**
```python
# Use PCA or linear projection to convert between dimensions
# Not ideal but allows cross-model compatibility
from sklearn.decomposition import PCA
```

### **2. Generation Fallback Improvements**

#### **Current Implementation:**
✅ **Groq** - Already excellent choice (fast, free, high quality)

#### **Additional Fallback Options:**

**Option A: Add Anthropic Claude (via API)**
```python
# Pros: High quality, good for complex reasoning
# Cons: Paid, slower than Groq
# Priority: Medium (if budget allows)
```

**Option B: Add Cohere API**
```python
# Pros: Good quality, reasonable pricing
# Cons: Not as fast as Groq
# Priority: Low (Groq is better)
```

**Option C: Add Local LLM (Ollama)**
```python
# Pros: No API costs, privacy, offline capable
# Cons: Requires local GPU, slower, setup complexity
# Implementation:
# - Use ollama Python client
# - Models: llama3, mistral, phi-3
# - Priority: High for privacy-sensitive use cases
```

**Option D: Add Hugging Face Inference API**
```python
# Pros: Many models available, some free tier
# Cons: Rate limits, variable quality
# Priority: Low
```

**Option E: Improve Heuristic Fallback**
```python
# Current: Simple sentence extraction
# Better: Use BM25 (keyword-based) + sentence ranking
# Already have rank-bm25 in requirements.txt!
# Priority: Medium (quick win)
```

### **3. Recommended Fallback Priority**

**For Embeddings:**
1. ✅ Keep SBERT as fallback (works well)
2. 🔄 Upgrade to 768D SBERT model for consistency
3. ⚠️ Add dimension conversion layer if needed

**For Generation:**
1. ✅ **Keep Groq** - Excellent current choice
2. 🆕 **Add Ollama** - For privacy/offline scenarios
3. 🆕 **Improve Heuristic** - Use BM25 + better extraction
4. ⚠️ **Add Claude** - Only if budget allows and need better reasoning

---

## 🏗️ Architecture Flow

### **Document Upload Flow:**
```
1. Parse document (PDF/DOCX/TXT/MD)
2. Chunk text (smart chunking with overlap)
3. Generate embeddings:
   - Try primary LLM embedding API
   - Fallback to SBERT if needed
4. Store vectors in FAISS index (per session)
5. Save document metadata to TinyDB
```

### **Query Flow:**
```
1. User asks question
2. Generate query embedding:
   - Try primary LLM embedding API
   - Fallback to SBERT if needed
3. Search FAISS index (cosine similarity)
4. Retrieve top K chunks
5. Generate answer:
   - Try primary LLM generation API
   - Fallback to Groq
   - Final fallback to heuristic
6. Return answer with source citations
```

---

## 💡 Specific Recommendations

### **Immediate Improvements (Quick Wins):**

1. **Upgrade SBERT Model** (5 minutes)
   ```python
   # Change from all-MiniLM-L6-v2 (384D) to:
   model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")  # 768D
   # Matches Gemini embedding dimension!
   ```

2. **Improve Heuristic with BM25** (30 minutes)
   ```python
   from rank_bm25 import BM25Okapi
   # Use BM25 for better keyword matching in heuristic fallback
   ```

3. **Add Ollama Support** (1-2 hours)
   ```python
   # pip install ollama
   import ollama
   # Add as another fallback option
   ```

### **Medium-Term Improvements:**

1. **Support Multiple Embedding Dimensions**
   - Track which embedding model was used per chunk
   - Route queries to correct index

2. **Add Embedding Caching**
   - Cache embeddings for common queries
   - Reduce API calls

3. **Better Error Handling**
   - Retry logic for API failures
   - Exponential backoff

### **Long-Term Improvements:**

1. **Hybrid Search**
   - Combine vector search (semantic) with BM25 (keyword)
   - Better results for specific queries

2. **Reranking**
   - Use cross-encoder for better relevance scoring
   - Re-rank top K results before generation

3. **Streaming Responses**
   - Stream LLM responses for better UX
   - Show partial answers as they generate

---

## 📊 Current Performance Characteristics

| Component | Speed | Quality | Cost |
|-----------|-------|---------|------|
| Gemini Embedding | Fast | High | Free tier available |
| ChatGPT Embedding | Fast | High | Paid |
| SBERT Embedding | Very Fast | Medium | Free (local) |
| Gemini Generation | Medium | High | Free tier available |
| ChatGPT Generation | Medium | High | Paid |
| Groq Generation | **Very Fast** | High | **Free tier** |
| Heuristic | Instant | Low | Free |

**Best Current Setup:**
- **Embeddings**: Gemini (free) → SBERT fallback
- **Generation**: Gemini (free) → Groq (free, fast) → Heuristic

---

## 🔧 Configuration

All settings in `backend/app/config.json`:
- Embedding models
- Generation models
- Chunking parameters
- Retrieval parameters
- Temperature, max tokens

---

## 📝 Summary

**Current Strengths:**
- ✅ Good fallback chain (Groq is excellent)
- ✅ Multiple LLM provider support
- ✅ Efficient FAISS vector search
- ✅ Per-session isolation

**Areas for Improvement:**
- ⚠️ Embedding dimension mismatch (384D vs 768D/1536D)
- ⚠️ Heuristic fallback is basic (can use BM25)
- ⚠️ No local LLM option (Ollama)
- ⚠️ No hybrid search (vector + keyword)

**Recommended Next Steps:**
1. Upgrade SBERT to 768D model (matches Gemini)
2. Add BM25 to heuristic fallback
3. Add Ollama support for privacy/offline use
4. Consider hybrid search for better results

