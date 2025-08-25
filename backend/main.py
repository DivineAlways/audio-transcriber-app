from dotenv import load_dotenv

# Explicitly load the .env file
load_dotenv()

from fastapi import FastAPI, File, UploadFile, Body, Form
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
import assemblyai as aai
import google.generativeai as genai
import os
import tempfile
import requests
import json
import base64
import datetime

# --- API Key Configuration ---
aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

app = FastAPI()

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# --- Project Generation Function ---
def generate_project_assets(transcript):
    """Analyzes a transcript and generates a complete project package."""
    model = genai.GenerativeModel('gemini-2.5-pro')
    prompt = f"""
    **CRITICAL TASK: Generate a complete, self-contained project package based on the user's request.**

    **USER REQUEST TRANSCRIPT:**
    ---
    {transcript}
    ---

    **PRIMARY GOAL:**
    Produce a complete, static, and interactive project deliverable based on the user's request. The entire output MUST be a single, valid JSON object where keys are the full file paths (e.g., "docs/overview.md", "prototype/index.html") and values are the complete file content.

    **PROJECT STRUCTURE & REQUIREMENTS:**

    1.  **Overall Structure (JSON Keys):**
        - `index.html`: A central hub page.
        - `README.md`: A brief project readme.
        - `docs/`: A directory for all markdown documentation.
        - `wireframes/`: A directory for low-fidelity HTML wireframes.
        - `prototype/`: A directory for the high-fidelity, interactive HTML/CSS/JS prototype.
        - `prototype/assets/`: For CSS, JS, and data files.

    2.  **Hub Page (`index.html`):**
        - Create a clean landing page with three main navigation cards:
            - **"Documentation"**: Links to `docs/overview.md`.
            - **"Wireframes"**: Links to `wireframes/index.html`.
            - **"Interactive Prototype"**: Links to `prototype/index.html`.
        - **IMPORTANT:** In the footer of this page, add two links: "View Documentation" (to `docs/overview.md`) and "View Wireframe" (to `wireframes/index.html`).

    3.  **Documentation (`docs/*.md`):**
        - Generate concise, actionable markdown documentation based on the user's request.
        - Include key sections like `overview.md`, `requirements.md`, and `flows.md`.
        - Use tables, lists, and clear examples.

    4.  **Wireframes (`wireframes/*.html`):**
        - Produce low-fidelity, grayscale HTML wireframes. Use simple CSS for layout (boxes, lines, labels).
        - Create an `index.html` in this directory that links to all other wireframe pages.
        - Each wireframe should have a header and a "notes" column explaining the logic.
        - These are for layout and flow, not for final design.

    5.  **Interactive Prototype (`prototype/`):**
        - Create a clickable, data-driven, and mobile-friendly prototype using vanilla HTML, CSS, and JavaScript.
        - **NO external libraries or frameworks.**
        - The `prototype/index.html` is the entry point.
        - `prototype/assets/styles.css`: All CSS for the prototype.
        - `prototype/assets/app.js`: All JavaScript for interactivity.
        - `prototype/assets/dummy-data.json`: Create realistic mock data to power the prototype.
        - The prototype must be a simulation of the core user flows.

    **EXECUTION:**
    - Analyze the provided **USER REQUEST TRANSCRIPT**.
    - Generate all the files described above according to the specified structure and requirements.
    - Ensure all internal links between the hub, docs, wireframes, and prototype pages are correct.
    - Return the entire project as a single, valid JSON object. Do not include any other text or explanation in your response.
    """
    print("--- Generating Project Assets... This may take a moment. ---")
    response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(response_mime_type="application/json"))
    print("--- Asset Generation Complete. ---")
    return json.loads(response.text)

