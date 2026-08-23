# Deployment Guide — RedSite AI

> **Goal:** Get RedSite AI publicly accessible for IBM AI Builders Challenge judges by August 31, 2026.

---

## Quick Decision Matrix

| Option | Time to Deploy | Cost | Complexity | Best For |
|--------|---------------|------|------------|----------|
| **A. Render (monolith)** | 15 min | Free | Low | Fastest path, single URL |
| **B. Vercel + Render** | 25 min | Free | Medium | Best performance, separate frontend/backend |
| **C. Railway** | 20 min | Free ($5/mo after) | Low | Modern DX, auto-deploy |
| **D. Replit** | 10 min | Free | Lowest | Quickest shareable link |
| **E. IBM Cloud** | 45 min | Free tier | High | Strategic alignment with IBM |

**Recommendation:** Use **Option A (Render monolith)** for speed and reliability, or **Option B (Vercel + Render)** if you want the best demo experience.

---

## Option A: Render Monolith (Recommended — Fastest)

Deploy the entire stack as a single Docker service on Render.

### Why This Works
- One URL, one service, one deploy
- Render free tier stays awake (unlike Heroku)
- SQLite instead of PostgreSQL = zero database setup
- Judges click one link and see everything

### Step-by-Step

**1. Push to GitHub**
```bash
git init
git add .
git commit -m "Initial RedSite AI scaffold"
git remote add origin https://github.com/YOUR_USERNAME/redsite-ai.git
git push -u origin main
```

**2. Create `render.yaml` (Blueprints)**

This file tells Render exactly how to build and run your app:

```yaml
services:
  - type: web
    name: redsite-ai
    runtime: docker
    repo: https://github.com/YOUR_USERNAME/redsite-ai
    branch: main
    dockerfilePath: ./Dockerfile.render
    envVars:
      - key: WATSONX_API_KEY
        sync: false  # Set manually in Render dashboard
      - key: WATSONX_PROJECT_ID
        sync: false
      - key: DATABASE_URL
        value: sqlite:///./data/redsite.db
      - key: FRONTEND_BUILD
        value: "true"
    plan: free
```

**3. Create `Dockerfile.render` (Root level)**

A single Dockerfile that builds both frontend and backend:

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + serve frontend
FROM python:3.11-slim
WORKDIR /app

