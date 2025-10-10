# Render Deployment (Alternative to Railway)

If Railway keeps timing out, Render is an excellent alternative that handles ML libraries well.

## Render Setup:

### 1. Go to [render.com](https://render.com)
- Sign up with GitHub

### 2. Create Web Service
- Click "New" → "Web Service"
- Connect your GitHub repository: `itsaboutps/NTT`
- **Root Directory**: `backend`

### 3. Configure Service
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python app/main.py`
- **Environment**: Python 3
- **Plan**: Free (750 hours/month)

### 4. Environment Variables
- `PORT`: 10000 (Render default)
- `PYTHONPATH`: `/opt/render/project/src`

## Benefits of Render:
- ✅ **750 hours/month** free (plenty for demos)
- ✅ **Better timeout handling** for ML builds
- ✅ **Automatic SSL** certificates
- ✅ **No credit card required** for free tier
- ✅ **Built-in monitoring** and logs

## Architecture:
```
Frontend (Vercel) → Backend (Render)
     ↑                    ↑
  Unlimited Free      750hrs/month Free
  Static hosting      ML-friendly builds
```