#!/bin/bash
# FINQUEST AI - One-Click Installation Script
# Handles corporate networks automatically

echo ""
echo "========================================"
echo "FINQUEST AI - Smart Installation"
echo "========================================"
echo ""

# Detect if we're on corporate network
echo "[INFO] Detecting network environment..."

# Test npm registry access
if npm ping > /dev/null 2>&1; then
    echo "[OK] Direct internet access detected"
else
    echo "[DETECTED] Corporate network - Configuring for SSL bypass..."
    echo ""
    
    # Configure npm for corporate network
    npm config set strict-ssl false
    npm config set registry https://registry.npmjs.org/
    
    echo "[OK] npm configured for corporate network"
    echo ""
fi

# ========== BACKEND SETUP ==========
echo "========================================"
echo "BACKEND SETUP"
echo "========================================"
echo ""

echo "[1/4] Creating Python virtual environment..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  [OK] Virtual environment created"
else
    echo "  [INFO] Virtual environment already exists"
fi

echo ""
echo "[2/4] Activating virtual environment..."
source venv/bin/activate

echo ""
echo "[3/4] Upgrading pip and setuptools..."
python -m pip install --upgrade pip setuptools --quiet

echo ""
echo "[4/4] Installing Python dependencies..."
pip install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "  [OK] Backend dependencies installed"
else
    echo "  [ERROR] Backend installation failed"
    exit 1
fi

echo ""
echo "========================================"
echo "FRONTEND SETUP"
echo "========================================"
echo ""

cd ../frontend

echo "[1/3] Clearing any existing caches..."
rm -rf node_modules .angular dist 2>/dev/null
npm cache clean --force > /dev/null 2>&1

echo ""
echo "[2/3] Installing Node dependencies..."
echo "  This may take 2-5 minutes..."
npm install

if [ $? -eq 0 ]; then
    echo "  [OK] Frontend dependencies installed"
else
    echo ""
    echo "  [ERROR] npm install failed!"
    echo ""
    echo "  Common fixes:"
    echo "  1. Run: npm config set strict-ssl false"
    echo "  2. Run: npm cache clean --force"
    echo "  3. Try again"
    echo ""
    exit 1
fi

echo ""
echo "[3/3] Verifying installation..."
if [ -d "node_modules/@angular" ]; then
    echo "  [OK] Angular installed successfully"
else
    echo "  [ERROR] Angular installation incomplete"
    exit 1
fi

# ========== SUCCESS ==========
echo ""
echo "========================================"
echo "INSTALLATION COMPLETE!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start Backend:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m app.main"
echo ""
echo "2. Start Frontend (new terminal):"
echo "   cd frontend"
echo "   npm start"
echo ""
echo "3. Open browser:"
echo "   http://localhost:4200"
echo ""
echo "========================================"
echo ""

# Ask if user wants to start now
read -p "Start FINQUEST AI now? (y/n): " start
if [ "$start" = "y" ] || [ "$start" = "Y" ]; then
    echo ""
    echo "Starting backend..."
    cd ../backend
    source venv/bin/activate
    python -m app.main &
    
    sleep 5
    
    echo "Starting frontend..."
    cd ../frontend
    npm start &
    
    echo ""
    echo "[OK] Both services starting..."
    echo "[INFO] Frontend will open at http://localhost:4200"
    echo ""
fi

