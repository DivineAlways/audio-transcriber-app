from fastapi import FastAPI, File, UploadFile, APIRouter, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import tempfile
from google.cloud import speech
from pydub import AudioSegment
import uvicorn
import requests
import base64
import json

# --- Vercel Environment Setup ---
# On Vercel, GOOGLE_APPLICATION_CREDENTIALS will be set from a Base64 env var
if os.getenv('GOOGLE_CREDENTIALS_BASE64'):
    print("Found GOOGLE_CREDENTIALS_BASE64, decoding to file...")
    try:
        # Decode the base64 string
        decoded_creds = base64.b64decode(os.getenv('GOOGLE_CREDENTIALS_BASE64'))
        
        # Create a temporary file to store the credentials
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_creds_file:
            temp_creds_file.write(decoded_creds.decode('utf-8'))
            # Set the environment variable to the path of the temporary file
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_file.name
            print(f"GOOGLE_APPLICATION_CREDENTIALS set to: {temp_creds_file.name}")

    except Exception as e:
        print(f"Error decoding or writing credentials: {e}")


app = FastAPI()
router = APIRouter()

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- n8n Webhook Configuration ---
N8N_WEBHOOK_URL = "https://innergcomplete.app.n8n.cloud/webhook/c0b2e4e8-c7b1-41c1-8e6e-db02f612b80d"


import uuid

# ... existing code ...

# --- n8n Webhook Configuration ---
N8N_WEBHOOK_URL = "https://innergcomplete.app.n8n.cloud/webhook/c0b2e4e8-c7b1-41c1-8e6e-db02f612b80d"

# --- Chunk Upload Handling ---
# A simple in-memory dictionary to track chunked uploads.
# In a production scenario, you might use Redis or another persistent store.
upload_sessions = {}

