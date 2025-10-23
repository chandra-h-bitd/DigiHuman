"""
Test script to verify the fallback mechanism works properly
Tests:
1. Invalid/no API keys should fallback to local LLM
2. If local LLM is unavailable, should fallback to heuristic
3. End-to-end flow with document upload and query
"""
import requests
import json
import time
from pathlib import Path

# API Base URL
BASE_URL = "http://localhost:8000"

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def test_health():
    """Test if backend is running"""
    print_header("Testing Backend Health")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Backend is healthy: {data}")
            return True
        else:
            print(f"[ERROR] Backend unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Cannot connect to backend: {e}")
        return False

def test_create_session_with_invalid_keys():
    """Test creating session with invalid API keys"""
    print_header("Testing Session Creation with Invalid API Keys")
    
    # First, set invalid API keys
    try:
        # Set Gemini API key
        response1 = requests.post(
            f"{BASE_URL}/config",
            json={
                "key_name": "gemini_api_key",
                "key_value": "INVALID_KEY_12345"
            }
        )
        # Set ChatGPT API key
        response2 = requests.post(
            f"{BASE_URL}/config",
            json={
                "key_name": "chatgpt_api_key",
                "key_value": "INVALID_KEY_67890"
            }
        )
        print(f"[OK] Set invalid API keys (Gemini: {response1.status_code}, ChatGPT: {response2.status_code})")
    except Exception as e:
        print(f"[ERROR] Failed to set config: {e}")
    
    # Create session
    try:
        response = requests.post(
            f"{BASE_URL}/sessions",
            json={
                "session_name": "Fallback Test Session",
                "primary_llm": "gemini"
            }
        )
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data["session_id"]
            print(f"[OK] Session created: {session_id}")
            return session_id
        else:
            print(f"[ERROR] Session creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Exception creating session: {e}")
        return None

def test_upload_document(session_id):
    """Test uploading a document"""
    print_header(f"Testing Document Upload to Session: {session_id}")
    
    # Create a test document
    test_doc_path = Path("test_fallback_doc.txt")
    test_content = """
    # FINQUEST AI Test Document
    
    This is a test document for FINQUEST AI fallback testing.
    
    Company Information:
    - Company Name: FINQUEST Technologies
    - Founded: 2024
    - Headquarters: San Francisco, CA
    - Industry: Financial Technology
    - Employees: 150
    
    Products:
    - FINQUEST AI: Document Q&A assistant
    - FINQUEST Analytics: Financial data analysis platform
    - FINQUEST Insights: Market intelligence tool
    
    Recent Achievements:
    - Raised $10M in Series A funding
    - Launched AI-powered document assistant
    - Reached 1,000 active users
    - Expanded to 5 new markets
    
    Future Plans:
    - Launch mobile app in Q2 2024
    - Integrate with 10 new data sources
    - Expand team to 300 employees
    - Open offices in London and Tokyo
    """
    
    test_doc_path.write_text(test_content)
    
    try:
        with open(test_doc_path, 'rb') as f:
            files = {'file': ('test_fallback_doc.txt', f, 'text/plain')}
            response = requests.post(
                f"{BASE_URL}/sessions/{session_id}/upload",
                files=files
            )
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Document uploaded successfully")
            print(f"   - Chunks created: {data.get('chunk_count', 0)}")
            print(f"   - Embedding provider: {data.get('embed_provider', 'unknown')}")
            print(f"   - Used fallback: {data.get('used_fallback', False)}")
            
            # Clean up test file
            test_doc_path.unlink()
            return True
        else:
            print(f"[ERROR] Upload failed: {response.status_code} - {response.text}")
            test_doc_path.unlink()
            return False
    except Exception as e:
        print(f"[ERROR] Exception during upload: {e}")
        if test_doc_path.exists():
            test_doc_path.unlink()
        return False

