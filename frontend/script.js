document.getElementById('transcribeBtn').addEventListener('click', async () => {
    const audioFile = document.getElementById('audioFile').files[0];
    const transcriptionDiv = document.getElementById('transcription');
    const transcribeBtn = document.getElementById('transcribeBtn');
    const progressBar = document.getElementById('progressBar');
    const progressContainer = document.getElementById('progressContainer');

    if (!audioFile) {
        transcriptionDiv.textContent = 'Please select a file.';
        return;
    }

    // --- Frontend Chunking Logic ---
    const CHUNK_SIZE = 4 * 1024 * 1024; // 4 MB chunks
    const totalChunks = Math.ceil(audioFile.size / CHUNK_SIZE);
    const sessionId = new Date().getTime().toString() + Math.random().toString(36).substring(2);
    const backendUrl = 'https://lamont-audio-upload.vercel.app';

    // --- UI Setup ---
    transcribeBtn.disabled = true;
    transcribeBtn.textContent = 'Uploading...';
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    transcriptionDiv.textContent = `Starting upload of ${totalChunks} chunks...`;

    try {
        // 1. Upload all chunks
        for (let i = 0; i < totalChunks; i++) {
            const start = i * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, audioFile.size);
            const chunk = audioFile.slice(start, end);

            const formData = new FormData();
            formData.append('file', chunk, audioFile.name);
            formData.append('session_id', sessionId);
            formData.append('chunk_index', i);
            formData.append('total_chunks', totalChunks);

            const response = await fetch(`${backendUrl}/upload_chunk`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Chunk upload failed. Server responded with ${response.status}`);
            }
            
            // Update progress bar
            const progress = Math.round(((i + 1) / totalChunks) * 100);
            progressBar.style.width = `${progress}%`;
            transcriptionDiv.textContent = `Uploaded chunk ${i + 1} of ${totalChunks}...`;
        }

        // 2. Signal backend to assemble and transcribe
        transcribeBtn.textContent = 'Transcribing...';
        transcriptionDiv.textContent = 'File upload complete. Assembling and transcribing on the server...';
        
        const transcribeResponse = await fetch(`${backendUrl}/transcribe_chunks?session_id=${sessionId}&original_filename=${encodeURIComponent(audioFile.name)}`, {
            method: 'POST',
        });

        if (transcribeResponse.ok) {
            const data = await transcribeResponse.json();
            console.log('Transcription response:', data);
            
            if (data.transcript && data.transcript.trim()) {
                transcriptionDiv.textContent = data.transcript;
            } else {
                transcriptionDiv.textContent = 'Transcription completed but no text was detected. This could happen if:\n• The audio is too quiet or unclear\n• The file contains no speech\n• The audio format is not compatible\n\nTry with a clearer audio file or check that the file contains speech.';
            }
        } else {
            console.error('Transcription failed:', transcribeResponse.status);
            const errorData = await transcribeResponse.json();
            console.error('Error data:', errorData);
            throw new Error(errorData.error || 'Transcription failed.');
        }

    } catch (error) {
        transcriptionDiv.textContent = `Error: ${error.message}`;
    } finally {
        // --- UI Cleanup ---
        transcribeBtn.disabled = false;
        transcribeBtn.textContent = 'Transcribe';
        progressContainer.style.display = 'none';
        progressBar.style.width = '0%';
    }
});




