from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import assemblyai as aai
import os
import tempfile
import requests

# --- Assembly AI Setup ---
aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

app = FastAPI()

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# --- n8n Webhook Configuration ---
N8N_WEBHOOK_URL = "https://n8n-service-3446.onrender.com/webhook/6da7c0ce-6f81-4fd7-a667-3784b4159bec"

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Direct transcription endpoint using Assembly AI.
    Handles any audio/video format, any size automatically.
    """
    print(f"Received file: {file.filename} ({file.content_type})")
    
    # Create a temporary file with the correct extension
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'tmp'
    
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
            
        print(f"Saved to temporary file: {temp_path}")
        print(f"File size: {len(content)} bytes ({len(content)/(1024*1024):.2f} MB)")
        
        # Initialize Assembly AI transcriber
        transcriber = aai.Transcriber()
        
        # Configure transcription (optional - Assembly AI auto-detects most things)
        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.best,  # Use the best model
            language_detection=True,  # Auto-detect language
            punctuate=True,  # Add punctuation
            format_text=True  # Format the text nicely
        )
        
        print("Starting transcription with Assembly AI...")
        
        # Transcribe the audio file
        transcript = transcriber.transcribe(temp_path, config=config)
        
        print(f"Transcription status: {transcript.status}")
        
        # Check if transcription was successful
        if transcript.status == aai.TranscriptStatus.error:
            error_msg = f"Assembly AI transcription failed: {transcript.error}"
            print(error_msg)
            
            # Send error to n8n
            try:
                requests.post(N8N_WEBHOOK_URL, json={
                    "transcript": "Error occurred during transcription", 
                    "originalFileName": file.filename, 
                    "status": "error",
                    "error": transcript.error
                })
            except Exception as e:
                print(f"Error sending to n8n: {e}")
            
            return JSONResponse(
                content={"error": error_msg}, 
                status_code=500
            )
        
        # Get the transcribed text
        transcribed_text = transcript.text
        
        if transcribed_text and transcribed_text.strip():
            print(f"Transcription successful! Length: {len(transcribed_text)} characters")
            print(f"Transcript preview: {transcribed_text[:200]}...")
            
            # Send to n8n
            try:
                requests.post(N8N_WEBHOOK_URL, json={
                    "transcript": transcribed_text, 
                    "originalFileName": file.filename,
                    "confidence": getattr(transcript, 'confidence', None),
                    "language": getattr(transcript, 'language_code', 'auto-detected')
                })
                print("Successfully sent to n8n webhook")
            except Exception as e:
                print(f"Error sending to n8n: {e}")
            
            return JSONResponse(content={"transcript": transcribed_text})
            
        else:
            print("No speech detected in the audio file")
            
            # Send to n8n
            try:
                requests.post(N8N_WEBHOOK_URL, json={
                    "transcript": "No speech detected", 
                    "originalFileName": file.filename, 
                    "status": "no_speech"
                })
            except Exception as e:
                print(f"Error sending to n8n: {e}")
            
            return JSONResponse(content={
                "transcript": "",
                "message": "No speech detected in the audio file. This could happen if:\n• The file contains only music or background noise\n• The audio is too quiet\n• The file is corrupted\n• The language is not supported\n\nTry with a file containing clear speech.",
                "status": "no_speech_detected"
            })
            
    except Exception as e:
        error_msg = f"Transcription failed: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        # Send error to n8n
        try:
            requests.post(N8N_WEBHOOK_URL, json={
                "transcript": "Error occurred during transcription", 
                "originalFileName": file.filename, 
                "status": "error",
                "error": str(e)
            })
        except Exception as webhook_error:
            print(f"Error sending to n8n: {webhook_error}")
        
        return JSONResponse(
            content={"error": error_msg}, 
            status_code=500
        )
        
    finally:
        # Clean up temporary file
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
                print(f"Cleaned up temporary file: {temp_path}")
        except Exception as cleanup_error:
            print(f"Error cleaning up temporary file: {cleanup_error}")

# --- Health check endpoint ---
@app.get("/")
async def root():
    return {"message": "Audio Transcriber API with Assembly AI", "status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
