"""
Quick test to see if query endpoint is hanging
"""
import requests
import time

BASE_URL = "http://localhost:8000"

print("\nTesting if query endpoint is hanging...")
print("This will timeout after 30 seconds if stuck\n")

# Create a quick session and upload
try:
    print("1. Creating session...")
    response = requests.post(
        f"{BASE_URL}/sessions",
        json={"session_name": "Timeout Test", "primary_llm": "gemini"}
    )
    session_id = response.json()["session_id"]
    print(f"   Session: {session_id}")
    
    print("\n2. Uploading document...")
    test_doc = "FINQUEST AI is a document assistant created in 2024."
    files = {'file': ('test.txt', test_doc.encode(), 'text/plain')}
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/upload",
        files=files
    )
    print(f"   Upload status: {response.status_code}")
    
    print("\n3. Testing query endpoint (30 second timeout)...")
    start = time.time()
    
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/query",
        json={"session_id": session_id, "question": "What is FINQUEST AI?", "k": 3},
        timeout=30  # 30 second timeout
    )
    
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Response received in {elapsed:.2f} seconds")
        print(f"   LLM Used: {data.get('llm_used')}")
        print(f"   Answer: {data.get('answer', '')[:100]}...")
    else:
        print(f"   [ERROR] Status: {response.status_code}")
        
except requests.exceptions.Timeout:
    print(f"\n   [ERROR] REQUEST TIMED OUT!")
    print(f"   The query endpoint is hanging/stuck")
    print(f"   This usually means:")
    print(f"   - Local LLM is stuck loading")
    print(f"   - Local LLM generation is too slow")
    print(f"   - Backend process is blocked")
    
except Exception as e:
    print(f"\n   [ERROR] {e}")

finally:
    print("\nCleaning up...")
    try:
        requests.delete(f"{BASE_URL}/sessions/{session_id}", timeout=5)
    except:
        pass

print("\nDone.")

