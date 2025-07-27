document.getElementById('transcribeBtn').addEventListener('click', async () => {
    const audioFile = document.getElementById('audioFile').files[0];
    const transcriptionDiv = document.getElementById('transcription');
    const transcribeBtn = document.getElementById('transcribeBtn');

    if (!audioFile) {
        transcriptionDiv.textContent = 'Please select an audio file.';
        return;
    }

    const formData = new FormData();
    formData.append('file', audioFile);

    // Disable button and show loading text
    transcribeBtn.disabled = true;
    transcribeBtn.textContent = 'Transcribing...';
    transcriptionDiv.textContent = 'Processing and transcribing your audio. This may take a moment...';

    try {
        // Use the correct backend URL provided by the user
        const backendUrl = 'https://lamont-audio-upload.vercel.app/transcribe';
        
        const response = await fetch(backendUrl, {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const data = await response.json();
            transcriptionDiv.textContent = data.transcript;
        } else {
            const errorData = await response.json();
            transcriptionDiv.textContent = `Error: ${errorData.error || 'An unknown error occurred.'}`;
        }
    } catch (error) {
        transcriptionDiv.textContent = `Error: ${error.message}`;
    } finally {
        // Re-enable the button
        transcribeBtn.disabled = false;
        transcribeBtn.textContent = 'Transcribe';
    }
});




