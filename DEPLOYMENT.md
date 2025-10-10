# Deploy to Vercel - Single Platform Solution

## What You Get:
- ✅ **FREE unlimited hosting** for personal use
- ✅ **Both frontend + backend** on one platform
- ✅ **Automatic HTTPS** and global CDN
- ✅ **No time limits** (unlike other platforms)

## Quick Deploy Steps:

### 1. Push to GitHub
```bash
git add .
git commit -m "Ready for Vercel deployment"
git push origin master
```

### 2. Deploy on Vercel
1. Go to [vercel.com](https://vercel.com)
2. Sign up/login with GitHub
3. Click "New Project"
4. Import your `NTT` repository
5. Click "Deploy" (Vercel auto-detects the config)

### 3. That's it! 🎉
Your app will be live at: `https://your-project-name.vercel.app`

## How it Works:
- **Frontend**: Served from `/` (your Angular app)
- **Backend**: Available at `/api/*` (your FastAPI routes)
- **Single URL**: Everything works together seamlessly

## Alternative: Render (Also Single Platform)

If you prefer Render:
1. Go to [render.com](https://render.com)
2. Create "Static Site" for frontend
3. Create "Web Service" for backend
4. Free tier: 750 hours/month

## Why Vercel is Better:
- **Unlimited** vs Render's 750hrs/month
- **No cold starts** for static frontend
- **Simpler** single-platform deployment
- **Better performance** with global CDN

## Your Live Demo Will:
- Accept document uploads
- Answer questions using Gemini/SBERT
- Work exactly like your local version
- Be accessible to anyone with the URL

Ready to deploy? Just push to GitHub and connect to Vercel!