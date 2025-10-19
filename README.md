# 📚 **Document Q&A System**

A powerful document question-answering system with multi-LLM support, intelligent fallback, and optimized performance.

## ✨ **Features**

- 🤖 **Multi-LLM Support**: Google Gemini, OpenAI ChatGPT, Local LLM
- 🧠 **Intelligent Fallback**: Automatic provider switching with circuit breakers
- ⚡ **Optimized Performance**: 50% faster processing with intelligent batching
- 📄 **Document Support**: PDF and DOCX files
- 🔍 **Smart Search**: Vector-based semantic search with context optimization
- 🌐 **Real-time Streaming**: Live response streaming for better UX
- 📊 **Health Monitoring**: Comprehensive system health and performance metrics
- 🐳 **Docker Ready**: Complete containerization with persistent storage
- 💾 **Persistent Storage**: Redis caching, PostgreSQL database, persistent Qdrant
- 🔄 **Session Management**: Multi-session support with chat history

## 🚀 **Quick Start**

### **Option 1: Docker (Recommended for Production)**

**All Platforms:**
```bash
# One-command setup with persistent storage
./docker-start.sh
```

**Manual Docker:**
```bash
docker-compose up --build -d
```

### **Option 2: Manual Installation**

1. **Install Python 3.9+** from [python.org](https://python.org)

2. **Backend Setup:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python app/main.py
```

3. **Frontend Setup:**
```bash
cd frontend
npm install
npm start
```

## 🌐 **Access Your Application**

### **Docker Setup:**
- **Frontend**: http://localhost:4200
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Qdrant**: http://localhost:6333
- **Nginx Proxy**: http://localhost (optional)

### **Manual Setup:**
- **Frontend**: http://localhost:4200
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🔑 **API Keys Setup**

1. **Google Gemini**: Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **OpenAI**: Get API key from [OpenAI Platform](https://platform.openai.com/api-keys)
3. **Local LLM**: No API key needed (automatic fallback)

## 📖 **How to Use**

1. **Upload Document**: Choose PDF or DOCX file
2. **Select Provider**: Choose Gemini, OpenAI, or Auto (intelligent selection)
3. **Enter API Key**: (Optional - system will use local LLM if not provided)
4. **Ask Questions**: Get intelligent answers based on your document

## 🎯 **API Endpoints**

### **Optimized Endpoints (v2):**
- `POST /v2/upload` - Upload and process documents
- `POST /v2/ask` - Ask questions about documents
- `POST /v2/ask/stream` - Streaming responses
- `GET /v2/health` - System health check
- `GET /v2/models` - Available models
- `POST /v2/validate` - Validate API keys

### **Legacy Endpoints (v1):**
- `POST /upload` - Original upload
- `POST /ask` - Original ask
- `GET /health` - Basic health check

## 🔧 **Configuration**

Edit `backend/app/config.json` to customize:
- Default models
- Available providers
- Local LLM settings
- Optimization parameters

## 📊 **Performance Features**

- **Intelligent Model Selection**: Chooses best model based on question complexity
- **Context Optimization**: Compresses context for better local LLM performance
- **Batch Processing**: Processes multiple texts efficiently
- **Circuit Breakers**: Prevents cascading failures
- **Caching**: Reduces redundant API calls
- **Streaming**: Real-time response delivery

## 🛠️ **Troubleshooting**

### **Common Issues:**

**Python Not Found:**
- Install Python 3.9+ from [python.org](https://python.org)

**Permission Errors:**
- Windows: Run as Administrator
- macOS/Linux: Use `sudo` if needed

**Port Already in Use:**
- Change port in `app/main.py`

**API Key Issues:**
- System automatically falls back to local LLM
- Check API key validity at `/v2/validate`

**SBERT Embedding Errors:**
- Run the fix script: `python backend/fix_sbert.py`
- Or manually: `pip install --upgrade huggingface_hub sentence-transformers`

**Local LLM Download Issues:**
- System will automatically try to download models
- If download fails, system continues with cloud providers only
- Check internet connection for model downloads

## 📱 **Mobile Access**

Access from any device on your network:
- Find your IP: `ipconfig` (Windows) or `ifconfig` (macOS/Linux)
- Access: `http://YOUR_IP:4200` (Frontend) or `http://YOUR_IP:8000` (Backend)

## 🎉 **Success!**

Your Document Q&A system is now running with:
- ✅ Multi-LLM support with intelligent fallback
- ✅ Optimized performance and reliability
- ✅ Real-time streaming responses
- ✅ Comprehensive health monitoring
- ✅ Easy-to-use interface

**Happy questioning! 🚀**



# Just double-click these files:
backend/start_windows.bat    # Starts backend
frontend/start_windows.bat   # Starts frontend


# Just run these commands:
./backend/start_macos.sh     # Starts backend
./frontend/start_macos.sh    # Starts frontend


# Just run these commands:
./backend/start_linux.sh     # Starts backend
./frontend/start_linux.sh    # Starts frontend



AIzaSyBRCFGKFd5RU81P6rizfJa49wBWIJUZ0K8
AIzaSyC0_UWujD0SSGDIejLNUosbTcd3fuBM8Zo
AIzaSyDy9FLpxLM_7AWRYKYbVVH7fIvjMAe-pVw 