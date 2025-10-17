#!/bin/bash

echo "🚀 Starting Document Q&A Backend..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found! Please install Python 3.9+ from https://python.org"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt
echo "🔧 Updating huggingface-hub for compatibility..."
pip install --upgrade huggingface-hub

# Install local LLM models (optional but recommended)
echo "🤖 Installing local LLM models for fallback..."
echo "💡 This will download ~4-8GB of models for offline use"
echo "❓ Install local LLM models? (y/N): "
read -r install_llm
if [[ $install_llm =~ ^[Yy]$ ]]; then
    python install_local_llm.py
else
    echo "⏭️ Skipping local LLM installation"
    echo "💡 You can run 'python install_local_llm.py' later to install them"
fi

# Start the application
echo "🚀 Starting backend server..."
echo
echo "✅ Backend will be available at: http://localhost:8000"
echo "✅ Health check: http://localhost:8000/health"
echo "✅ API docs: http://localhost:8000/docs"
echo
echo "Press Ctrl+C to stop the server"
echo

python -m app.main
