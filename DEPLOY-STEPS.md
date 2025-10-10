# 🚀 Railway + Vercel Deployment Guide

## ✅ Configuration Complete! Now Deploy:

### Step 1: Deploy Backend to Railway 🚂

1. **Go to [railway.app](https://railway.app)**
   - Sign up/login with GitHub
   
2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo" 
   - Choose your `itsaboutps/NTT` repository
   
3. **Configure Backend Service**
   - **Root Directory**: `backend`
   - **Start Command**: `python app/main.py` (auto-detected from Procfile)
   - **Build Command**: Leave empty (auto-detected)
   
4. **Set Environment Variable**
   - Go to "Variables" tab
   - Add: `PORT = 8000`
   
5. **Deploy!**
   - Railway will automatically install from `backend/requirements.txt`
   - Wait for deployment to complete (~3-5 minutes)
   - **Copy your Railway URL** (e.g., `https://ntt-production-xxxx.up.railway.app`)

### Step 2: Deploy Frontend to Vercel 🌐

1. **Go to [vercel.com](https://vercel.com)**
   - Sign up/login with GitHub
   
2. **Import Project**
   - Click "New Project"
   - Import your `itsaboutps/NTT` repository
   - **Framework Preset**: Other
   - **Root Directory**: `/` (root)
   
3. **Build Configuration**
   - **Build Command**: `npm run build`
   - **Output Directory**: `frontend/dist`
   - **Install Command**: `npm install`
   
4. **Deploy!**
   - Vercel will build your Angular app
   - Get your Vercel URL (e.g., `https://ntt-frontend.vercel.app`)

### Step 3: Connect Frontend to Railway Backend 🔗

1. **Update API Service**
   - Copy your Railway backend URL from Step 1
   - Replace `ntt-production.up.railway.app` in the code
   
2. **Update & Redeploy**
   - I'll help you update the API service with the real Railway URL
   - Commit and push changes
   - Vercel will auto-redeploy

### Step 4: Test Your Live App! 🎉

Your app will be live at:
- **Frontend**: `https://your-app.vercel.app`
- **Backend**: `https://your-app.up.railway.app` (internal)

## What You Get:

✅ **Frontend**: Unlimited free hosting on Vercel  
✅ **Backend**: Railway with 1GB RAM for ML libraries  
✅ **Full functionality**: Document uploads + AI Q&A  
✅ **Auto-deployments**: Push code → automatic updates  
✅ **Professional setup**: Production-ready architecture  

## Ready to Deploy?

**Start with Step 1** - deploy backend to Railway first, then I'll help you connect everything! 🚀