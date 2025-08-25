import os
import json
import base64
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
# Configure the Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# --- Core Functions ---

def generate_project_assets(transcript):
    """
    Analyzes a transcript and generates a complete project package:
    documentation, wireframes, and an interactive prototype.
    """
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

    print("---" + "Generating Project Assets... This may take a moment." + "---")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    print("---" + "Asset Generation Complete." + "---")
    return json.loads(response.text)

def create_github_repo(repo_name):
    """Creates a new repository on GitHub."""
    url = "https://api.github.com/user/repos"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {
        "name": repo_name,
        "description": "A new repository for a generated project package.",
        "private": False,
        "auto_init": True
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def upload_file_to_github(repo_full_name, file_path, file_content):
    """Uploads or updates a file in the specified GitHub repository."""
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    # First, try to get the file to see if it exists
    get_response = requests.get(url, headers=headers)
    
    sha = None
    if get_response.status_code == 200:
        # File exists, get its SHA to perform an update
        sha = get_response.json()['sha']
        
    # Prepare the data for the PUT request
    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
    data = {
        "message": f"feat: Add or update {file_path}",
        "content": encoded_content
    }
    
    if sha:
        # If we have a SHA, it means the file exists and we are updating it.
        data['sha'] = sha
        
    # Make the PUT request to create or update the file
    response = requests.put(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def enable_github_pages(repo_full_name):
    """Enables GitHub Pages for the repository."""
    url = f"https://api.github.com/repos/{repo_full_name}/pages"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {"source": {"branch": "main", "path": "/"}}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    # For demonstration, we'll use the coffee shop example transcript.
    # This can be replaced with any user request.
    example_transcript = """
    Hi, my name is John Doe. I need a simple website for my new coffee shop.
    It should have a homepage with our story, a menu page, and a contact page
    with a map. I like a modern and clean design, maybe with brown and beige colors.
    It needs to be mobile-friendly.
    """

    print("1. Generating complete project package (Docs, Wireframes, Prototype)...")
    project_files = generate_project_assets(example_transcript)
    print(f"   Done. Generated {len(project_files)} files.")

    repo_name = "coffee-shop-project-package" # You can make this dynamic later

    print(f"\n2. Creating GitHub repository named '{repo_name}'...")
    repo_info = create_github_repo(repo_name)
    repo_full_name = repo_info['full_name']
    print(f"   Repository created: {repo_info['html_url']}")

    print("\n3. Uploading all project files to the repository...")
    for file_path, file_content in project_files.items():
        print(f"   - Uploading {file_path}...")
        upload_file_to_github(repo_full_name, file_path, file_content)
    print("   All files uploaded.")

    print("\n4. Enabling GitHub Pages...")
    pages_info = enable_github_pages(repo_full_name)
    print("   GitHub Pages enabled.")
    print(f"   Your new site will be available at: {pages_info['html_url']}")

    print("\n--- All steps completed successfully! ---")
