# Deployment Guide

This guide covers various deployment options for the Multi-Session RAG Document Assistant.

## 📦 Deployment Options

### 1. Local Development (Already Configured)

**Best for**: Development and testing

**Setup**: Already working! Just run:
```bash
# Terminal 1 - Backend
cd backend
python -m app.main

# Terminal 2 - Frontend  
cd frontend
npm start
```

### 2. Production Build (Local Server)

**Best for**: Running on a local network or personal server

#### Backend

```bash
cd backend

# Install production dependencies
pip install -r requirements.txt

# Run with production settings
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Frontend

```bash
cd frontend

# Build for production
npm run build

# Serve with a static server
npx serve -s dist/docqa-spa -l 4200
```

Or configure nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /path/to/frontend/dist/docqa-spa;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 3. Docker Deployment

**Best for**: Containerized deployment and easy distribution

Create `Dockerfile` in project root:

```dockerfile
# Backend stage
FROM python:3.10-slim as backend
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

# Frontend stage
FROM node:18-alpine as frontend
WORKDIR /app/frontend
COPY frontend/package*.json .
RUN npm ci
COPY frontend/ .
RUN npm run build

# Production stage
FROM python:3.10-slim
WORKDIR /app

# Install nginx for serving frontend
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

# Copy backend
COPY --from=backend /app/backend /app/backend

# Copy frontend build
COPY --from=frontend /app/frontend/dist/docqa-spa /var/www/html

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Expose ports
EXPOSE 80 8000

# Start script
COPY start.sh /app/
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  rag-assistant:
    build: .
    ports:
      - "80:80"
      - "8000:8000"
    volumes:
      - rag-data:/root/.rag-assistant
    environment:
      - STORAGE_PATH=/root/.rag-assistant
    restart: unless-stopped

volumes:
  rag-data:
```

Deploy:

```bash
docker-compose up -d
```

### 4. Desktop Application (Electron)

**Best for**: Standalone desktop app for Windows/Mac/Linux

#### Setup Electron Wrapper

```bash
npm install -g @electron-forge/cli
cd desktop-app
npx create-electron-app rag-assistant
cd rag-assistant
```

Create `src/index.js`:

```javascript
const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;

function startBackend() {
  const pythonPath = path.join(__dirname, '../backend/venv/Scripts/python.exe');
  const mainPath = path.join(__dirname, '../backend/app/main.py');
  
  backendProcess = spawn(pythonPath, ['-m', 'uvicorn', 'app.main:app', '--port', '8000']);
  
  backendProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    icon: path.join(__dirname, 'assets/icon.png')
  });

  // Wait for backend to start
  setTimeout(() => {
    mainWindow.loadURL('http://localhost:4200');
  }, 3000);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('ready', () => {
  startBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
```

Build executables:

```bash
npm run make
```

### 5. Cloud Deployment

#### AWS EC2

```bash
# SSH into EC2 instance
ssh -i key.pem ubuntu@your-ec2-ip

# Install dependencies
sudo apt update
sudo apt install python3-pip nodejs npm nginx

# Clone repository
git clone <your-repo>
cd ntt

# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup frontend
cd ../frontend
npm install
npm run build

# Configure nginx
sudo nano /etc/nginx/sites-available/rag-assistant
# (copy nginx config from above)

sudo ln -s /etc/nginx/sites-available/rag-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Setup systemd service
sudo nano /etc/systemd/system/rag-backend.service
```

`/etc/systemd/system/rag-backend.service`:

```ini
[Unit]
Description=RAG Document Assistant Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ntt/backend
Environment="PATH=/home/ubuntu/ntt/backend/venv/bin"
ExecStart=/home/ubuntu/ntt/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:

```bash
sudo systemctl enable rag-backend
sudo systemctl start rag-backend
```

#### Google Cloud Platform (Cloud Run)

```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/rag-assistant

# Deploy
gcloud run deploy rag-assistant \
  --image gcr.io/PROJECT_ID/rag-assistant \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi
```

#### Azure Web App

```bash
# Create resource group
az group create --name rag-assistant-rg --location eastus

# Create app service plan
az appservice plan create \
  --name rag-assistant-plan \
  --resource-group rag-assistant-rg \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --resource-group rag-assistant-rg \
  --plan rag-assistant-plan \
  --name rag-assistant-app \
  --runtime "PYTHON:3.10"

# Deploy
az webapp up --name rag-assistant-app
```

## 🔒 Production Security Checklist

- [ ] Enable HTTPS/SSL certificates
- [ ] Configure CORS properly
- [ ] Set up authentication (if multi-user)
- [ ] Implement rate limiting
- [ ] Configure firewall rules
- [ ] Regular security updates
- [ ] Backup strategy for data
- [ ] Monitor logs and errors
- [ ] Set up alerts

## 📊 Performance Optimization

### Backend

```python
# app/main.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,  # Multiple workers
        loop="uvloop",  # Fast event loop
        http="httptools"  # Fast HTTP parser
    )
```

### Frontend

```bash
# Build with optimization
ng build --configuration production --optimization=true --aot=true
```

### Database

```python
# Use connection pooling for TinyDB
# Consider upgrading to PostgreSQL for large deployments
```

## 📈 Monitoring

### Logging

```python
# backend/app/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/rag-assistant.log'),
        logging.StreamHandler()
    ]
)
```

### Health Checks

Already implemented:
- `GET /health` - Basic health check
- `GET /sessions/{session_id}/diagnostics` - Session diagnostics

Add monitoring with Prometheus, Grafana, or similar tools.

## 🔄 Backup Strategy

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/rag-assistant"
DATA_DIR="$HOME/.rag-assistant"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/rag-backup-$DATE.tar.gz" "$DATA_DIR"

# Keep only last 7 backups
cd "$BACKUP_DIR"
ls -t | tail -n +8 | xargs rm -f

echo "Backup completed: rag-backup-$DATE.tar.gz"
```

Run daily with cron:

```bash
# crontab -e
0 2 * * * /path/to/backup.sh
```

## 🚀 Scaling

For high load:

1. **Horizontal Scaling**: Run multiple backend instances behind a load balancer
2. **Database**: Migrate from TinyDB to PostgreSQL
3. **Caching**: Implement Redis for session caching
4. **Queue**: Use Celery for async document processing
5. **CDN**: Serve frontend through CDN

## 📞 Support

For deployment issues:
- Check logs: `tail -f /var/log/rag-assistant.log`
- Test endpoints: `curl http://localhost:8000/health`
- Review system resources: `htop` or `top`

---

**Choose the deployment option that best fits your needs!**

