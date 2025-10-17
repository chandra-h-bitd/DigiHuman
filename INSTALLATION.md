# 🚀 **Simple Installation Guide**

## 📋 **Prerequisites**

- **Python 3.9+** installed on your system
- **Git** (optional, for cloning)

---

## 🖥️ **Windows Installation**

### **Step 1: Download & Extract**
```bash
# Download the project and extract to a folder
# Example: C:\Users\YourName\Documents\NTT
```

### **Step 2: Open Command Prompt**
```bash
# Press Windows + R, type "cmd", press Enter
# Navigate to your project folder
cd C:\Users\YourName\Documents\NTT\backend
```

### **Step 3: Create Virtual Environment**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# You should see (venv) in your prompt
```

### **Step 4: Install Dependencies**
```bash
# Install required packages
pip install -r requirements.txt
pip install aiohttp
```

### **Step 5: Run the Application**
```bash
# Start the backend server
python app/main.py
```

**✅ Done! Your backend is running at http://localhost:8000**

---

## 🍎 **macOS Installation**

### **Step 1: Open Terminal**
```bash
# Press Cmd + Space, type "Terminal", press Enter
# Navigate to your project folder
cd /Users/YourName/Downloads/NTT/backend
```

### **Step 2: Create Virtual Environment**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in your prompt
```

### **Step 3: Install Dependencies**
```bash
# Install required packages
pip install -r requirements.txt
pip install aiohttp
```

### **Step 4: Run the Application**
```bash
# Start the backend server
python app/main.py
```

**✅ Done! Your backend is running at http://localhost:8000**

---

## 🐧 **Linux Installation**

### **Step 1: Open Terminal**
```bash
# Press Ctrl + Alt + T
# Navigate to your project folder
cd /home/YourName/NTT/backend
```

### **Step 2: Create Virtual Environment**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in your prompt
```

### **Step 3: Install Dependencies**
```bash
# Install required packages
pip install -r requirements.txt
pip install aiohttp
```

### **Step 4: Run the Application**
```bash
# Start the backend server
python app/main.py
```

**✅ Done! Your backend is running at http://localhost:8000**

---

## 🌐 **Frontend Installation (All Platforms)**

### **Step 1: Navigate to Frontend**
```bash
# Windows
cd C:\Users\YourName\Documents\NTT\frontend

# macOS/Linux
cd /Users/YourName/Downloads/NTT/frontend
```

### **Step 2: Install Dependencies**
```bash
# Install Node.js dependencies
npm install
```

### **Step 3: Run Frontend**
```bash
# Start the frontend development server
npm start
```

**✅ Done! Your frontend is running at http://localhost:4200**

---

## 🧪 **Quick Test**

### **Test Backend:**
```bash
# Open browser and go to:
http://localhost:8000/health
```

### **Test Frontend:**
```bash
# Open browser and go to:
http://localhost:4200
```

---

## 🔧 **Troubleshooting**

### **Python Not Found:**
- **Windows**: Install Python from [python.org](https://python.org)
- **macOS**: Install Python from [python.org](https://python.org) or use `brew install python3`
- **Linux**: `sudo apt install python3 python3-pip` (Ubuntu/Debian)

### **Permission Errors:**
- **Windows**: Run Command Prompt as Administrator
- **macOS/Linux**: Use `sudo` if needed

### **Port Already in Use:**
- Change port in `app/main.py`: `uvicorn.run(app, host="0.0.0.0", port=8001)`

### **Virtual Environment Issues:**
```bash
# Delete and recreate
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows
python -m venv venv
```

---

## 📱 **Mobile/Tablet Access**

Once running, access from any device on your network:
- **Backend**: `http://YOUR_IP:8000`
- **Frontend**: `http://YOUR_IP:4200`

Find your IP:
- **Windows**: `ipconfig`
- **macOS/Linux**: `ifconfig` or `ip addr`

---

## 🎯 **Quick Start Commands**

### **Backend Only:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt aiohttp
python app/main.py
```

### **Frontend Only:**
```bash
cd frontend
npm install
npm start
```

### **Both (Terminal 1):**
```bash
cd backend && source venv/bin/activate && pip install -r requirements.txt aiohttp && python app/main.py
```

### **Both (Terminal 2):**
```bash
cd frontend && npm install && npm start
```

---

## ✅ **Success Checklist**

- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed
- [ ] Backend running on port 8000
- [ ] Frontend running on port 4200
- [ ] Health check passes: http://localhost:8000/health
- [ ] Frontend loads: http://localhost:4200

**🎉 You're all set! Your Document Q&A system is ready to use!**
