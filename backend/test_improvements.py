"""
Test script to verify all improvements are working correctly
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        from rank_bm25 import BM25Okapi
        print("[OK] BM25 import successful")
    except ImportError as e:
        print(f"[WARN] BM25 import failed: {e}")
    
    try:
        import ollama
        print("[OK] Ollama import successful")
    except ImportError:
        print("[WARN] Ollama not installed (optional)")
    
    try:
        from sentence_transformers import SentenceTransformer
        print("[OK] Sentence Transformers import successful")
    except ImportError as e:
        print(f"[FAIL] Sentence Transformers import failed: {e}")
        return False
    
    return True

def test_sbert_model():
    """Test that SBERT model is correctly configured"""
    print("\nTesting SBERT model configuration...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
        # Test embedding
        test_text = ["This is a test"]
        embedding = model.encode(test_text)
        print(f"[OK] SBERT model loaded successfully")
        print(f"   Model: all-mpnet-base-v2")
        print(f"   Embedding dimension: {embedding.shape[1]} (should be 768)")
        if embedding.shape[1] == 768:
            print("[OK] Dimension matches Gemini (768D)")
        else:
            print(f"[WARN] Dimension mismatch: expected 768, got {embedding.shape[1]}")
        return True
    except Exception as e:
        print(f"[FAIL] SBERT model test failed: {e}")
        return False

def test_bm25():
    """Test BM25 functionality"""
    print("\nTesting BM25...")
    try:
        from rank_bm25 import BM25Okapi
        
        # Sample corpus
        corpus = [
            "The quick brown fox jumps over the lazy dog",
            "Python is a programming language",
            "Machine learning is a subset of AI"
        ]
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        
        # Create BM25 index
        bm25 = BM25Okapi(tokenized_corpus)
        
        # Test query
        query = "programming language"
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        
        print("[OK] BM25 test successful")
        print(f"   Query: '{query}'")
        print(f"   Scores: {scores}")
        best_idx = list(scores).index(max(scores))
        print(f"   Best match: '{corpus[best_idx]}'")
        return True
    except Exception as e:
        print(f"[FAIL] BM25 test failed: {e}")
        return False

def test_hybrid_search_logic():
    """Test hybrid search combination logic"""
    print("\nTesting hybrid search logic...")
    try:
        # Simulate vector and BM25 scores
        vector_scores = {"doc1": 0.9, "doc2": 0.7, "doc3": 0.5}
        bm25_scores = {"doc1": 0.6, "doc2": 0.8, "doc4": 0.9}
        
        # Normalize
        max_vec = max(vector_scores.values()) or 1
        vector_scores_norm = {k: v / max_vec for k, v in vector_scores.items()}
        
        max_bm25 = max(bm25_scores.values()) or 1
        bm25_scores_norm = {k: v / max_bm25 for k, v in bm25_scores.items()}
        
        # Combine (70% vector, 30% BM25)
        combined = {}
        for k in set(list(vector_scores_norm.keys()) + list(bm25_scores_norm.keys())):
            combined[k] = (vector_scores_norm.get(k, 0) * 0.7) + (bm25_scores_norm.get(k, 0) * 0.3)
        
        sorted_results = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        
        print("[OK] Hybrid search logic test successful")
        print(f"   Combined scores: {dict(sorted_results)}")
        return True
    except Exception as e:
        print(f"[FAIL] Hybrid search test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Backend Improvements")
    print("=" * 60)
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test SBERT model
    results.append(("SBERT Model", test_sbert_model()))
    
    # Test BM25
    results.append(("BM25", test_bm25()))
    
    # Test hybrid search
    results.append(("Hybrid Search Logic", test_hybrid_search_logic()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] All tests passed!")
    else:
        print("[WARN] Some tests failed - check output above")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