# --- GitHub Functions ---
def create_github_repo(repo_name):
    """Creates a new repository on GitHub."""
    url = "https://api.github.com/user/repos"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {"name": repo_name, "description": "A new repository for a generated project package.", "private": False, "auto_init": True}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def upload_file_to_github(repo_full_name, file_path, file_content):
    """Uploads or updates a file in the specified GitHub repository."""
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    get_response = requests.get(url, headers=headers)
    sha = None
    if get_response.status_code == 200:
        sha = get_response.json().get('sha')
    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
    data = {"message": f"feat: Add or update {file_path}", "content": encoded_content}
    if sha:
        data['sha'] = sha
    response = requests.put(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def enable_github_pages(repo_full_name):
    """Enables GitHub Pages for the repository."""
    url = f"https://api.github.com/repos/{repo_full_name}/pages"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"source": {"branch": "main", "path": "/"}}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# --- Orchestrator Function ---
def generate_and_deploy_project(transcript):
    """Generates assets, creates a repo, uploads files, and enables GitHub Pages."""
    if not GITHUB_TOKEN or not GITHUB_USERNAME:
        raise ValueError("GITHUB_TOKEN and GITHUB_USERNAME must be set in the environment.")

    print("1. Generating complete project package...")
    project_files = generate_project_assets(transcript)
    print(f"   Done. Generated {len(project_files)} files.")

    repo_name = f"generated-project-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"\n2. Creating GitHub repository named '{repo_name}'...")
    repo_info = create_github_repo(repo_name)
    repo_full_name = f"{GITHUB_USERNAME}/{repo_name}"
    print(f"   Repository created: {repo_info['html_url']}")

    print("\n3. Uploading all project files to the repository...")
    for file_path, file_content in project_files.items():
        print(f"   - Uploading {file_path}...")
        upload_file_to_github(repo_full_name, file_path, file_content)
    print("   All files uploaded.")

    print("\n4. Enabling GitHub Pages...")
    pages_info = enable_github_pages(repo_full_name)
    print(f"   GitHub Pages enabled: {pages_info['html_url']}")

    return {"repo_url": repo_info['html_url'], "pages_url": pages_info['html_url']}

# --- API Endpoints ---
@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), webhook_url: str = Form(None)):
    """Transcribes audio, then generates and deploys a project, optionally calling a webhook."""
    temp_path = None
    try:
        # Read file content into memory for webhook and local processing
        content = await file.read()
        
        # --- Webhook Trigger (Audio) ---
        if webhook_url:
            print(f"--- Sending audio to webhook: {webhook_url} ---")
            try:
                # Re-create UploadFile for webhook if needed, or just send raw content
                # For simplicity, sending as multipart form data, similar to how FastAPI receives it
                files = {'file': (file.filename, content, file.content_type)}
                requests.post(webhook_url, files=files, timeout=30) # Increased timeout for file uploads
                print("--- Audio sent to webhook successfully. ---")
            except Exception as e:
                print(f"--- Failed to send audio to webhook: {e} ---")

        # Save to temporary file for AssemblyAI processing
        file_extension = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(temp_path)

        if transcript.status == aai.TranscriptStatus.error:
            return JSONResponse(content={"error": f"Transcription failed: {transcript.error}"}, status_code=500)

        transcribed_text = transcript.text
        if not transcribed_text or not transcribed_text.strip():
            return JSONResponse(content={"error": "No speech detected in the audio file."}, status_code=400)

        result = await run_in_threadpool(generate_and_deploy_project, transcribed_text)
        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(content={"error": f"An error occurred: {str(e)}"}, status_code=500)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

@app.post("/generate-from-text")
async def generate_project(payload: dict = Body(...)):
    """Generates and deploys a project from text, optionally calling a webhook."""
    try:
        transcript = payload.get("transcript")
        webhook_url = payload.get("webhook_url")

        if not transcript:
            return JSONResponse(content={"error": "Transcript is required"}, status_code=400)

        # --- Webhook Trigger (Text) ---
        if webhook_url:
            print(f"--- Sending text to webhook: {webhook_url} ---")
            try:
                requests.post(webhook_url, json={'transcript': transcript}, timeout=10)
                print("--- Text sent to webhook successfully. ---")
            except Exception as e:
                print(f"--- Failed to send text to webhook: {e} ---")

        result = await run_in_threadpool(generate_and_deploy_project, transcript)
        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(content={"error": f"An error occurred: {str(e)}"}, status_code=500)

@app.get("/")
async def root():
    return {"message": "Audio Transcriber and Project Generator API", "status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)