# Audio Transcriber - Cloud Run Deployment

This is a web application that provides audio and video transcription using Assembly AI's API directly from the browser.

## Local Development

1. Open `index.html` in a web browser
2. Make sure to update the API keys in `script.js` before deployment

## Docker Build and Run

```bash
# Build the Docker image
docker build -t audio-transcriber .

# Run locally
docker run -p 8080:8080 audio-transcriber
```

## Deploy to Google Cloud Run

### Prerequisites
- Google Cloud SDK installed and configured
- Docker installed
- A Google Cloud project with Cloud Run API enabled

### Deployment Steps

1. **Build and push to Google Container Registry:**
```bash
# Set your project ID
export PROJECT_ID=your-project-id

# Build and tag the image
docker build -t gcr.io/$PROJECT_ID/audio-transcriber .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/audio-transcriber
```

2. **Deploy to Cloud Run:**
```bash
gcloud run deploy audio-transcriber \
  --image gcr.io/$PROJECT_ID/audio-transcriber \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1
```

### Alternative: Deploy directly from source

```bash
gcloud run deploy audio-transcriber \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1
```

## Configuration

Before deploying, make sure to update the following in `script.js`:

1. **Assembly AI API Key**: Replace the placeholder with your actual API key
2. **n8n Webhook URL**: Replace with your actual n8n webhook URL

```javascript
const ASSEMBLYAI_API_KEY = 'YOUR_ASSEMBLYAI_API_KEY_HERE';
const N8N_WEBHOOK_URL = "https://your-n8n-webhook-url";
```

## Features

- Upload audio/video files up to 512MB
- Direct browser-to-Assembly AI integration
- Real-time transcription progress
- Copy transcription results to clipboard
- Responsive design with drag-and-drop interface
- Health check endpoint at `/health`

## Architecture

- **Frontend**: Pure HTML/CSS/JavaScript served by nginx
- **Container**: Alpine Linux with nginx
- **Cloud Run**: Serverless container platform
- **Assembly AI**: External transcription service
- **n8n**: Webhook integration for processing results

## Security Considerations

- API keys are exposed in frontend code (consider environment variables for production)
- CORS is handled by Assembly AI
- Basic security headers included in nginx configuration
- Content Security Policy configured

## Monitoring

Cloud Run provides built-in monitoring. Check the following:
- Container logs: `gcloud logging read "resource.type=cloud_run_revision"`
- Metrics in Google Cloud Console
- Health check endpoint: `https://your-service-url/health`
