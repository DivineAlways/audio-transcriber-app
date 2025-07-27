from fastapi import FastAPI, File, UploadFile, APIRouter
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


# Tell pydub where to find ffmpeg
AudioSegment.converter = "/tmp/ffmpeg/ffmpeg"

def chunk_audio(input_path: str, chunk_duration_minutes: int = 3) -> list:
    """
    Split audio file into smaller chunks.
    Returns list of paths to chunk files.
    """
    try:
        print(f"Splitting audio into {chunk_duration_minutes}-minute chunks...")
        audio = AudioSegment.from_file(input_path)
        chunk_size_ms = chunk_duration_minutes * 60 * 1000
        chunks = []
        temp_dir = tempfile.gettempdir()
        
        for i, chunk_start in enumerate(range(0, len(audio), chunk_size_ms)):
            chunk_end = min(chunk_start + chunk_size_ms, len(audio))
            chunk = audio[chunk_start:chunk_end]
            chunk = chunk.set_frame_rate(8000).set_channels(1)
            
            chunk_path = os.path.join(temp_dir, f"audio_chunk_{i}.mp3")
            chunk.export(chunk_path, format="mp3", bitrate="16k")
            chunks.append(chunk_path)
            
            chunk_size = os.path.getsize(chunk_path)
            print(f"Chunk {i+1}: {chunk_size / (1024*1024):.2f} MB")
        
        return chunks
    except Exception as e:
        print(f"Error chunking audio: {e}")
        return [input_path]

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribes an audio file using Google Speech-to-Text.
    """
    # Vercel's serverless environment is stateless, and only the /tmp directory is writable.
    temp_dir = "/tmp"
    temp_audio_path = os.path.join(temp_dir, file.filename)

    try:
        # Save the uploaded file to the /tmp directory
        with open(temp_audio_path, "wb") as buffer:
            buffer.write(await file.read())
        
        print(f"Temporary file created at: {temp_audio_path}")
        print(f"Does the file exist? {os.path.exists(temp_audio_path)}")
        print(f"File size: {os.path.getsize(temp_audio_path)} bytes")

        client = speech.SpeechClient()
        
        # Pass the correct path to the chunking function
        audio_chunks = chunk_audio(temp_audio_path)
        
        all_transcripts = []
        
        for i, chunk_path in enumerate(audio_chunks):
            print(f"\nProcessing chunk {i+1}/{len(audio_chunks)} at {chunk_path}...")
            print(f"Does chunk exist? {os.path.exists(chunk_path)}")
            
            with io.open(chunk_path, "rb") as audio_file:
                content = audio_file.read()
                audio = speech.RecognitionAudio(content=content)

            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                sample_rate_hertz=8000,
                language_code="en-US",
            )

            print(f"Transcribing chunk {i+1}...")
            response = client.recognize(config=config, audio=audio)
            
            chunk_transcript = ""
            for result in response.results:
                chunk_transcript += result.alternatives[0].transcript + " "
            
            if chunk_transcript.strip():
                all_transcripts.append(chunk_transcript.strip())
                print(f"Chunk {i+1} transcribed successfully.")
            else:
                print(f"No transcription found for chunk {i+1}.")
        
        transcript = " ".join(all_transcripts)
        
        # Clean up all temporary files
        for chunk_path in audio_chunks:
            try:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    print(f"Cleaned up chunk: {os.path.basename(chunk_path)}")
            except Exception as e:
                print(f"Error cleaning up chunk {chunk_path}: {e}")
        
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            print(f"Cleaned up original temp file: {temp_audio_path}")

        if transcript:
            # Send transcript to n8n webhook
            try:
                payload = {
                    "transcript": transcript,
                    "originalFileName": file.filename,
                }
                print(f"Sending transcript to n8n webhook: {N8N_WEBHOOK_URL}...")
                n8n_response = requests.post(N8N_WEBHOOK_URL, json=payload)
                n8n_response.raise_for_status()
                print("Successfully sent data to n8n webhook.")
            except requests.exceptions.RequestException as e:
                print(f"Error sending data to n8n webhook: {e}")

            return JSONResponse(content={"transcript": transcript})
        else:
            return JSONResponse(content={"message": "No transcription found for the audio file."}, status_code=404)

    except Exception as e:
        print(f"An error occurred: {e}")
        # Clean up in case of error
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        return JSONResponse(content={"error": str(e)}, status_code=500)

app.include_router(router)

if __name__ == "__main__":
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("WARNING: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Please set it to the path of your Google Cloud service account key JSON file.")
        print("Example: export GOOGLE_APPLICATION_CREDENTIALS=\"/path/to/your/key.json\"")
        exit(1)
    uvicorn.run(app, host="0.0.0.0", port=8000)
