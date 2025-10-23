# FINQUEST AI - Groq Fallback Setup Guide

## 🚀 What is Groq?

**Groq** is a FREE, FAST LLM API that provides:
- ⚡ **Lightning Fast** - Faster than Gemini (seriously!)
- 🆓 **Free Tier** - 7,000 requests/day FREE
- 🧠 **High Quality** - Uses Llama 3 70B (excellent answers)
- 💰 **Paid Tier** - $0.70 per million tokens (very cheap)

## ✨ Why Use Groq as Fallback?

When your Gemini API fails or you don't have a key:
1. System tries **Groq** first (fast, intelligent answers)
2. If Groq fails → Uses **heuristic** (basic extraction)

**Result**: You ALWAYS get good answers, even without your primary API key!

---

## 🎯 How to Get FREE Groq API Key

### Step 1: Create Account
1. Go to: https://console.groq.com
2. Click **"Sign Up"** (free!)
3. Sign up with Google or Email

### Step 2: Generate API Key
1. After login, go to **"API Keys"**
2. Click **"Create API Key"**
3. Give it a name: "FINQUEST AI Fallback"
4. Click **"Create"**
5. **COPY THE KEY** (you only see it once!)

### Step 3: Add to FINQUEST AI

#### Option 1: Via Frontend (Easy)
1. Open http://localhost:4200
2. Go to **Settings** tab
3. Find **"Groq API Key"** field
4. Paste your key
5. Click **Save**

#### Option 2: Via Python/API
```python
import requests

requests.post('http://localhost:8000/config', json={
    'key_name': 'groq_api_key',
    'key_value': 'gsk_YOUR_KEY_HERE'  # Your Groq API key
})
```

---

## 📊 Fallback Flow with Groq

### Without ANY API Keys
```
User asks question
  ↓
Gemini? → No key → Skip
  ↓
ChatGPT? → No key → Skip
  ↓
Groq? → No key → Skip
  ↓
Heuristic → ✅ Basic answer (fast but simple)
```

### With ONLY Groq API Key (Free!)
```
User asks question
  ↓
Gemini? → No key → Skip
  ↓
ChatGPT? → No key → Skip
  ↓
Groq? → ✅ HIGH QUALITY ANSWER! (fast, intelligent)
```

### With Gemini + Groq (Recommended!)
```
User asks question
  ↓
Gemini? → ✅ Works! (best quality)
```

**BUT if Gemini fails:**
```
Gemini → Error/Timeout
  ↓
Groq → ✅ AUTOMATIC FALLBACK! (fast, still great quality)
```

---

## 🎯 Recommended Setup

### Best Practice: Set Both Keys

1. **Primary**: Gemini API key (best quality, your main choice)
2. **Fallback**: Groq API key (free safety net)

**Why?**
- Gemini for normal operation (excellent)
- Groq kicks in if Gemini fails (excellent fallback)
- Never see errors or poor answers!

---

## 💰 Cost Comparison

| Provider | Free Tier | Speed | Quality | When to Use |
|----------|-----------|-------|---------|-------------|
| **Gemini** | Limited | Fast | ⭐⭐⭐⭐⭐ | Primary |
| **Groq** | 7k req/day | **VERY Fast** | ⭐⭐⭐⭐ | Fallback |
| **ChatGPT** | No free | Fast | ⭐⭐⭐⭐⭐ | Optional |
| **Heuristic** | Unlimited | Instant | ⭐⭐ | Last resort |

---

## 🔧 Testing Your Setup

### Test 1: Check if Groq Key is Set
```python
import requests
response = requests.get('http://localhost:8000/config')
config = response.json()
print("Groq API Key:", "SET" if config.get('groq_api_key') else "NOT SET")
```

### Test 2: Test Without Primary Keys
1. Clear your Gemini and ChatGPT keys (temporarily)
2. Ask a question in FINQUEST AI
3. Check the response:
   - If Groq is set: `"llm_used": "groq-fallback"`
   - If not: `"llm_used": "heuristic"`

### Test 3: Full Fallback Test
```bash
cd backend
python test_complete_fallback.py
```

Look for:
- `"llm_used": "groq-fallback"` ✅ Good!
- `"llm_model": "llama3-70b-8192"` ✅ Perfect!

---

## 📈 Benefits Summary

### ✅ With Groq Fallback
- Fast responses (even without Gemini)
- Intelligent answers (actual LLM)
- Free for basic usage
- Reliable backup

### ❌ Without Groq Fallback
- Slow or no response if Gemini fails
- Only basic text extraction (heuristic)
- No intelligent answers in fallback mode

---

## 🎓 Example Response

### With Groq Fallback Active
```json
{
  "answer": "FINQUEST AI was founded in 2024. It's a financial technology company specializing in AI-powered document analysis. [Source 1]",
  "llm_used": "groq-fallback",
  "llm_model": "llama3-70b-8192",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "used_fallback": true
}
```

**Answer Quality**: ⭐⭐⭐⭐ Excellent
**Speed**: ⚡⚡⚡ Very Fast (1-2 seconds)

### Without Groq (Heuristic Only)
```json
{
  "answer": "FINQUEST AI Company Profile Company Overview: FINQUEST AI is a cutting-edge...",
  "llm_used": "heuristic",
  "llm_model": "rule-based-extraction",
  "used_fallback": true
}
```

**Answer Quality**: ⭐⭐ Basic (just raw text)
**Speed**: ⚡⚡⚡⚡ Instant

---

## 🚀 Get Started Now!

1. **Get free Groq key**: https://console.groq.com
2. **Add to settings**: http://localhost:4200 → Settings
3. **Test it**: Ask a question without Gemini key
4. **Enjoy**: Fast, intelligent fallback!

---

## 📞 Need Help?

- **Groq Documentation**: https://console.groq.com/docs
- **Free Tier Limits**: 7,000 requests/day, 500 req/minute
- **Supported Models**: Llama 3 70B, Llama 3 8B, Mixtral 8x7B

---

**Your FINQUEST AI now has INTELLIGENT fallback with actual LLM!** 🎉

No more poor quality fallback responses - you get great answers even when your primary API fails!

