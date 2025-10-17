#!/bin/bash

echo "🚀 Starting Document Q&A Frontend..."
echo

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found! Please install Node.js from https://nodejs.org"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found! Please install Node.js (includes npm) from https://nodejs.org"
    exit 1
fi

# Install dependencies
echo "📥 Installing dependencies..."
npm install

# Start the application
echo "🚀 Starting frontend development server..."
echo
echo "✅ Frontend will be available at: http://localhost:4200"
echo
echo "Press Ctrl+C to stop the server"
echo

npm start
