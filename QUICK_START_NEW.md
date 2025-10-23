# Quick Start Guide - Multi-Session RAG Document Assistant

Get started with your RAG Document Assistant in 5 minutes!

## 🎯 Prerequisites Check

Before starting, ensure you have:

- ✅ Python 3.8 or higher installed
- ✅ Node.js 18 or higher installed
- ✅ At least 8GB RAM available
- ✅ 10GB free disk space
- ✅ Internet connection (for initial setup and API calls)

Check versions:
```bash
python --version    # Should be 3.8+
node --version      # Should be 18+
npm --version       # Should be 8+
```

## 📦 Installation

### Step 1: Backend Setup (5 minutes)

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
# On Windows:
python -m venv venv
venv\Scripts\activate

# On Linux/Mac:
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; import tinydb; import faiss; print('✅ All dependencies installed!')"
```

### Step 2: Frontend Setup (3 minutes)

Open a **new terminal** (keep backend terminal open):

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Verify installation
npm list --depth=0
```

## 🚀 Running the Application

### Step 3: Start Backend Server

In the backend terminal:

```bash
# Make sure virtual environment is activated
# You should see (venv) in your prompt

# Start the server
python -m app.main
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal running!**

### Step 4: Start Frontend Server

In the frontend terminal:

```bash
# Start Angular development server
npm start
```

You should see:
```
** Angular Live Development Server is listening on localhost:4200 **
✔ Compiled successfully.
```

Your browser should automatically open to `http://localhost:4200`

**Keep this terminal running too!**

## 🎨 First-Time Setup

### Step 5: Configure API Keys

1. Click the **Settings** icon (⚙️) in the top-right corner
2. Enter your API keys:

   **For Gemini (Google AI):**
   - Go to https://makersuite.google.com/app/apikey
   - Click "Create API Key"
   - Copy and paste into "Gemini API Key" field

   **For ChatGPT (OpenAI):**
   - Go to https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Copy and paste into "ChatGPT API Key" field

3. Click **Save Settings**

> **Note**: You only need one API key to get started. Both are recommended for redundancy.

### Step 6: Create Your First Session

1. Click **Back to Dashboard** (or the dashboard icon)
2. Fill in the "Create New Session" form:
   - **Session Name**: e.g., "Test Documents"
   - **Primary LLM**: Choose "Gemini" or "ChatGPT"
3. Click **Create Session**

### Step 7: Upload a Document

1. In your new session, you'll see the upload zone
2. Either:
   - **Drag and drop** a file (PDF, DOCX, TXT, or MD)
   - Click **Upload Document** and select a file
3. Wait for processing (usually 10-30 seconds)

Supported files:
- 📄 PDF files (`.pdf`)
- 📝 Word documents (`.docx`)
- 📃 Text files (`.txt`)
- 📋 Markdown files (`.md`)

### Step 8: Ask Your First Question

1. Type a question in the input field at the bottom
2. Press **Enter** or click **Ask**
3. Wait for the answer (usually 2-5 seconds)

Example questions:
- "Summarize this document in 3 bullet points"
- "What are the key takeaways?"
- "What dates are mentioned in the document?"
- "Who are the main people or organizations mentioned?"

## 🎉 You're All Set!

You now have a fully functional RAG document assistant! Here's what you can do:

### Create Multiple Sessions
- Click the dashboard icon to return home
- Create sessions for different projects or document sets
- Each session has its own documents and conversation history

### Upload Multiple Documents
- Upload as many documents as you need per session
- Large PDFs are automatically chunked for efficient processing
- All documents are searchable together

### View Conversation History
- All your questions and answers are saved
- Source citations show which document each answer came from
- History persists even after closing the browser

### Switch Between Sessions
- Return to the dashboard anytime
- Click any session to open it
- Delete sessions you no longer need

## 🔧 Common Issues & Solutions

### Issue: "Connection refused" error

**Solution**: Make sure the backend server is running
```bash
cd backend
# Activate venv first!
python -m app.main
```

### Issue: "Module not found" error

**Solution**: Reinstall backend dependencies
```bash
cd backend
pip install -r requirements.txt --upgrade
```

### Issue: Frontend won't start

**Solution**: Clear node modules and reinstall
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Issue: "Failed to generate embeddings"

**Solution**: 
1. Check your API key is entered correctly
2. Verify your API key has usage quota remaining
3. Try the other LLM provider
4. System will automatically fall back to local embeddings if APIs fail

### Issue: Slow responses

**Possible causes**:
- Large documents take longer to process initially
- First query loads models (subsequent queries are faster)
- Local LLM fallback is slower than API-based (but works offline!)
- API rate limiting (wait a few seconds and try again)

## 📚 Next Steps

Now that you're up and running:

1. **Read the full README**: `README.md` for advanced features
2. **Check the architecture**: `SYSTEM_ARCHITECTURE.md` for technical details
3. **Try different document types**: Test with PDFs, Word docs, and text files
4. **Experiment with questions**: Try summaries, specific queries, and comparisons
5. **Create multiple sessions**: Organize documents by project or topic

## 🆘 Need Help?

- **Issues**: Check [GitHub Issues](https://github.com/yourusername/ntt/issues)
- **Documentation**: See `SYSTEM_ARCHITECTURE.md`
- **Logs**: Check terminal output for error messages

## 💡 Tips for Best Results

1. **Document Quality**: Clear, well-formatted documents work best
2. **Question Clarity**: Be specific in your questions
3. **Source Citations**: Click on [Source N] tags to see original text
4. **Session Organization**: Create separate sessions for different topics
5. **API Keys**: Use both Gemini and ChatGPT for redundancy

## 🚀 Advanced Features

Once you're comfortable with the basics:

- **Out-of-Context Detection**: System intelligently detects when questions can't be answered
- **Automatic Fallback**: If APIs fail, local LLM kicks in automatically
- **Smart Chunking**: Large documents split intelligently for better answers
- **Source Citations**: Every answer includes references to source documents
- **Persistent Storage**: Everything saved to `~/.rag-assistant/`

---

**Ready to explore? Start uploading documents and asking questions!** 🎯

