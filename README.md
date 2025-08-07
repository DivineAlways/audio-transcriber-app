# Audio Transcriber App

A modern audio transcription app that leverages [AssemblyAI](https://www.assemblyai.com/) for accurate speech-to-text, with optional workflow integration via [n8n](https://n8n.io/).

## Features

- Drag-and-drop audio file upload
- Supports large files (up to 512MB)
- Transcription powered by AssemblyAI
- Optional n8n webhook integration for workflow automation
- Deployable as a static frontend or with a Python FastAPI backend

---

## Deployment Options

### 1. **Frontend-Only (Static Hosting)**

You can deploy just the frontend (HTML/CSS/JS) to any static host (Cloud Run, Vercel, Netlify, etc.).  
**Note:** If you use this method, your AssemblyAI API key will be exposed in the browser.  
**Recommended only for testing or non-sensitive use.**

#### Steps:
- Edit `frontend/script.js` and set your `ASSEMBLYAI_API_KEY` and `N8N_WEBHOOK_URL`.
- Build and deploy the `frontend/` directory to your preferred static host.

### 2. **Backend + Frontend (Recommended for Security & Flexibility)**

Run the Python FastAPI backend to securely handle your AssemblyAI API key and file uploads.  
The backend proxies requests to AssemblyAI and can trigger n8n workflows.

#### Steps:
- Set your `ASSEMBLYAI_API_KEY` in the backend environment (e.g., `.env` or cloud secret manager).
- Deploy the backend (e.g., to Cloud Run, App Engine, or any server).
- Point your frontend to the backend's `/transcribe` endpoint.

---

## Quick Start

### Backend (FastAPI)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ASSEMBLYAI_API_KEY=your_assemblyai_api_key
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend (Static)

Just open `frontend/index.html` in your browser, or deploy the `frontend/` folder to your favorite static host.

---

## Cloud Run Deployment

**Frontend:**
1. Build and push the Docker image (see `frontend/Dockerfile`).
2. Deploy to Cloud Run or your preferred container host.

**Backend:**
1. Build and push the Docker image (see `backend/Dockerfile` if present).
2. Deploy to Cloud Run or your preferred container host.

---

## Configuration

- **AssemblyAI API Key:**  
  - For backend: Set as environment variable `ASSEMBLYAI_API_KEY`.
  - For frontend-only: Set directly in `frontend/script.js` (not recommended for production).

- **n8n Webhook URL:**  
  - Set in both backend and frontend as needed.

---

## Security Note

- **Frontend-only deployments expose your AssemblyAI API key to users.**
- For production, always use the backend to keep your API key secure.

---