def test_query_with_fallback(session_id):
    """Test querying with fallback mechanism"""
    print_header(f"Testing Query with Fallback (Session: {session_id})")
    
    questions = [
        "When was FINQUEST Technologies founded?",
        "How many employees does FINQUEST have?",
        "What are the main products offered by FINQUEST?",
        "What are the future plans for FINQUEST?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n[Q] Question {i}: {question}")
        try:
            response = requests.post(
                f"{BASE_URL}/sessions/{session_id}/query",
                json={"session_id": session_id, "question": question, "k": 5}
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "No answer")
                llm_used = data.get("llm_used", "unknown")
                used_fallback = data.get("used_fallback", False)
                sources_count = len(data.get("sources", []))
                
                print(f"[OK] Answer received:")
                print(f"   - LLM Used: {llm_used}")
                print(f"   - Used Fallback: {used_fallback}")
                print(f"   - Sources: {sources_count}")
                print(f"   - Answer: {answer[:200]}...")
                
                if used_fallback:
                    print(f"   *** FALLBACK MECHANISM WORKING!")
            else:
                print(f"[ERROR] Query failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[ERROR] Exception during query: {e}")
        
        time.sleep(1)  # Small delay between queries

def test_cleanup(session_id):
    """Clean up test session"""
    print_header("Cleaning Up Test Data")
    try:
        response = requests.delete(f"{BASE_URL}/sessions/{session_id}")
        if response.status_code == 200:
            print(f"[OK] Test session deleted: {session_id}")
        else:
            print(f"[WARN] Could not delete session: {response.status_code}")
    except Exception as e:
        print(f"[WARN] Cleanup exception: {e}")

def check_local_llm_status():
    """Check if local LLM is installed"""
    print_header("Checking Local LLM Status")
    models_dir = Path(__file__).parent / "app" / "models"
    
    if not models_dir.exists():
        print(f"[ERROR] Models directory not found: {models_dir}")
        print(f"   Local LLM fallback will not be available")
        print(f"   System will use heuristic fallback instead")
        return False
    
    model_files = list(models_dir.glob("*.gguf"))
    if not model_files:
        print(f"[ERROR] No model files found in: {models_dir}")
        print(f"   Local LLM fallback will not be available")
        print(f"   System will use heuristic fallback instead")
        return False
    
    print(f"[OK] Local LLM models found:")
    for model in model_files:
        size_mb = model.stat().st_size / (1024*1024)
        print(f"   - {model.name} ({size_mb:.1f} MB)")
    return True

def main():
    print("\n")
    print("FINQUEST AI - Fallback Mechanism Test")
    print("=" * 60)
    print("This script tests the complete fallback flow:")
    print("1. Invalid API keys -> should use fallback")
    print("2. Document upload with fallback embeddings")
    print("3. Query with fallback LLM generation")
    print("=" * 60)
    
    # Check local LLM status
    has_local_llm = check_local_llm_status()
    if has_local_llm:
        print("\n[OK] Local LLM is available - will test local LLM fallback")
    else:
        print("\n[WARN] Local LLM not available - will test heuristic fallback")
    
    # Test backend health
    if not test_health():
        print("\n[ERROR] Backend is not running. Please start it first.")
        print("   Run: cd backend && python -m app.main")
        return
    
    # Create session with invalid keys
    session_id = test_create_session_with_invalid_keys()
    if not session_id:
        print("\n[ERROR] Could not create test session. Aborting.")
        return
    
    # Upload document (should use fallback embeddings)
    if not test_upload_document(session_id):
        print("\n[ERROR] Document upload failed. Aborting.")
        test_cleanup(session_id)
        return
    
    # Test queries (should use fallback generation)
    test_query_with_fallback(session_id)
    
    # Cleanup
    test_cleanup(session_id)
    
    print_header("Test Complete")
    print("\n[SUCCESS] Fallback mechanism test completed!")
    print("\nSummary:")
    print("- If you saw 'used_fallback: true' in the responses,")
    print("  the fallback mechanism is working correctly!")
    print("- Check the backend logs for detailed fallback information")
    print()

if __name__ == "__main__":
    main()

