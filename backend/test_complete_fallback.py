"""
Complete Fallback Flow Test - No API Keys Required
Tests the full flow: SBERT embeddings + Local LLM generation
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("\n" + "="*70)
print("FINQUEST AI - Complete Fallback Flow Test")
print("Testing system WITHOUT valid API keys (pure offline mode)")
print("="*70)

# Test 1: Ensure backend is running
print("\n1. Checking backend...")
try:
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("   [OK] Backend is running")
    else:
        print("   [ERROR] Backend not responding")
        exit(1)
except Exception as e:
    print(f"   [ERROR] Cannot connect: {e}")
    exit(1)

# Test 2: Clear API keys to force fallback
print("\n2. Clearing API keys (forcing fallback mode)...")
try:
    requests.post(f"{BASE_URL}/config", json={"key_name": "gemini_api_key", "key_value": ""})
    requests.post(f"{BASE_URL}/config", json={"key_name": "chatgpt_api_key", "key_value": ""})
    print("   [OK] API keys cleared - system will use fallback")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 3: Create a session
print("\n3. Creating test session...")
try:
    response = requests.post(
        f"{BASE_URL}/sessions",
        json={"session_name": "Fallback Flow Test", "primary_llm": "gemini"}
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

# Test 4: Upload a document
print("\n4. Uploading document (should use SBERT embeddings)...")
test_document = """
FINQUEST AI Company Profile

Company Overview:
FINQUEST AI is a cutting-edge financial technology company founded in 2024.
The company specializes in AI-powered document analysis and question-answering systems.

Headquarters: San Francisco, California
Industry: Financial Technology (FinTech)
Founded: 2024
Employees: 150 professionals

Products and Services:
1. FINQUEST AI Document Assistant - Intelligent Q&A system for documents
2. FINQUEST Analytics - Advanced financial data analysis platform
3. FINQUEST Insights - Market intelligence and reporting tools

Key Features:
- Multi-session document management
- Support for PDF, DOCX, TXT, and Markdown files
- Powered by RAG (Retrieval-Augmented Generation) technology
- Local LLM fallback for offline operation
- Enterprise-grade security and privacy

Recent Achievements:
- Successfully raised $10 million in Series A funding
- Launched AI document assistant with 1,000+ active users
- Expanded operations to 5 international markets
- Awarded "Best FinTech Innovation 2024" by TechCrunch

Technology Stack:
- Backend: Python, FastAPI, FAISS vector search
- Frontend: Angular, TypeScript
- AI Models: Gemini, GPT-4, Local LLMs (GPT4All)
- Database: TinyDB for session persistence

Future Plans:
- Launch mobile applications for iOS and Android (Q2 2024)
- Integrate with 10+ major financial data providers
- Expand team to 300+ employees by end of 2024
- Open new offices in London and Tokyo
- Develop industry-specific AI solutions

Contact Information:
Email: contact@finquestai.com
Website: www.finquestai.com
Phone: +1 (555) 123-4567
"""

try:
    files = {'file': ('finquest_profile.txt', test_document.encode(), 'text/plain')}
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/upload",
        files=files
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Document uploaded")
        print(f"   - Chunks: {data.get('chunks_indexed', 0)}")
        print(f"   - Embedding Provider: {data.get('embed_provider', 'N/A')}")
        print(f"   - Embedding Model: {data.get('embedding_model', 'N/A')}")
        print(f"   - Used Fallback: {data.get('used_fallback', False)}")
        
        if data.get('embed_provider') == 'sbert' and data.get('used_fallback'):
            print("   >>> SBERT FALLBACK WORKING! <<<")
        else:
            print("   [WARN] Expected SBERT fallback but got:", data.get('embed_provider'))
    else:
        print(f"   [ERROR] Upload failed: {response.status_code}")
        print(f"   {response.text[:200]}")
        exit(1)
except Exception as e:
    print(f"   [ERROR] {e}")
    exit(1)

# Test 5: Ask questions (should use Local LLM)
print("\n5. Testing queries with Local LLM fallback...")

questions = [
    "When was FINQUEST AI founded?",
    "Where is the company headquarters?",
    "How many employees does FINQUEST have?",
    "What are the main products offered?",
    "What are the future expansion plans?"
]

successful_queries = 0
local_llm_used = 0

for i, question in enumerate(questions, 1):
    print(f"\n   Question {i}: {question}")
    try:
        response = requests.post(
            f"{BASE_URL}/sessions/{session_id}/query",
            json={"session_id": session_id, "question": question, "k": 5}
        )
        
        if response.status_code == 200:
            data = response.json()
            llm_used = data.get('llm_used', 'unknown')
            llm_model = data.get('llm_model', 'unknown')
            embedding_model = data.get('embedding_model', 'unknown')
            used_fallback = data.get('used_fallback', False)
            answer = data.get('answer', '')
            sources_count = len(data.get('sources', []))
            
            print(f"   - LLM Used: {llm_used}")
            print(f"   - LLM Model: {llm_model}")
            print(f"   - Embedding Model: {embedding_model}")
            print(f"   - Sources Found: {sources_count}")
            print(f"   - Used Fallback: {used_fallback}")
            print(f"   - Answer: {answer[:100]}...")
            
            if llm_used == 'local-llm' or llm_used == 'heuristic':
                print(f"   >>> FALLBACK LLM WORKING! <<<")
                local_llm_used += 1
            elif llm_used == 'out-of-context':
                print(f"   [WARN] Got 'out-of-context' - fallback not triggered")
            else:
                print(f"   [WARN] Unexpected LLM: {llm_used}")
            
            successful_queries += 1
        else:
            print(f"   [ERROR] Query failed: {response.status_code}")
        
        time.sleep(1)  # Small delay between queries
        
    except Exception as e:
        print(f"   [ERROR] {e}")

# Test 6: Summary
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)
print(f"\nTotal Questions: {len(questions)}")
print(f"Successful Queries: {successful_queries}")
print(f"Local LLM Used: {local_llm_used}")
print()

if local_llm_used > 0:
    print("[SUCCESS] COMPLETE FALLBACK FLOW IS WORKING!")
    print("  - SBERT embeddings: OK")
    print("  - Local LLM generation: OK")
    print("  - System works WITHOUT API keys!")
    print()
    print("The system is ready for:")
    print("  - Offline operation")
    print("  - Privacy-sensitive environments")
    print("  - API key fallback scenarios")
elif successful_queries > 0:
    print("[PARTIAL] Queries succeeded but check which LLM was used")
    print("Expected: local-llm or heuristic")
    print("If you see 'out-of-context', the fallback logic needs adjustment")
else:
    print("[FAILED] Fallback flow not working properly")
    print("Check backend logs for errors")

# Test 7: Cleanup
print("\n6. Cleaning up...")
try:
    requests.delete(f"{BASE_URL}/sessions/{session_id}")
    print("   [OK] Test session deleted")
except:
    pass

print("\n" + "="*70)
print()

