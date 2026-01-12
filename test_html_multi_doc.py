"""
End-to-end test for HTML support with multi-document scenarios
Tests: HTML upload → Multi-format documents → Query across all documents
"""
import requests
import json
import os
import time

BASE_URL = "http://localhost:8000"

# Read API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

def test_health():
    """Test backend health"""
    print("1. Testing backend health...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"
    print(f"   [OK] Backend is healthy")

def test_set_api_key():
    """Set ChatGPT API key if available"""
    if not OPENAI_API_KEY:
        print("   [SKIP] No OPENAI_API_KEY in environment, skipping API key setup")
        return
    
    print("\n2. Setting ChatGPT API key...")
    response = requests.post(
        f"{BASE_URL}/config",
        json={"key_name": "chatgpt_api_key", "key_value": OPENAI_API_KEY}
    )
    if response.status_code == 200:
        print(f"   [OK] API key set successfully")
    else:
        print(f"   [WARN] Failed to set API key: {response.status_code}")

def test_create_session():
    """Create a ChatGPT session"""
    print("\n3. Creating ChatGPT session...")
    response = requests.post(
        f"{BASE_URL}/sessions",
        json={"session_name": "Multi-Format Test Session", "primary_llm": "chatgpt"}
    )
    assert response.status_code == 200, f"Failed to create session: {response.status_code}"
    session = response.json()
    session_id = session["session_id"]
    print(f"   [OK] Session created: {session_id}")
    return session_id

def test_upload_html(session_id):
    """Test uploading HTML file"""
    print("\n4. Uploading HTML document...")
    html_file = "testData/sample.html"
    
    if not os.path.exists(html_file):
        print(f"   [FAIL] HTML file not found: {html_file}")
        return None
    
    with open(html_file, "rb") as f:
        files = {"file": ("sample.html", f, "text/html")}
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/upload",
            files=files
        )
    
    if response.status_code != 200:
        print(f"   [FAIL] Failed to upload HTML: {response.status_code} - {response.text}")
        return None
    
    result = response.json()
    print(f"   [OK] HTML uploaded: {result.get('file_name')} ({result.get('chunks_indexed')} chunks)")
    return result

def test_upload_docx(session_id):
    """Test uploading DOCX file (multi-document)"""
    print("\n5. Uploading DOCX document (multi-document test)...")
    docx_file = "testData/sample1.docx"
    
    if not os.path.exists(docx_file):
        print(f"   [SKIP] DOCX file not found: {docx_file}")
        return None
    
    with open(docx_file, "rb") as f:
        files = {"file": ("sample1.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/upload",
            files=files
        )
    
    if response.status_code != 200:
        print(f"   [FAIL] Failed to upload DOCX: {response.status_code} - {response.text}")
        return None
    
    result = response.json()
    print(f"   [OK] DOCX uploaded: {result.get('file_name')} ({result.get('chunks_indexed')} chunks)")
    return result

def test_list_documents(session_id):
    """Test listing all documents"""
    print("\n6. Listing all documents in session...")
    response = requests.get(f"{BASE_URL}/sessions/{session_id}/documents")
    
    if response.status_code != 200:
        print(f"   [FAIL] Failed to list documents: {response.status_code}")
        return []
    
    documents = response.json()
    print(f"   [OK] Found {len(documents)} documents:")
    for doc in documents:
        print(f"      - {doc.get('file_name')} ({doc.get('file_type')}) - {doc.get('chunk_count')} chunks")
    return documents

def test_query_html_content(session_id):
    """Test querying HTML-specific content"""
    print("\n7. Querying HTML-specific content...")
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/query",
        json={"question": "What technologies does NTT DATA specialize in?", "k": 5}
    )
    
    if response.status_code != 200:
        print(f"   [FAIL] Query failed: {response.status_code} - {response.text}")
        return None
    
    result = response.json()
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    
    print(f"   [OK] Query successful!")
    print(f"   Answer: {answer[:200]}...")
    print(f"   Sources: {len(sources)} found")
    
    # Check if HTML content was used
    if "Cloud Computing" in answer or "Artificial Intelligence" in answer or "Blockchain" in answer:
        print(f"   [OK] HTML content was successfully used in answer!")
    else:
        print(f"   [WARN] HTML content may not have been used")
    
    return result

def test_query_multi_document(session_id):
    """Test querying across multiple documents"""
    print("\n8. Querying across multiple documents (HTML + DOCX)...")
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/query",
        json={"question": "What is NTT DATA and what are its main services?", "k": 5}
    )
    
    if response.status_code != 200:
        print(f"   [FAIL] Query failed: {response.status_code} - {response.text}")
        return None
    
    result = response.json()
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    llm_used = result.get("llm_used", "")
    embed_provider = result.get("embed_provider", "")
    
    print(f"   [OK] Multi-document query successful!")
    print(f"   LLM Used: {llm_used}")
    print(f"   Embed Provider: {embed_provider}")
    print(f"   Answer: {answer[:250]}...")
    print(f"   Sources: {len(sources)} found")
    
    # Check if multiple documents were referenced
    unique_docs = set()
    for source in sources:
        doc_name = source.get("doc", "")
        if doc_name:
            unique_docs.add(doc_name)
    
    print(f"   Documents referenced: {len(unique_docs)}")
    if len(unique_docs) > 1:
        print(f"   [OK] Multiple documents were used in the answer!")
    else:
        print(f"   [INFO] Answer used {len(unique_docs)} document(s)")
    
    return result

def main():
    """Run all tests"""
    print("=" * 60)
    print("HTML Support + Multi-Document End-to-End Test")
    print("=" * 60)
    
    try:
        test_health()
        test_set_api_key()
        session_id = test_create_session()
        
        # Wait for session to be ready
        time.sleep(1)
        
        # Upload HTML file
        html_result = test_upload_html(session_id)
        if not html_result:
            print("\n[FAIL] HTML upload failed, cannot continue")
            return 1
        
        # Wait for processing
        print("\n   Waiting for HTML processing...")
        time.sleep(3)
        
        # Upload DOCX file (multi-document)
        docx_result = test_upload_docx(session_id)
        if docx_result:
            print("\n   Waiting for DOCX processing...")
            time.sleep(3)
        
        # List all documents
        documents = test_list_documents(session_id)
        
        if len(documents) < 1:
            print("\n[FAIL] No documents found in session")
            return 1
        
        # Test HTML-specific query
        html_query = test_query_html_content(session_id)
        
        # Test multi-document query
        multi_query = test_query_multi_document(session_id)
        
        print("\n" + "=" * 60)
        print("[OK] All tests completed!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  - HTML upload: {'PASS' if html_result else 'FAIL'}")
        print(f"  - DOCX upload: {'PASS' if docx_result else 'SKIP'}")
        print(f"  - Documents in session: {len(documents)}")
        print(f"  - HTML query: {'PASS' if html_query else 'FAIL'}")
        print(f"  - Multi-document query: {'PASS' if multi_query else 'FAIL'}")
        
        return 0
        
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
