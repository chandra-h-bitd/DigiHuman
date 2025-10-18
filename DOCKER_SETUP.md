# 🐳 Docker Setup Guide

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- 10GB free disk space

### One-Command Start
```bash
./docker-start.sh
```

### Manual Start
```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🏗️ Architecture

### Services
- **Frontend**: Angular app (port 4200)
- **Backend**: FastAPI with persistent storage (port 8000)
- **Qdrant**: Vector database (port 6333)
- **Redis**: Caching layer (port 6379)
- **PostgreSQL**: Persistent database (port 5432)
- **Nginx**: Reverse proxy (port 80)

### Storage
- **Persistent Volumes**: All data survives container restarts
- **Production Storage**: Organized file structure
- **Backup Ready**: Easy to backup volumes

## 🔧 Configuration

### Environment Variables
```bash
# Backend
REDIS_URL=redis://redis:6379
QDRANT_URL=http://qdrant:6333
DATABASE_URL=postgresql://docqa_user:docqa_password@postgres:5432/docqa

# Database
POSTGRES_DB=docqa
POSTGRES_USER=docqa_user
POSTGRES_PASSWORD=docqa_password
```

### Storage Directories
```
production_storage/
├── documents/     # Uploaded files
├── embeddings/    # Cached embeddings
├── sessions/      # Session data
└── qdrant_db/     # Vector database
```

## 📊 Monitoring

### Health Checks
- Backend: `http://localhost:8000/health`
- Frontend: `http://localhost:4200`
- Qdrant: `http://localhost:6333/collections`
- Redis: `docker-compose exec redis redis-cli ping`
- PostgreSQL: `docker-compose exec postgres pg_isready`

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f qdrant
```

## 🚀 Production Deployment

### Security
- Non-root containers
- Network isolation
- Rate limiting via Nginx
- Environment-based secrets

### Scaling
```bash
# Scale backend instances
docker-compose up --scale backend=3 -d

# Scale with load balancer
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Backup
```bash
# Backup volumes
docker run --rm -v docqa_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
docker run --rm -v docqa_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup.tar.gz -C /data .
docker run --rm -v docqa_qdrant_data:/data -v $(pwd):/backup alpine tar czf /backup/qdrant_backup.tar.gz -C /data .
```

## 🔄 Development

### Hot Reload
```bash
# Development mode with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Debugging
```bash
# Access container shell
docker-compose exec backend bash
docker-compose exec frontend sh

# View container resources
docker stats
```

## 🛠️ Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Check what's using the port
lsof -i :8000
# Kill the process or change port in docker-compose.yml
```

**Out of Memory**
```bash
# Increase Docker memory limit
# Docker Desktop: Settings > Resources > Memory
```

**Permission Issues**
```bash
# Fix storage permissions
sudo chown -R $USER:$USER production_storage/
chmod -R 755 production_storage/
```

**Database Connection Issues**
```bash
# Reset database
docker-compose down -v
docker-compose up -d
```

### Reset Everything
```bash
# Complete reset (removes all data)
docker-compose down -v
docker system prune -a
./docker-start.sh
```

## 📈 Performance

### Resource Requirements
- **Minimum**: 2 CPU cores, 4GB RAM
- **Recommended**: 4 CPU cores, 8GB RAM
- **Production**: 8+ CPU cores, 16GB+ RAM

### Optimization
- Enable Docker BuildKit for faster builds
- Use multi-stage builds (already implemented)
- Configure resource limits in production
- Use Docker secrets for sensitive data

## 🔐 Security

### Production Checklist
- [ ] Change default passwords
- [ ] Use Docker secrets
- [ ] Enable HTTPS
- [ ] Configure firewall
- [ ] Regular security updates
- [ ] Monitor logs
- [ ] Backup strategy

### Network Security
- Services communicate via internal network
- Only necessary ports exposed
- Nginx handles SSL termination
- Rate limiting enabled
