document.getEle        // IMPORTANT: Replace with your deployed Vercel backend URL
        const backendUrl = 'https://audio-transcriber-app-backend.vercel.app/transcribe';
        
        const response = await fetch(backendUrl, {
            method: 'POST',
            body: formData,
        });d('transcribeBtn').addEventListener('click', async () => {
    const audioFile = document.getElementById('audioFile').files[0];
    const transcriptionDiv = document.getElementById('transcription');

    if (!audioFile) {
        transcriptionDiv.textContent = 'Please select an audio file.';
        return;
    }

    const formData = new FormData();
    formData.append('file', audioFile);

    transcriptionDiv.textContent = 'Transcribing...';

    try {
        // IMPORTANT: Replace with your deployed Vercel backend URL
        const backendUrl = 'https://lamont-audio-upload.vercel.app/transcribe/';
        
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
    }
});




