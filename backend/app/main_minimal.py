import os
import io
import re
import uuid
import json
from typing import List, Optional, Dict, Any
import logging

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import fitz  # PyMuPDF
from docx import Document
import nltk
from nltk.tokenize import sent_tokenize
import requests

# Ensure punkt tokenizer for NLTK
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

app = FastAPI(title="Doc Q&A (Gemini-Only)")

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (simplified)
SESSIONS = {}

class UploadResponse(BaseModel):
    session_id: str
    message: str
    chunks_processed: int

class AskRequest(BaseModel):
    session_id: str
    question: str
    k: int = 5
    gemini_api_key: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    method: str
    chunks_used: List[str]

@app.get("/")
async def root():
    return {"message": "Document Q&A API - Gemini Only", "status": "ready"}

@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...), 
    session_id: Optional[str] = Form(None),
    gemini_api_key: Optional[str] = Form(None)
):
    try:
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        text = ""
        if file.filename.lower().endswith('.pdf'):
            pdf_doc = fitz.open(stream=content, filetype="pdf")
            for page in pdf_doc:
                text += page.get_text()
        elif file.filename.lower().endswith('.docx'):
            doc = Document(io.BytesIO(content))
            text = "\n".join([para.text for para in doc.paragraphs])
        elif file.filename.lower().endswith('.txt'):
            text = content.decode('utf-8', errors='ignore')
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text found in document")
        
        # Simple chunking using NLTK
        sentences = sent_tokenize(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < 500:  # Keep chunks under 500 chars
                current_chunk += " " + sentence
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Store in session (Gemini-only mode)
        SESSIONS[session_id] = {
            "filename": file.filename,
            "chunks": chunks,
            "gemini_key": gemini_api_key,
            "text": text,
            "events": [{"event": "upload", "timestamp": "now", "file": file.filename}]
        }
        
        return UploadResponse(
            session_id=session_id,
            message=f"Document processed successfully using Gemini-only mode",
            chunks_processed=len(chunks)
        )
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    try:
        if request.session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = SESSIONS[request.session_id]
        gemini_key = request.gemini_api_key or session_data.get("gemini_key")
        
        if not gemini_key:
            raise HTTPException(status_code=400, detail="Gemini API key required")
        
        # Use Gemini AI directly with full document text
        document_text = session_data["text"]
        
        # Create context-aware prompt
        prompt = f"""Based on the following document, please answer the question accurately and concisely.

Document:
{document_text[:4000]}  # Limit context to avoid token limits

Question: {request.question}

Please provide a clear, accurate answer based solely on the information in the document."""

        # Call Gemini API
        gemini_response = await call_gemini_api(prompt, gemini_key)
        
        if gemini_response:
            return AskResponse(
                answer=gemini_response,
                method="Gemini AI",
                chunks_used=["Full document context"]
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to get response from Gemini")
            
    except Exception as e:
        logger.error(f"Ask error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def call_gemini_api(prompt: str, api_key: str) -> Optional[str]:
    """Call Gemini API directly"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    return candidate["content"]["parts"][0]["text"]
        
        logger.error(f"Gemini API error: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Gemini API call failed: {str(e)}")
        return None

@app.get("/models")
async def get_models(gemini_api_key: Optional[str] = None):
    """Get available models"""
    models = ["gemini-1.5-flash", "gemini-1.5-pro"]
    return {
        "gemini_models": models if gemini_api_key else [],
        "sbert_available": False,  # Disabled in minimal version
        "message": "Minimal version - Gemini only"
    }

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    info = SESSIONS[session_id]
    return {
        "session_id": session_id,
        "filename": info.get("filename"),
        "chunks_count": len(info.get("chunks", [])),
        "has_gemini_key": bool(info.get("gemini_key")),
        "mode": "gemini_only"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)