# Install Node.js for any runtime needs (optional)
RUN apt-get update && apt-get install -y --no-install-recommends     nodejs npm     && rm -rf /var/lib/apt/lists/*

# Copy backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/

# Copy built frontend static files
COPY --from=frontend-builder /app/frontend/.next/static ./frontend/static
COPY --from=frontend-builder /app/frontend/out ./frontend/out

# Create data directory for SQLite
RUN mkdir -p ./data

# Copy startup script
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
```

**4. Create `start.sh`**

```bash
#!/bin/bash
set -e

echo "Starting RedSite AI..."

# Start FastAPI backend (serves API + static frontend)
cd backend
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

**5. Update `backend/main.py` to serve static frontend**

Add this to `backend/main.py`:

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Mount static files if they exist
static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "out")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "RedSite AI API is running. Visit /docs for API documentation."}
```

**6. Update `frontend/next.config.js` for static export**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',  // Static HTML export for embedding
  distDir: 'out',
  images: {
    unoptimized: true,  // Required for static export
  },
};

module.exports = nextConfig;
```

**7. Deploy to Render**
- Go to [render.com](https://render.com)
- Click "New +" → "Blueprint"
- Connect your GitHub repo
- Render reads `render.yaml` and deploys automatically
- Set `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` in Environment dashboard
- Wait 5–10 minutes for build
- Your app is live at `https://redsite-ai.onrender.com`

---

## Option B: Vercel (Frontend) + Render (Backend)

Best performance, but two URLs to manage.

### Backend on Render

**1. Create `render-backend.yaml`**
```yaml
services:
  - type: web
    name: redsite-ai-backend
    runtime: python
    repo: https://github.com/YOUR_USERNAME/redsite-ai
    branch: main
    buildCommand: "pip install -r backend/requirements.txt"
    startCommand: "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: WATSONX_API_KEY
        sync: false
      - key: WATSONX_PROJECT_ID
        sync: false
    plan: free
```

**2. Update CORS in `backend/main.py`**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://redsite-ai.vercel.app",  # Your Vercel URL
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Frontend on Vercel

**1. Update `frontend/next.config.js`**
```javascript
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'https://redsite-ai-backend.onrender.com/api/:path*',
      },
    ];
  },
};
module.exports = nextConfig;
```

**2. Deploy**
- Go to [vercel.com](https://vercel.com)
- Import your GitHub repo
- Set root directory to `frontend/`
- Add environment variable: `NEXT_PUBLIC_API_URL=https://redsite-ai-backend.onrender.com`
- Deploy

---

## Option C: Railway (Modern Alternative)

Railway has a generous free tier and great developer experience.

**1. Install Railway CLI**
```bash
npm install -g @railway/cli
railway login
```

**2. Create `railway.json`**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.render"
  },
  "deploy": {
    "startCommand": "./start.sh",
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**3. Deploy**
```bash
railway link
railway up
```

---

## Option D: Replit (Fastest Shareable Link)

If you need a working link in 10 minutes:

**1. Import to Replit**
- Go to [replit.com](https://replit.com)
- Click "Create" → "Import from GitHub"
- Paste your repo URL
- Replit auto-detects Python + Node.js

**2. Configure `.replit`**
```toml
run = "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000"
language = "python"
```

**3. Set secrets in Replit dashboard**
- WATSONX_API_KEY
- WATSONX_PROJECT_ID

**4. Run**
- Click "Run" button
- Replit gives you a public URL instantly

**Pros:** Fastest, no credit card, live collaboration
**Cons:** URL changes on fork, less professional for judges

---

## Option E: IBM Cloud (Strategic Alignment)

Deploying on IBM Cloud shows deep ecosystem commitment.

**1. IBM Cloud Foundry (Classic)**
```bash
# Install IBM Cloud CLI
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh
ibmcloud login

# Push app
ibmcloud cf push redsite-ai -b python_buildpack
```

**2. IBM Cloud Code Engine (Serverless)**
- Containerize with the Dockerfile above
- Push to IBM Container Registry
- Deploy to Code Engine
- Auto-scales to zero when not in use (cost-effective)

**3. IBM Cloud Kubernetes (Overkill for demo)**
- Only if you want to show enterprise-grade deployment
- Free cluster for 30 days

**Pros:** Perfect alignment with challenge sponsor, impressive to judges
**Cons:** Steeper learning curve, 45+ min setup

---

## Environment Variables Reference

| Variable | Required | Description | Where to Set |
|----------|----------|-------------|--------------|
| `WATSONX_API_KEY` | Yes (for Granite) | IBM Cloud API key | Render/Vercel dashboard |
| `WATSONX_PROJECT_ID` | Yes (for Granite) | watsonx.ai project ID | Render/Vercel dashboard |
| `DATABASE_URL` | No | Defaults to SQLite | Auto-set |
| `PORT` | No | Render sets automatically | Auto-set |
| `NEXT_PUBLIC_API_URL` | Yes (Option B) | Backend URL for frontend | Vercel dashboard |

---

## Pre-Deployment Checklist

Before submitting, verify:

- [ ] GitHub repo is **public**
- [ ] `README.md` is complete and accurate
- [ ] `docs/BOB_USAGE.md` is populated with real sessions
- [ ] Demo video is uploaded to YouTube (unlisted or public)
- [ ] Live app URL works and loads without errors
- [ ] All API endpoints respond correctly (`/api/health`, `/api/sites`, `/api/score`)
- [ ] Frontend renders Mars map, site list, and chat panel
- [ ] Mission profile switching recalculates scores
- [ ] AI analyst responds to questions (or falls back gracefully)
- [ ] Environment variables are set (not hardcoded in repo)
- [ ] No API keys committed to git (check with `git log --all --full-history -- '*env*'`)

---

## Troubleshooting

### Build fails on Render
**Fix:** Check that `requirements.txt` has no commented-out required packages. For deployment, uncomment:
```
# fastapi==0.111.0
# uvicorn[standard]==0.30.0
```

### Frontend shows "Cannot connect to backend"
**Fix:** Check CORS origins in `backend/main.py` match your frontend URL exactly.

### Watsonx.ai returns 401
**Fix:** Verify `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` are set in deployment dashboard, not just locally.

### SQLite database is empty
**Fix:** The MVP uses in-memory sample data. For production, run data ingestion script first:
```bash
python backend/data_ingest.py
```

### Static files not serving
**Fix:** Ensure `frontend/next.config.js` has `output: 'export'` and `distDir: 'out'`.

---

## Recommended Final Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         JUDGES                              │
│                           │                                 │
│                    https://redsite-ai.onrender.com          │
│                           │                                 │
│              ┌────────────┴────────────┐                  │
│              │    Render (Free Tier)    │                  │
│              │  ┌─────────────────────┐  │                  │
│              │  │  FastAPI Backend    │  │                  │
│              │  │  + Static Frontend  │  │                  │
│              │  │  + SQLite DB        │  │                  │
│              │  └─────────────────────┘  │                  │
│              │         Docker            │                  │
│              └───────────────────────────┘                  │
│                           │                                 │
│              ┌────────────┴────────────┐                  │
│              │    IBM watsonx.ai        │                  │
│              │    (Granite LLM)         │                  │
│              └───────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Submission Package

By August 31, you should have:

1. **GitHub Repo** (public): `github.com/YOU/redsite-ai`
2. **Live App** (public): `https://redsite-ai.onrender.com`
3. **Demo Video** (public/YouTube): 3 minutes max
4. **Project Page** (challenge platform): Links to repo + video + live app

---

> **Deploy early, test often, submit on time.**