@router.post("/upload_chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...)
):
    """
    Receives a single chunk of a large file and saves it.
    """
    temp_dir = "/tmp"
    session_dir = os.path.join(temp_dir, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    chunk_path = os.path.join(session_dir, f"chunk_{chunk_index}")
    
    try:
        with open(chunk_path, "wb") as buffer:
            buffer.write(await file.read())
        
        print(f"Received chunk {chunk_index}/{total_chunks} for session {session_id}")
        
        if session_id not in upload_sessions:
            upload_sessions[session_id] = {"total_chunks": total_chunks, "chunks_received": set()}
        
        upload_sessions[session_id]["chunks_received"].add(chunk_index)
        
        # Check if all chunks have been received
        if len(upload_sessions[session_id]["chunks_received"]) == total_chunks:
            print(f"All chunks received for session {session_id}. Ready for assembly.")
            
        return JSONResponse(content={"message": f"Chunk {chunk_index} received."})

    except Exception as e:
        print(f"Error receiving chunk {chunk_index} for session {session_id}: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.post("/transcribe_chunks")
async def transcribe_chunks(session_id: str, original_filename: str):
    """
    Assembles chunks, transcribes the file, and cleans up.
    """
    temp_dir = "/tmp"
    session_dir = os.path.join(temp_dir, session_id)
    assembled_file_path = os.path.join(temp_dir, original_filename)

    try:
        if not os.path.exists(session_dir):
            return JSONResponse(content={"error": "Invalid session ID or no chunks found."}, status_code=404)

        # Assemble the file from chunks
        print(f"Assembling file for session {session_id}...")
        with open(assembled_file_path, "wb") as assembled_file:
            # Assuming chunks are named chunk_0, chunk_1, etc.
            total_chunks = len(os.listdir(session_dir))
            for i in range(total_chunks):
                chunk_path = os.path.join(session_dir, f"chunk_{i}")
                with open(chunk_path, "rb") as chunk_file:
                    assembled_file.write(chunk_file.read())
        
        print(f"File assembled at: {assembled_file_path}")

        # --- Start Transcription Logic (adapted from original function) ---
        client = speech.SpeechClient()
        audio_chunks = chunk_audio(assembled_file_path) # This is the backend chunking for Google API
        all_transcripts = []

        for i, chunk_path in enumerate(audio_chunks):
            print(f"\nProcessing Google API chunk {i+1}/{len(audio_chunks)}...")
            with io.open(chunk_path, "rb") as audio_file:
                content = audio_file.read()
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                sample_rate_hertz=8000,
                language_code="en-US",
            )
            response = client.recognize(config=config, audio=audio)
            for result in response.results:
                all_transcripts.append(result.alternatives[0].transcript)
        
        transcript = " ".join(all_transcripts)
        # --- End Transcription Logic ---

        if transcript:
            # Send to n8n
            try:
                requests.post(N8N_WEBHOOK_URL, json={"transcript": transcript, "originalFileName": original_filename})
            except Exception as e:
                print(f"Error sending to n8n: {e}")
            return JSONResponse(content={"transcript": transcript})
        else:
            return JSONResponse(content={"message": "No transcription found."}, status_code=404)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        # Clean up session directory and assembled file
        if os.path.exists(session_dir):
            import shutil
            shutil.rmtree(session_dir)
            print(f"Cleaned up session directory: {session_dir}")
        if os.path.exists(assembled_file_path):
            os.remove(assembled_file_path)
            print(f"Cleaned up assembled file: {assembled_file_path}")
        if session_id in upload_sessions:
            del upload_sessions[session_id]

# Determine the absolute path to the project's root directory
# This is necessary for locating the 'bin' directory in the Vercel environment
project_root = os.path.dirname(os.path.abspath(__file__))
ffmpeg_path = os.path.join(project_root, "bin/ffmpeg")
ffprobe_path = os.path.join(project_root, "bin/ffprobe")

# Debug: Log the paths and check if files exist
print(f"Project root: {project_root}")
print(f"FFmpeg path: {ffmpeg_path}")
print(f"FFprobe path: {ffprobe_path}")
print(f"FFmpeg exists: {os.path.exists(ffmpeg_path)}")
print(f"FFprobe exists: {os.path.exists(ffprobe_path)}")

# List contents of project root and bin directory for debugging
print(f"Contents of project root: {os.listdir(project_root)}")
bin_dir = os.path.join(project_root, "bin")
if os.path.exists(bin_dir):
    print(f"Contents of bin directory: {os.listdir(bin_dir)}")
else:
    print("Bin directory does not exist!")

# Tell pydub where to find ffmpeg and ffprobe
AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

def chunk_audio(input_path: str, chunk_duration_seconds: int = 50) -> list:
    """
    Split audio file into smaller chunks for Google API.
    Returns list of paths to chunk files.
    """
    try:
        print(f"Splitting audio for Google API into {chunk_duration_seconds}-second chunks...")
        audio = AudioSegment.from_file(input_path)
        chunk_size_ms = chunk_duration_seconds * 1000
        chunks = []
        temp_dir = tempfile.gettempdir()
        
        for i, chunk_start in enumerate(range(0, len(audio), chunk_size_ms)):
            chunk_end = min(chunk_start + chunk_size_ms, len(audio))
            chunk = audio[chunk_start:chunk_end]
            chunk = chunk.set_frame_rate(8000).set_channels(1)
            
            chunk_path = os.path.join(temp_dir, f"google_api_chunk_{i}.mp3")
            chunk.export(chunk_path, format="mp3", bitrate="16k")
            chunks.append(chunk_path)
            
        return chunks
    except Exception as e:
        print(f"Error chunking audio for Google API: {e}")
        # Re-raise the exception to be caught by the main endpoint handler
        raise e

# The original endpoint is now deprecated and can be removed or disabled.
# For now, let's leave it but it won't be used by the new frontend.
@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    DEPRECATED: This endpoint does not support chunked uploads and will fail for large files on Vercel.
    """
    return JSONResponse(
        content={"error": "This endpoint is deprecated. Please use the chunked upload flow."},
        status_code=400
    )

app.include_router(router)

if __name__ == "__main__":
    # ... existing code ...
    uvicorn.run(app, host="0.0.0.0", port=8000)
