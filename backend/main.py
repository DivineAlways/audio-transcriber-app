from fastapi import FastAPI, File, UploadFile, APIRouter, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import tempfile
from google.cloud import speech
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

        # --- Start Transcription Logic (using Google's built-in audio processing) ---
        print("Starting transcription with Google Speech-to-Text...")
        transcript = process_audio_with_google_directly(assembled_file_path)
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

def chunk_audio_simple(input_path: str, max_size_mb: int = 10) -> list:
    """
    Split audio file into smaller chunks based on file size for Google API.
    This approach doesn't require ffmpeg - just splits the raw audio data.
    """
    try:
        print(f"Splitting audio file by size (max {max_size_mb}MB per chunk)...")
        
        # Get file size
        file_size = os.path.getsize(input_path)
        max_chunk_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
        
        if file_size <= max_chunk_size:
            print("File is small enough, no chunking needed")
            return [input_path]
        
        chunks = []
        temp_dir = tempfile.gettempdir()
        
        with open(input_path, 'rb') as input_file:
            chunk_index = 0
            while True:
                chunk_data = input_file.read(max_chunk_size)
                if not chunk_data:
                    break
                
                chunk_path = os.path.join(temp_dir, f"audio_chunk_{chunk_index}.dat")
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(chunk_data)
                chunks.append(chunk_path)
                chunk_index += 1
                print(f"Created chunk {chunk_index}: {len(chunk_data)} bytes")
        
        return chunks
    except Exception as e:
        print(f"Error chunking audio: {e}")
        raise e

def process_audio_with_google_directly(file_path: str) -> str:
    """
    Process audio file directly with Google Speech-to-Text without ffmpeg.
    Try different configurations to handle various audio formats.
    """
    try:
        print("Processing audio with Google Speech-to-Text directly...")
        client = speech.SpeechClient()
        
        # Read the audio file
        with io.open(file_path, "rb") as audio_file:
            content = audio_file.read()
        
        audio = speech.RecognitionAudio(content=content)
        
        # Get file extension to help determine format
        file_extension = os.path.splitext(file_path)[1].lower()
        print(f"File extension: {file_extension}")
        
        # Try different configurations based on file type
        configs_to_try = []
        
        if file_extension in ['.mp3']:
            configs_to_try.append({
                "encoding": speech.RecognitionConfig.AudioEncoding.MP3,
                "language_code": "en-US",
                "enable_automatic_punctuation": True,
            })
        elif file_extension in ['.wav']:
            configs_to_try.append({
                "encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                "language_code": "en-US",
                "enable_automatic_punctuation": True,
            })
        elif file_extension in ['.flac']:
            configs_to_try.append({
                "encoding": speech.RecognitionConfig.AudioEncoding.FLAC,
                "language_code": "en-US",
                "enable_automatic_punctuation": True,
            })
        elif file_extension in ['.m4a', '.mp4', '.mov', '.avi', '.mkv']:
            # For video files or m4a, try multiple encodings
            configs_to_try.extend([
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.MP3,
                    "language_code": "en-US",
                    "enable_automatic_punctuation": True,
                },
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    "language_code": "en-US",
                    "enable_automatic_punctuation": True,
                }
            ])
        
        # If no specific format detected, try common ones
        if not configs_to_try:
            configs_to_try.extend([
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.MP3,
                    "language_code": "en-US",
                    "enable_automatic_punctuation": True,
                },
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    "language_code": "en-US",
                    "enable_automatic_punctuation": True,
                },
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.FLAC,
                    "language_code": "en-US",
                    "enable_automatic_punctuation": True,
                }
            ])
        
        # Try each configuration until one works
        for i, config_dict in enumerate(configs_to_try):
            try:
                print(f"Trying configuration {i+1}: {config_dict['encoding']}")
                config = speech.RecognitionConfig(**config_dict)
                
                # For files larger than 10MB, split them
                file_size_mb = len(content) / (1024 * 1024)
                
                if file_size_mb > 10:
                    print(f"Large file detected ({file_size_mb:.2f}MB), splitting...")
                    chunks = chunk_audio_simple(file_path, max_size_mb=10)
                    all_transcripts = []
                    
                    for j, chunk_path in enumerate(chunks):
                        print(f"Processing chunk {j+1}/{len(chunks)}...")
                        with io.open(chunk_path, "rb") as chunk_file:
                            chunk_content = chunk_file.read()
                        
                        chunk_audio = speech.RecognitionAudio(content=chunk_content)
                        response = client.recognize(config=config, audio=chunk_audio)
                        
                        for result in response.results:
                            all_transcripts.append(result.alternatives[0].transcript)
                        
                        # Clean up chunk file
                        os.remove(chunk_path)
                    
                    return " ".join(all_transcripts)
                else:
                    print("Using standard recognition for smaller file...")
                    response = client.recognize(config=config, audio=audio)
                    
                    transcripts = []
                    for result in response.results:
                        transcripts.append(result.alternatives[0].transcript)
                    
                    return " ".join(transcripts)
                    
            except Exception as config_error:
                print(f"Configuration {i+1} failed: {config_error}")
                if i == len(configs_to_try) - 1:  # Last configuration
                    raise config_error
                continue
        
        return "No transcription could be generated."
            
    except Exception as e:
        print(f"Error processing audio with Google: {e}")
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
