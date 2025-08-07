# Frontend Audio Transcriber

A standalone web application that uses Assembly AI for audio and video transcription directly from the browser.

## Features

- **Direct Assembly AI Integration**: No backend server required
- **Large File Support**: Up to 512MB file uploads
- **Real-time Progress**: Live progress updates during transcription
- **Multiple Formats**: Supports all major audio and video formats
- **n8n Integration**: Automatically sends results to webhook
- **Copy to Clipboard**: Easy transcript copying

## Setup

### 🔐 Secure Configuration (Recommended)

1. **Get Assembly AI API Key**:

   - Go to [Assembly AI](https://www.assemblyai.com/)
   - Sign up for a free account
   - Copy your API key from the dashboard

2. **Configure API Keys Securely**:

   ```bash
   # Copy the configuration template
   cp config.example.js script-local.js

   # Edit script-local.js with your actual keys
   # This file is in .gitignore and won't be committed
   ```

3. **Update script.js**:

   - Replace `'YOUR_ASSEMBLYAI_API_KEY_HERE'` with your API key
   - Replace `'YOUR_N8N_WEBHOOK_URL_HERE'` with your webhook URL
   - **OR** use the script-local.js approach for development

4. **Deploy**:
   - Upload files to any web hosting service
   - Or serve locally with a simple HTTP server
   - **⚠️ For production**: Use environment variables or server-side proxy

### ⚡ Quick Setup (Development Only)

1. Open `script.js`
2. Replace placeholders with your actual credentials
3. **🚨 WARNING**: Never commit real API keys to version control!

## Files

- `index.html` - Main application interface
- `script.js` - Assembly AI integration and logic
- `styles.css` - Styling and responsive design

## Usage

1. Open `index.html` in a web browser
2. Drag and drop an audio/video file (up to 512MB)
3. Click "Start Transcription"
4. Wait for transcription to complete
5. Results are displayed and sent to n8n webhook

## Supported Formats

**Audio**: MP3, WAV, FLAC, M4A, AAC, OGG, OPUS, and more
**Video**: MP4, MOV, AVI, MKV, WebM, FLV, 3GP, and more

## Technical Details

- Uses Assembly AI REST API directly from browser
- No server-side dependencies
- Polling-based transcription status checking
- Comprehensive error handling
- CORS-compatible design

## Browser Compatibility

Works in all modern browsers that support:

- Fetch API
- File API
- FormData
- Async/Await

---

**Note**: This is a client-side only application. The Assembly AI API key is exposed in the frontend code, so only use this for internal/trusted environments or implement additional security measures for production use.
