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
        print(f"=== TRANSCRIBE CHUNKS START ===")
        print(f"Session ID: {session_id}")
        print(f"Original filename: {original_filename}")
        print(f"Session dir: {session_dir}")
        print(f"Assembled file path: {assembled_file_path}")
        
        if not os.path.exists(session_dir):
            print(f"ERROR: Session directory does not exist: {session_dir}")
            return JSONResponse(content={"error": "Invalid session ID or no chunks found."}, status_code=404)

        # Assemble the file from chunks
        print(f"Assembling file for session {session_id}...")
        with open(assembled_file_path, "wb") as assembled_file:
            # Assuming chunks are named chunk_0, chunk_1, etc.
            chunk_files = os.listdir(session_dir)
            chunk_files.sort(key=lambda x: int(x.split('_')[1]) if '_' in x else 0)
            print(f"Found chunk files: {chunk_files}")
            
            for chunk_file in chunk_files:
                chunk_path = os.path.join(session_dir, chunk_file)
                print(f"Processing chunk: {chunk_path}")
                with open(chunk_path, "rb") as chunk_file_handle:
                    assembled_file.write(chunk_file_handle.read())
        
        print(f"File assembled at: {assembled_file_path}")
        file_size = os.path.getsize(assembled_file_path)
        print(f"Assembled file size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")

        # --- Start Transcription Logic (using Google's built-in audio processing) ---
        print("Starting transcription with Google Speech-to-Text...")
        try:
            transcript = process_audio_with_google_directly(assembled_file_path)
            print(f"Transcription completed. Result: '{transcript}' (length: {len(transcript)})")
        except Exception as transcription_error:
            print(f"TRANSCRIPTION ERROR: {transcription_error}")
            print(f"Error type: {type(transcription_error).__name__}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            raise transcription_error
        # --- End Transcription Logic ---

        if transcript and transcript.strip():
            print(f"Transcription successful! Length: {len(transcript)} characters")
            print(f"Transcript preview: {transcript[:200]}...")
            # Send to n8n
            try:
                requests.post(N8N_WEBHOOK_URL, json={"transcript": transcript, "originalFileName": original_filename})
                print("Successfully sent to n8n webhook")
            except Exception as e:
                print(f"Error sending to n8n: {e}")
            return JSONResponse(content={"transcript": transcript})
        else:
            print("No transcription found - transcript is empty or only whitespace")
            # Still send to n8n for tracking
            try:
                requests.post(N8N_WEBHOOK_URL, json={"transcript": "No speech detected", "originalFileName": original_filename, "status": "no_speech"})
                print("Sent 'no speech' notification to n8n webhook")
            except Exception as e:
                print(f"Error sending to n8n: {e}")
            
            return JSONResponse(content={
                "transcript": "",
                "message": "No speech detected in the audio file. This could happen if:\n• The audio is too quiet or unclear\n• The file contains only music or background noise\n• The speech is in a language not supported\n• The audio quality is too poor for recognition\n\nTry with a clearer audio file containing clear speech.",
                "status": "no_speech_detected"
            }, status_code=200)

    except Exception as e:
        print(f"MAJOR ERROR in transcribe_chunks: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return JSONResponse(content={"error": f"Transcription failed: {str(e)}"}, status_code=500)
    finally:
        # Clean up session directory and assembled file
        try:
            if os.path.exists(session_dir):
                import shutil
                shutil.rmtree(session_dir)
                print(f"Cleaned up session directory: {session_dir}")
        except Exception as cleanup_error:
            print(f"Error cleaning up session directory: {cleanup_error}")
            
        try:
            if os.path.exists(assembled_file_path):
                os.remove(assembled_file_path)
                print(f"Cleaned up assembled file: {assembled_file_path}")
        except Exception as cleanup_error:
            print(f"Error cleaning up assembled file: {cleanup_error}")
            
        try:
            if session_id in upload_sessions:
                del upload_sessions[session_id]
                print(f"Cleaned up session from memory: {session_id}")
        except Exception as cleanup_error:
            print(f"Error cleaning up session from memory: {cleanup_error}")
            
        print(f"=== TRANSCRIBE CHUNKS END ===")

def chunk_audio_simple(input_path: str, max_size_mb: int = 3) -> list:
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
    Process audio file directly with Google Speech-to-Text.
    Automatically handles short vs long audio files.
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
        
        # Check file duration/size to determine if we need long-running recognition
        file_size_mb = len(content) / (1024 * 1024)
        print(f"File size: {file_size_mb:.2f} MB")
        
        # Be very conservative - if file is larger than 5MB, use chunking approach
        # This helps avoid the "Sync input too long" error since we can't easily determine actual duration
        if file_size_mb > 5:
            print("File size > 5MB, using chunking approach to avoid sync limits...")
            return process_large_audio_file(file_path, file_extension)
        
        # Try different configurations based on file type
        configs_to_try = []
        
        # Create base configurations for different formats
        base_configs = []
        
        if file_extension in ['.mp3']:
            base_configs.extend([
                {"encoding": speech.RecognitionConfig.AudioEncoding.MP3, "sample_rate_hertz": 44100},
                {"encoding": speech.RecognitionConfig.AudioEncoding.MP3, "sample_rate_hertz": 22050},
                {"encoding": speech.RecognitionConfig.AudioEncoding.MP3, "sample_rate_hertz": 16000},
                {"encoding": speech.RecognitionConfig.AudioEncoding.MP3},  # No sample rate - let Google detect
            ])
        elif file_extension in ['.wav']:
            base_configs.extend([
                {"encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16, "sample_rate_hertz": 44100},
                {"encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16, "sample_rate_hertz": 22050},
                {"encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16, "sample_rate_hertz": 16000},
            ])
        elif file_extension in ['.flac']:
            base_configs.extend([
                {"encoding": speech.RecognitionConfig.AudioEncoding.FLAC, "sample_rate_hertz": 44100},
                {"encoding": speech.RecognitionConfig.AudioEncoding.FLAC, "sample_rate_hertz": 22050},
                {"encoding": speech.RecognitionConfig.AudioEncoding.FLAC, "sample_rate_hertz": 16000},
            ])
        else:
            # For other formats (including video), try MP3 and LINEAR16
            base_configs.extend([
                {"encoding": speech.RecognitionConfig.AudioEncoding.MP3, "sample_rate_hertz": 44100},
                {"encoding": speech.RecognitionConfig.AudioEncoding.MP3},
                {"encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16, "sample_rate_hertz": 44100},
                {"encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16, "sample_rate_hertz": 16000},
            ])
        
        # Try with multiple languages
        languages_to_try = ["en-US", "en-GB"]
        
        for base_config in base_configs:
            for language in languages_to_try:
                config_dict = {
                    **base_config,
                    "language_code": language,
                    "enable_automatic_punctuation": True,
                }
                configs_to_try.append(config_dict)
                
        print(f"Total configurations to try: {len(configs_to_try)}")
        
        # Try each configuration until one works
        for i, config_dict in enumerate(configs_to_try):
            try:
                encoding_name = config_dict['encoding'].name if hasattr(config_dict['encoding'], 'name') else str(config_dict['encoding'])
                sample_rate = config_dict.get('sample_rate_hertz', 'auto')
                language = config_dict.get('language_code', 'unknown')
                print(f"Trying configuration {i+1}: {encoding_name} @ {sample_rate}Hz, language: {language}")
                
                config = speech.RecognitionConfig(**config_dict)
                
                # Use standard recognition for smaller files
                print("Using standard recognition...")
                response = client.recognize(config=config, audio=audio)
                
                print(f"Google API response received with {len(response.results)} results")
                
                transcripts = []
                for j, result in enumerate(response.results):
                    print(f"Processing result {j+1}:")
                    print(f"  - Alternatives count: {len(result.alternatives)}")
                    
                    if result.alternatives:
                        for k, alternative in enumerate(result.alternatives):
                            transcript_text = alternative.transcript
                            confidence = alternative.confidence if hasattr(alternative, 'confidence') else 'N/A'
                            print(f"  - Alternative {k+1}: '{transcript_text}' (confidence: {confidence})")
                            if k == 0:  # Only take the first (best) alternative
                                transcripts.append(transcript_text)
                    else:
                        print(f"  - No alternatives found in result {j+1}")
                
                final_transcript = " ".join(transcripts)
                print(f"Final transcript: '{final_transcript}' (length: {len(final_transcript)})")
                
                # If we got an empty result, this config worked but found no speech
                if len(final_transcript.strip()) == 0:
                    print(f"Configuration {i+1} worked but found no speech content")
                    # Try next configuration instead of returning empty
                    continue
                
                return final_transcript
                    
            except Exception as config_error:
                error_message = str(config_error)
                print(f"Configuration {i+1} failed: {error_message}")
                
                # Check if this is the "too long" error
                if "Sync input too long" in error_message or "too long" in error_message.lower():
                    print("Audio is too long for sync recognition, switching to chunking approach...")
                    return process_large_audio_file(file_path, file_extension)
                
                if i == len(configs_to_try) - 1:  # Last configuration
                    print("All configurations failed")
                    # If all configs failed, try the chunking approach as last resort
                    print("Trying chunking approach as fallback...")
                    return process_large_audio_file(file_path, file_extension)
                continue
        
        return ""  # No speech detected
            
    except Exception as e:
        error_message = str(e)
        print(f"Error processing audio with Google: {error_message}")
        
        # Check if this is the "too long" error
        if "Sync input too long" in error_message or "too long" in error_message.lower():
            print("Audio is too long, trying chunking approach...")
            return process_large_audio_file(file_path, file_extension)
        
        raise e

def process_large_audio_file(file_path: str, file_extension: str) -> str:
    """
    Process large audio files by splitting them into smaller chunks.
    """
    try:
        print("Processing large audio file with chunking...")
        
        # Split the file into very small chunks to ensure they're under 1 minute
        chunks = chunk_audio_simple(file_path, max_size_mb=3)  # Very small chunks for safety
        all_transcripts = []
        
        client = speech.SpeechClient()
        
        # Determine best config for this file type - use simpler configs for reliability
        if file_extension in ['.mp3']:
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                language_code="en-US",
                enable_automatic_punctuation=True,
            )
        elif file_extension in ['.wav']:
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                language_code="en-US",
                enable_automatic_punctuation=True,
            )
        else:
            # Default to MP3 for video files and others - don't specify sample rate
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                language_code="en-US",
                enable_automatic_punctuation=True,
            )
        
        successful_chunks = 0
        
        for i, chunk_path in enumerate(chunks):
            try:
                print(f"Processing chunk {i+1}/{len(chunks)}...")
                
                # Check chunk size before processing
                chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
                print(f"Chunk {i+1} size: {chunk_size_mb:.2f} MB")
                
                with io.open(chunk_path, "rb") as chunk_file:
                    chunk_content = chunk_file.read()
                
                chunk_audio = speech.RecognitionAudio(content=chunk_content)
                response = client.recognize(config=config, audio=chunk_audio)
                
                chunk_transcripts = []
                for result in response.results:
                    if result.alternatives:
                        transcript_text = result.alternatives[0].transcript
                        print(f"Chunk {i+1} transcript: {transcript_text}")
                        chunk_transcripts.append(transcript_text)
                
                if chunk_transcripts:
                    all_transcripts.extend(chunk_transcripts)
                    successful_chunks += 1
                else:
                    print(f"Chunk {i+1}: No speech detected")
                
                # Clean up chunk file
                os.remove(chunk_path)
                
            except Exception as chunk_error:
                error_msg = str(chunk_error)
                print(f"Error processing chunk {i+1}: {error_msg}")
                
                # If this chunk is still too long, we have a problem
                if "Sync input too long" in error_msg:
                    print(f"Chunk {i+1} is still too long! Skipping...")
                
                # Clean up and continue with other chunks
                try:
                    os.remove(chunk_path)
                except:
                    pass
                continue
        
        final_transcript = " ".join(all_transcripts)
        print(f"Combined transcript from {successful_chunks}/{len(chunks)} successful chunks: {len(final_transcript)} characters")
        
        if successful_chunks == 0:
            return ""  # No chunks were successfully processed
        
        return final_transcript
        
    except Exception as e:
        print(f"Error in process_large_audio_file: {e}")
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
