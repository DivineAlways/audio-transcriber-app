// Assembly AI Configuration - Direct Frontend Integration
const ASSEMBLYAI_API_KEY = '9563dac8b85846029bd3921edf0d8509'; // You'll need to replace this
const N8N_WEBHOOK_URL = "https://innergcomplete.app.n8n.cloud/webhook/c0b2e4e8-c7b1-41c1-8e6e-db02f612b80d";

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const transcribeBtn = document.getElementById('transcribeBtn');
const progressContainer = document.getElementById('progressContainer');
const progressBar = document.getElementById('progressBar');
const statusText = document.getElementById('statusText');
const result = document.getElementById('result');
const transcriptText = document.getElementById('transcriptText');
const copyBtn = document.getElementById('copyBtn');

let selectedFile = null;

// Event Listeners
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', handleDragOver);
dropZone.addEventListener('drop', handleDrop);
fileInput.addEventListener('change', handleFileSelect);
transcribeBtn.addEventListener('click', handleTranscribe);
copyBtn.addEventListener('click', handleCopy);

// Drag and Drop Handlers
function handleDragOver(e) {
    e.preventDefault();
    dropZone.classList.add('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

// File Selection Handler
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

// Handle File
function handleFile(file) {
    // Assembly AI supports up to 512MB - no more Vercel limits!
    const maxSize = 512 * 1024 * 1024; // 512MB in bytes
    
    if (file.size > maxSize) {
        showError(`File is too large. Maximum file size is ${formatFileSize(maxSize)}.`);
        return;
    }
    
    selectedFile = file;
    
    // Update UI
    dropZone.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 24px;">📄</span>
            <div>
                <div style="font-weight: bold;">${file.name}</div>
                <div style="color: #666; font-size: 14px;">
                    ${formatFileSize(file.size)} • Ready to transcribe
                </div>
            </div>
        </div>
    `;
    
    transcribeBtn.disabled = false;
    transcribeBtn.textContent = 'Start Transcription';
    
    // Clear any previous results
    result.style.display = 'none';
    progressContainer.style.display = 'none';
}

// Format File Size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Handle Transcription - Direct Assembly AI REST API Integration
async function handleTranscribe() {
    if (!selectedFile) {
        showError('Please select a file first.');
        return;
    }

    // Check if API key is set
    if (ASSEMBLYAI_API_KEY === 'Assembly_API_Key' || ASSEMBLYAI_API_KEY === 'YOUR_ASSEMBLYAI_API_KEY_HERE') {
        showError('Please set your Assembly AI API key in the script.js file.');
        return;
    }
    
    // Update UI
    transcribeBtn.disabled = true;
    transcribeBtn.textContent = 'Transcribing...';
    progressContainer.style.display = 'block';
    result.style.display = 'none';
    
    updateStatus('Uploading file to Assembly AI...');
    updateProgress(10);
    
    try {
        // Step 1: Upload the file to Assembly AI
        updateStatus('Uploading file...');
        const formData = new FormData();
        formData.append('audio', selectedFile);
        
        const uploadResponse = await fetch('https://api.assemblyai.com/v2/upload', {
            method: 'POST',
            headers: {
                'Authorization': ASSEMBLYAI_API_KEY
            },
            body: formData
        });
        
        if (!uploadResponse.ok) {
            throw new Error(`Upload failed: ${uploadResponse.status} ${uploadResponse.statusText}`);
        }
        
        const uploadData = await uploadResponse.json();
        const audioUrl = uploadData.upload_url;
        
        updateProgress(30);
        updateStatus('File uploaded. Starting transcription...');
        
        // Step 2: Start transcription
        const transcriptRequest = {
            audio_url: audioUrl,
            speaker_labels: true,
            punctuate: true,
            format_text: true,
            language_detection: true
        };
        
        const transcriptResponse = await fetch('https://api.assemblyai.com/v2/transcript', {
            method: 'POST',
            headers: {
                'Authorization': ASSEMBLYAI_API_KEY,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(transcriptRequest)
        });
        
        if (!transcriptResponse.ok) {
            throw new Error(`Transcription request failed: ${transcriptResponse.status} ${transcriptResponse.statusText}`);
        }
        
        const transcriptData = await transcriptResponse.json();
        const transcriptId = transcriptData.id;
        
        updateProgress(40);
        updateStatus('Transcription in progress...');
        
        // Step 3: Poll for completion
        let transcript;
        let attempts = 0;
        const maxAttempts = 60; // 5 minutes max
        
        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
            
            const statusResponse = await fetch(`https://api.assemblyai.com/v2/transcript/${transcriptId}`, {
                headers: {
                    'Authorization': ASSEMBLYAI_API_KEY
                }
            });
            
            if (!statusResponse.ok) {
                throw new Error(`Status check failed: ${statusResponse.status} ${statusResponse.statusText}`);
            }
            
            transcript = await statusResponse.json();
            
            if (transcript.status === 'completed') {
                break;
            } else if (transcript.status === 'error') {
                throw new Error(`Assembly AI transcription error: ${transcript.error}`);
            }
            
            attempts++;
            const progress = 40 + (attempts / maxAttempts) * 50; // Progress from 40% to 90%
            updateProgress(Math.min(progress, 90));
            updateStatus(`Transcription in progress... (${attempts * 5}s)`);
        }
        
        if (attempts >= maxAttempts) {
            throw new Error('Transcription timed out. Please try again with a shorter file.');
        }
        
        updateProgress(95);
        updateStatus('Processing results...');
        
        const transcriptText = transcript.text;
        
        if (transcriptText && transcriptText.trim()) {
            updateStatus('Sending to n8n webhook...');
            
            // Send transcript to n8n webhook
            try {
                await fetch(N8N_WEBHOOK_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        transcript: transcriptText,
                        originalFileName: selectedFile.name,
                        confidence: transcript.confidence || null,
                        language: transcript.language_code || 'auto-detected',
                        source: 'frontend-direct',
                        assemblyai_id: transcriptId
                    })
                });
                console.log('Successfully sent to n8n webhook');
            } catch (webhookError) {
                console.error('Error sending to n8n:', webhookError);
                // Don't throw error - still show transcript to user
            }
            
            updateProgress(100);
            updateStatus('Transcription complete!');
            displayResult(transcriptText);
            
        } else {
            updateProgress(100);
            updateStatus('No speech detected');
            
            // Send no speech result to webhook
            try {
                await fetch(N8N_WEBHOOK_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        transcript: "No speech detected",
                        originalFileName: selectedFile.name,
                        status: "no_speech",
                        source: 'frontend-direct'
                    })
                });
            } catch (webhookError) {
                console.error('Error sending to n8n:', webhookError);
            }
            
            showError('No speech detected in the audio file. This could happen if:\n• The file contains only music or background noise\n• The audio is too quiet\n• The file is corrupted\n• The language is not supported\n\nTry with a file containing clear speech.');
        }
        
    } catch (error) {
        console.error('Transcription error:', error);
        updateProgress(100);
        showError(`Transcription failed: ${error.message}`);
        
        // Send error to webhook
        try {
            await fetch(N8N_WEBHOOK_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    transcript: "Error occurred during transcription",
                    originalFileName: selectedFile.name,
                    status: "error",
                    error: error.message,
                    source: 'frontend-direct'
                })
            });
        } catch (webhookError) {
            console.error('Error sending to n8n:', webhookError);
        }
        
    } finally {
        // Reset UI
        transcribeBtn.disabled = false;
        transcribeBtn.textContent = 'Start Transcription';
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 2000);
    }
}

