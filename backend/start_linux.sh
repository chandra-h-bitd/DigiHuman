#!/bin/bash

echo "🚀 Starting Document Q&A Backend..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found! Please install Python 3.9+"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
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
