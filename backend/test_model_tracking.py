"""
Test to verify model name tracking in API responses
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("\n" + "="*60)
print("FINQUEST AI - Model Tracking Test")
print("="*60)

# Test 1: Check if backend is running
print("\n1. Testing backend health...")
try:
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("   [OK] Backend is running")
    else:
        print("   [ERROR] Backend not responding correctly")
        exit(1)
except Exception as e:
    print(f"   [ERROR] Backend not running: {e}")
    exit(1)

# Test 2: Create test session
print("\n2. Creating test session...")
try:
    response = requests.post(
        f"{BASE_URL}/sessions",
        json={"session_name": "Model Tracking Test", "primary_llm": "gemini"}
    )
    if response.status_code == 200:
        session_id = response.json()["session_id"]
        print(f"   [OK] Session created: {session_id}")
    else:
        print(f"   [ERROR] Failed: {response.status_code}")
        exit(1)
except Exception as e:
    print(f"   [ERROR] {e}")
    exit(1)

# Test 3: Upload document and check embedding model
print("\n3. Uploading document (testing model tracking)...")
test_content = """
FINQUEST AI Model Tracking Test
This document tests if the system properly tracks which models are used.
The embedding model and LLM model names should be included in API responses.
"""
try:
    files = {'file': ('test_models.txt', test_content.encode(), 'text/plain')}
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/upload",
        files=files
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Document uploaded successfully")
        print(f"")
        print(f"   Response Fields:")
        print(f"   - embed_provider: {data.get('embed_provider', 'NOT FOUND')}")
        print(f"   - embedding_model: {data.get('embedding_model', 'NOT FOUND')}")
        print(f"   - used_fallback: {data.get('used_fallback', 'NOT FOUND')}")
        print(f"")
        
        if 'embedding_model' in data and data['embedding_model']:
            print(f"   >>> MODEL TRACKING WORKING FOR UPLOAD! <<<")
            print(f"   >>> Embedding Model: {data['embedding_model']} <<<")
        else:
            print(f"   [WARN] embedding_model field not found or empty")
    else:
        print(f"   [ERROR] {response.status_code} - {response.text[:200]}")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 4: Query and check both embedding and LLM models
print("\n4. Querying document (testing model tracking)...")
try:
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/query",
        json={
            "session_id": session_id,
            "question": "What is this document about?",
            "k": 3
        }
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Query successful")
        print(f"")
        print(f"   Response Fields:")
        print(f"   - llm_used: {data.get('llm_used', 'NOT FOUND')}")
        print(f"   - llm_model: {data.get('llm_model', 'NOT FOUND')}")
        print(f"   - embedding_model: {data.get('embedding_model', 'NOT FOUND')}")
        print(f"   - used_fallback: {data.get('used_fallback', 'NOT FOUND')}")
        print(f"")
        print(f"   Answer Preview:")
        print(f"   {data.get('answer', 'No answer')[:150]}...")
        print(f"")
        
        if 'embedding_model' in data and 'llm_model' in data:
            if data['embedding_model'] and data['llm_model']:
                print(f"   >>> MODEL TRACKING WORKING FOR QUERIES! <<<")
                print(f"   >>> Embedding: {data['embedding_model']} <<<")
                print(f"   >>> LLM: {data['llm_model']} <<<")
            else:
                print(f"   [WARN] Model fields exist but are empty")
        else:
            print(f"   [ERROR] Model tracking fields missing!")
    else:
        print(f"   [ERROR] {response.status_code} - {response.text[:200]}")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 5: Cleanup
print("\n5. Cleaning up...")
try:
    requests.delete(f"{BASE_URL}/sessions/{session_id}")
    print("   [OK] Test session deleted")
except:
    pass

# Summary
print("\n" + "="*60)
print("Test Complete - Model Tracking Summary")
print("="*60)
print("\nExpected Response Structure:")
print("{")
print('  "embed_provider": "gemini",')
print('  "embedding_model": "text-embedding-004",')
print('  "llm_used": "gemini",')
print('  "llm_model": "gemini-2.0-flash-exp",')
print('  "used_fallback": false,')
print('  "answer": "..."')
print("}")
print("\nWith valid Gemini API key, you should see:")
print("- Embedding Model: text-embedding-004")
print("- LLM Model: gemini-2.0-flash-exp")
print("\nWith fallback, you might see:")
print("- Embedding Model: sentence-transformers/all-MiniLM-L6-v2")
print("- LLM Model: orca-mini-3b-gguf2-q4_0.gguf or rule-based-extraction")
print()

