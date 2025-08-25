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

const textInput = document.getElementById('textInput');
const generateBtn = document.getElementById('generateBtn');
const generationResult = document.getElementById('generationResult');
const generatedFilesText = document.getElementById('generatedFilesText');

let selectedFile = null;

// --- Backend API Base URL ---
const API_BASE_URL = 'https://audio-transcriber-596584619630.us-central1.run.app';

// --- Event Listeners ---
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', handleDragOver);
dropZone.addEventListener('drop', handleDrop);
fileInput.addEventListener('change', handleFileSelect);
transcribeBtn.addEventListener('click', handleTranscribe);
copyBtn.addEventListener('click', handleCopy);
generateBtn.addEventListener('click', handleGenerateFromText);

// --- Drag and Drop Handlers ---
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

// --- File Handling ---
function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFile(file) {
    const maxSize = 512 * 1024 * 1024; // 512MB
    if (file.size > maxSize) {
        showError(`File is too large. Maximum file size is ${formatFileSize(maxSize)}.`);
        return;
    }
    selectedFile = file;
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
    transcribeBtn.textContent = 'Start Transcription & Deploy';
    result.style.display = 'none';
    progressContainer.style.display = 'none';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// --- Core Logic Handlers ---
async function handleTranscribe() {
    if (!selectedFile) {
        showError('Please select a file first.');
        return;
    }
    const formData = new FormData();
    formData.append('file', selectedFile);

    // Setup UI for processing
    transcribeBtn.disabled = true;
    transcribeBtn.textContent = 'Processing...';
    progressContainer.style.display = 'block';
    result.style.display = 'none';
    updateStatus('Uploading and processing... this may take a few minutes.');
    updateProgress(10);

    try {
        const response = await fetch(`${API_BASE_URL}/transcribe`, {
            method: 'POST',
            body: formData,
        });

        updateProgress(100);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Server returned an unreadable error' }));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.repo_url && data.pages_url) {
            updateStatus('Deployment Complete!');
            displaySuccessLinks(data.repo_url, data.pages_url);
        } else {
            throw new Error(data.error || 'Invalid response from server.');
        }

    } catch (error) {
        console.error('Processing error:', error);
        showError(`Failed: ${error.message}`);
    } finally {
        transcribeBtn.disabled = false;
        transcribeBtn.textContent = 'Start Transcription & Deploy';
    }
}

async function handleGenerateFromText() {
    const transcript = textInput.value;
    if (!transcript || !transcript.trim()) {
        alert('Please enter a project description.');
        return;
    }

    // Setup UI for processing
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating...';
    generationResult.style.display = 'none';

    const body = { transcript: transcript };

    try {
        const response = await fetch(`${API_BASE_URL}/generate-from-text`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Server returned an unreadable error' }));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.repo_url && data.pages_url) {
            generationResult.style.display = 'block';
            generatedFilesText.innerHTML = `
                <p><strong>Project created and deployed!</strong></p>
                <p><strong>GitHub Repository:</strong> <a href="${data.repo_url}" target="_blank">${data.repo_url}</a></p>
                <p><strong>Live GitHub Pages Site:</strong> <a href="${data.pages_url}" target="_blank">${data.pages_url}</a></p>
                <p><small>(Note: It may take a minute or two for the GitHub Pages site to become active.)</small></p>
            `;
        } else {
            throw new Error(data.error || 'Invalid response from server.');
        }

    } catch (error) {
        console.error('Generation error:', error);
        generationResult.style.display = 'block';
        generatedFilesText.innerHTML = `<p style="color: red;"><strong>Error:</strong> ${error.message}</p>`;
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Project';
    }
}


// --- UI Update Functions ---
function updateProgress(percent) {
    progressBar.style.width = `${percent}%`;
}

function updateStatus(message) {
    statusText.textContent = message;
}

function displaySuccessLinks(repoUrl, pagesUrl) {
    transcriptText.innerHTML = `
        <p><strong>Success! Your project has been generated and deployed.</strong></p>
        <p><strong>GitHub Repository:</strong> <a href="${repoUrl}" target="_blank">${repoUrl}</a></p>
        <p><strong>Live GitHub Pages Site:</strong> <a href="${pagesUrl}" target="_blank">${pagesUrl}</a></p>
        <p><small>(Note: It may take a minute or two for the GitHub Pages site to become active.)</small></p>
    `;
    result.style.display = 'block';
    result.scrollIntoView({ behavior: 'smooth' });
}

function displaySuccessMessage(message) {
    transcriptText.innerHTML = `<p><strong>${message}</strong></p>`;
    result.style.display = 'block';
    result.scrollIntoView({ behavior: 'smooth' });
}

function showError(message) {
    updateStatus(`Error: ${message}`);
    progressBar.style.backgroundColor = '#ef4444';
    setTimeout(() => {
        progressBar.style.backgroundColor = '#3b82f6';
    }, 3000);
}

function handleCopy() {
    const text = transcriptText.innerText; // Use innerText to get text content without HTML
    if (text) {
        navigator.clipboard.writeText(text).then(() => {
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.textContent = 'Copy Links';
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    }
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('Audio Transcriber & Project Generator Initialized');
    // Add tab switching logic
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    tabLinks.forEach(link => {
        link.addEventListener('click', () => {
            const tab = link.getAttribute('data-tab');
            
            tabLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            tabContents.forEach(content => {
                if (content.id === tab) {
                    content.style.display = 'block';
                } else {
                    content.style.display = 'none';
                }
            });
        });
    });
});



