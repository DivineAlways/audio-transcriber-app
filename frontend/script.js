// Backend API URL
const API_URL = 'https://doc-ai-backend.vercel.app';

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
    // Check file size (Assembly AI supports up to 512MB)
    const maxSize = 512 * 1024 * 1024; // 512MB in bytes
    
    if (file.size > maxSize) {
        showError('File is too large. Maximum file size is 512MB.');
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

// Handle Transcription
async function handleTranscribe() {
    if (!selectedFile) {
        showError('Please select a file first.');
        return;
    }
    
    // Update UI
    transcribeBtn.disabled = true;
    transcribeBtn.textContent = 'Transcribing...';
    progressContainer.style.display = 'block';
    result.style.display = 'none';
    
    updateStatus('Uploading file to Assembly AI...');
    updateProgress(0);
    
    try {
        // Create FormData for the upload
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        // Upload and transcribe with Assembly AI
        const response = await fetch(`${API_URL}/transcribe`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        updateProgress(100);
        updateStatus('Transcription complete!');
        
        const data = await response.json();
        
        if (data.transcript && data.transcript.trim()) {
            displayResult(data.transcript);
        } else {
            // Handle no speech detected
            const message = data.message || 'No speech detected in the audio file.';
            showError(message);
        }
        
    } catch (error) {
        console.error('Transcription error:', error);
        showError(`Transcription failed: ${error.message}`);
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
    console.log('Audio Transcriber App initialized');
    console.log('API URL:', API_URL);
    
    // Remove dragover class when dragging leaves the drop zone
    dropZone.addEventListener('dragleave', (e) => {
        if (!dropZone.contains(e.relatedTarget)) {
            dropZone.classList.remove('dragover');
        }
    });
});




