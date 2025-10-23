"""
Simple diagnostic test for fallback mechanism
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("\n" + "="*60)
print("FINQUEST AI - Fallback Diagnostic Test")
print("="*60)

# Test 1: Check if backend is running
print("\n1. Testing backend health...")
try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   [ERROR] Backend not running: {e}")
    print("   Please start the backend first!")
    exit(1)

# Test 2: Check current config
print("\n2. Checking current API configuration...")
try:
    response = requests.get(f"{BASE_URL}/config")
    if response.status_code == 200:
        configs = response.json()
        print(f"   Gemini API Key: {'SET' if configs.get('gemini_api_key') else 'NOT SET'}")
        print(f"   ChatGPT API Key: {'SET' if configs.get('chatgpt_api_key') else 'NOT SET'}")
except Exception as e:
    print(f"   [WARN] Could not get config: {e}")

# Test 3: Set invalid API keys for testing
print("\n3. Setting INVALID API keys for fallback test...")
try:
    # Save current keys first
    response = requests.get(f"{BASE_URL}/config")
    original_config = response.json() if response.status_code == 200 else {}
    
    # Set invalid keys
    requests.post(f"{BASE_URL}/config", json={"key_name": "gemini_api_key", "key_value": "INVALID_TEST_KEY"})
    requests.post(f"{BASE_URL}/config", json={"key_name": "chatgpt_api_key", "key_value": "INVALID_TEST_KEY"})
    print("   Invalid keys set for testing")
except Exception as e:
    print(f"   [ERROR] Failed to set keys: {e}")

# Test 4: Create test session
print("\n4. Creating test session...")
try:
    response = requests.post(f"{BASE_URL}/sessions", json={"session_name": "Fallback Test", "primary_llm": "gemini"})
    if response.status_code == 200:
        session_id = response.json()["session_id"]
        print(f"   Session created: {session_id}")
    else:
        print(f"   [ERROR] Failed: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"   [ERROR] {e}")
    exit(1)

# Test 5: Upload document
print("\n5. Uploading test document...")
test_content = """
FINQUEST AI is an intelligent document assistant.
It was created in 2024 to help users query their documents.
The system supports PDF, DOCX, and TXT files.
FINQUEST AI uses RAG (Retrieval-Augmented Generation) technology.
"""
try:
    files = {'file': ('test.txt', test_content.encode(), 'text/plain')}
    response = requests.post(f"{BASE_URL}/sessions/{session_id}/upload", files=files)
    if response.status_code == 200:
        data = response.json()
        print(f"   Upload: SUCCESS")
        print(f"   Chunks: {data.get('chunk_count', 0)}")
        print(f"   Embed provider: {data.get('embed_provider', 'unknown')}")
        print(f"   Used fallback: {data.get('used_fallback', False)}")
        if data.get('used_fallback'):
            print("   >>> FALLBACK WORKING FOR EMBEDDINGS <<<")
    else:
        print(f"   [ERROR] {response.status_code} - {response.text[:200]}")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 6: Query with fallback
print("\n6. Testing query with fallback...")
try:
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/query",
        json={"session_id": session_id, "question": "What is FINQUEST AI?", "k": 3}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Query: SUCCESS")
        print(f"   LLM used: {data.get('llm_used', 'unknown')}")
        print(f"   Used fallback: {data.get('used_fallback', False)}")
        print(f"   Answer: {data.get('answer', 'No answer')[:150]}...")
        
        if data.get('used_fallback'):
            print("   >>> FALLBACK WORKING FOR GENERATION <<<")
            if data.get('llm_used') == 'local-llm':
                print("   >>> LOCAL LLM DETECTED AND WORKING <<<")
            elif data.get('llm_used') == 'heuristic':
                print("   >>> HEURISTIC FALLBACK ACTIVE (Local LLM not available) <<<")
        else:
            print("   >>> WARNING: Fallback flag is FALSE - this might be an issue <<<")
    else:
        print(f"   [ERROR] {response.status_code} - {response.text[:200]}")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 7: Cleanup
print("\n7. Cleaning up...")
try:
    requests.delete(f"{BASE_URL}/sessions/{session_id}")
    print("   Test session deleted")
except:
    pass

# Test 8: Restore original keys (if you had valid ones)
print("\n8. Restoring original configuration...")
print("   [INFO] You may need to manually restore your valid API keys")
print("   Use the frontend Settings tab or API endpoint to set your real keys")

print("\n" + "="*60)
print("Test Complete")
print("="*60)
print()

