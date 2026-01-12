# Why k=5? Is It Optimized?

## Current State

**Before Fix:**
- `k=5` was **hardcoded** in `QueryRequest` model
- Not using `config.json` values (`default_k: 5`, `max_k: 20`)
- No validation or optimization

**After Fix:**
- `k` now uses `DEFAULT_K` from `config.json` (currently 5)
- Validated to be between 1 and `MAX_K` (20)
- Configurable via `config.json`

## Why k=5?

### Industry Standards:
- **Common RAG practice**: 3-7 chunks is typical
- **LLM context limits**: Most models have ~4K-8K token context windows
- **Quality vs Speed tradeoff**: 
  - Too few chunks (k=1-2): May miss relevant context
  - Too many chunks (k=10+): More noise, slower, more expensive

### Token Math:
- Average chunk size: ~700 tokens (from config)
- k=5 chunks × 700 tokens = ~3,500 tokens
- Plus question + system prompt = ~4,000 tokens total
- Fits comfortably in most LLM context windows (4K-8K)

### Your System's Design:
- **Hybrid search**: Retrieves `k * 2` chunks initially (10 chunks)
- **Combines**: Vector (70%) + BM25 (30%) scores
- **Filters down**: To top `k` chunks (5 chunks)
- **Sends to LLM**: Only the most relevant 5 chunks

## Is k=5 Optimal?

### ✅ Good for:
- **Most questions**: Provides enough context without overwhelming
- **Cost efficiency**: Fewer tokens = lower API costs
- **Speed**: Faster processing with fewer chunks
- **Quality**: Top 5 chunks usually contain the answer

### ⚠️ May need adjustment for:
- **Complex questions**: Might need k=7-10 for multi-part answers
- **Large documents**: With many topics, might need more chunks
- **Specific queries**: Very targeted questions might work with k=3

## How to Optimize:

### Option 1: Adjust in `config.json`
```json
{
  "retrieval": {
    "default_k": 7,  // Increase for more context
    "max_k": 20       // Maximum allowed
  }
}
```

### Option 2: Make it dynamic (future enhancement)
- Simple questions → k=3
- Complex questions → k=7
- Based on question length/complexity

### Option 3: User-configurable
- Add UI slider: "Retrieval depth: 3-10 chunks"
- Let users choose based on their needs

## Current Optimization:

✅ **Now optimized** because:
1. Uses config value (not hardcoded)
2. Validated (can't exceed MAX_K)
3. Configurable (change in config.json)
4. Follows industry best practices (5 is common)

## Recommendation:

**Keep k=5 as default** - it's a good balance, but make it configurable (which we just did!).

For most use cases, k=5 works well. If you find:
- Answers missing context → Increase to k=7-10
- Answers too verbose/noisy → Decrease to k=3-4
- Cost concerns → Decrease k
- Quality concerns → Increase k
