# Gemini Transcribe Reel - Web UI

A minimal web interface for the gemini-transcribe-reel script.

## Quick Start

1. Install Flask:
```bash
pip install flask
```

2. Run the web server:
```bash
python app.py
```

3. Open your browser to: `http://127.0.0.1:5000`

4. Paste a reel URL and click "Transcribe"

## Design Philosophy

The UI embodies the same minimalist, zero-friction philosophy as the CLI:

- **Single input field** - Paste URL only
- **Single action button** - "Transcribe"
- **Instant feedback** - Loading state, errors in red, transcripts in a readable box
- **No extras** - No settings, no accounts, no history, no branding
- **Transient sessions** - Every transcription is independent

## Error Handling

All error states from the CLI are preserved:
- Invalid URLs
- Missing API key
- Network failures
- Download failures
- Rate limits
- API errors

Errors display in red text immediately below the button.

## Technical Notes

- Uses native HTML form elements
- System default fonts
- Minimal CSS for clarity only
- JavaScript handles async transcription
- Enter key submits form
- Auto-focus on input field
- Scrollable transcript display for long results
