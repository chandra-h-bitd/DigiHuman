#!/bin/bash

echo "🚀 Starting Document Q&A System with Docker (Simple Setup)"
echo "=========================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found! Please install Docker from https://docker.com"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found! Please install Docker Compose"
    exit 1
fi

# Create necessary directories
echo "📁 Creating storage directories..."
mkdir -p production_storage/documents
mkdir -p production_storage/embeddings
mkdir -p production_storage/sessions
mkdir -p production_storage/qdrant_db

# Set proper permissions
chmod 755 production_storage
chmod 755 production_storage/*

echo "🐳 Building and starting Docker containers..."
echo "This may take a few minutes on first run..."

# Build and start services (backend + databases only)
docker-compose -f docker-compose.simple.yml up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 15

# Check service health
echo "🔍 Checking service health..."

# Check backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️ Backend health check failed"
fi

# Check Qdrant
if curl -f http://localhost:6333/collections > /dev/null 2>&1; then
    echo "✅ Qdrant is healthy"
else
    echo "⚠️ Qdrant health check failed"
fi

# Check Redis
if docker-compose -f docker-compose.simple.yml exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is healthy"
else
    echo "⚠️ Redis health check failed"
fi

# Check PostgreSQL
if docker-compose -f docker-compose.simple.yml exec postgres pg_isready -U docqa_user > /dev/null 2>&1; then
    echo "✅ PostgreSQL is healthy"
else
    echo "⚠️ PostgreSQL health check failed"
fi

echo ""
echo "🎉 Document Q&A System is now running!"
echo ""
echo "📱 Access your application:"
echo "   Backend API: http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"
echo ""
echo "🔧 Service URLs:"
echo "   Qdrant: http://localhost:6333"
echo "   Redis: localhost:6379"
echo "   PostgreSQL: localhost:5432"
echo ""
echo "📊 View logs:"
echo "   docker-compose -f docker-compose.simple.yml logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose -f docker-compose.simple.yml down"
echo ""
echo "🔄 Restart services:"
echo "   docker-compose -f docker-compose.simple.yml restart"
echo ""
echo "🗑️ Clean up (removes all data):"
echo "   docker-compose -f docker-compose.simple.yml down -v"
echo ""
echo "💡 Note: Frontend is not included in this simple setup."
echo "   You can run the frontend manually: cd frontend && npm start"
echo ""
