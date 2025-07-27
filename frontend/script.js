document.getElementById('transcribeBtn').addEventListener('click', async () => {
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
        const response = await fetch('http://localhost:8000/transcribe/', {
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