// Update Progress
function updateProgress(percent) {
    progressBar.style.width = `${percent}%`;
}

// Update Status
function updateStatus(message) {
    statusText.textContent = message;
}

// Display Result
function displayResult(transcript) {
    transcriptText.textContent = transcript;
    result.style.display = 'block';
    
    // Scroll to result
    result.scrollIntoView({ behavior: 'smooth' });
}

// Show Error
function showError(message) {
    updateStatus(`Error: ${message}`);
    progressBar.style.backgroundColor = '#ef4444';
    
    // Reset progress bar color after 3 seconds
    setTimeout(() => {
        progressBar.style.backgroundColor = '#3b82f6';
    }, 3000);
}

// Copy to Clipboard
function handleCopy() {
    const text = transcriptText.textContent;
    if (text) {
        navigator.clipboard.writeText(text).then(() => {
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.textContent = 'Copy to Clipboard';
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            showError('Failed to copy text to clipboard');
        });
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Audio Transcriber App initialized with Assembly AI direct integration');
    console.log('N8N Webhook URL:', N8N_WEBHOOK_URL);
    
    // Remove dragover class when dragging leaves the drop zone
    dropZone.addEventListener('dragleave', (e) => {
        if (!dropZone.contains(e.relatedTarget)) {
            dropZone.classList.remove('dragover');
        }
    });
});




