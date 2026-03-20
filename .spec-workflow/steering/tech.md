# Technical Architecture

## Technology Stack

| Layer        | Technology                | Purpose                                  |
|--------------|---------------------------|------------------------------------------|
| Language     | Python 3.10+              | Core runtime                             |
| AI / LLM    | Google Gemini API (`gemini-2.5-flash`) | Video transcription via file upload |
| Video DL     | yt-dlp                    | Download videos from Instagram, TikTok, Facebook |
| Video Proc   | FFmpeg                    | Compress videos exceeding 20 MB          |
| Web          | Flask                     | Lightweight web UI server                |
| Config       | python-dotenv             | Load `GEMINI_API_KEY` from `.env`        |
| Testing      | pytest + pytest-cov + pytest-mock | Unit tests with 100% coverage   |

## System Dependencies

- **FFmpeg** — required at runtime for video compression and audio extraction
- **yt-dlp** — required at runtime for video downloading (installed via pip or system package)

## Architecture Decisions

### Stateless, no-database design

There is no database. Each transcription request is self-contained: download → compress (if needed) → upload to Gemini → return text → delete temp files. This keeps deployment trivial and avoids data-retention concerns.

### Dual interface, shared core

`transcribe.py` contains all business logic. `app.py` is a thin Flask wrapper that calls into the same functions. This avoids duplication and ensures CLI and web UI behave identically.

### Error-code-driven control flow

Every failure mode maps to a specific exit code (1–7). Functions return `None` on failure and print errors to stderr, letting callers decide how to handle each case. The web layer translates these into JSON error responses.

### Temp file lifecycle

Videos are downloaded into Python `tempfile.TemporaryDirectory` contexts. The directory (and all contents) is automatically deleted when the context exits, even on exceptions. No orphaned files.

### Rate-limit awareness

Batch processing inserts a 4-second `time.sleep()` between requests to stay within the Gemini free tier (15 req/min). This is intentionally conservative.

### Video compression strategy

Videos larger than 20 MB are compressed using FFmpeg with a target bitrate calculated to produce ~18 MB output. This keeps uploads within the Gemini file-upload limit without user intervention.

## API Integration — Google Gemini

1. **Upload** — `genai.upload_file(path)` sends the video file to Google's file service.
2. **Poll** — The file transitions through `PROCESSING` → `ACTIVE`. Code polls every 2 seconds with a 60-second timeout.
3. **Generate** — `model.generate_content([file, prompt])` returns the transcription text.
4. **Cleanup** — `genai.delete_file(file.name)` removes the uploaded file from Google's servers.

### Free-tier limits

| Limit               | Value            |
|----------------------|------------------|
| Requests per minute  | 15               |
| Tokens per minute    | 1,000,000        |
| Requests per day     | 1,500            |

## Development Principles

1. **Minimal dependencies** — Only add a package if it solves a problem that can't be handled in a few lines of stdlib code.
2. **No silent failures** — Every error path prints a clear message to stderr and returns a distinct exit code.
3. **Mock everything external** — Tests never hit the network, the Gemini API, or the filesystem. All external calls are mocked.
4. **Cross-platform parity** — Core logic works identically on Windows, macOS, and Linux. Platform-specific setup is documented separately.
5. **Keep the web layer thin** — `app.py` should only translate HTTP ↔ function calls. No business logic in the web layer.

## Testing Strategy

- **Framework:** pytest with pytest-mock for patching and pytest-cov for coverage
- **Coverage target:** 100% of `transcribe.py`
- **Test count:** 48 tests across 13 test classes
- **Mocking approach:** All external dependencies (Gemini API, yt-dlp subprocess, socket, file I/O) are mocked
- **Run tests:** `pytest test_transcribe.py -v --cov=transcribe --cov-report=html`
- **Integration smoke tests:** `test.sh` exercises real error paths (network blocks, invalid URLs) against the live CLI

## Configuration

| Variable        | Source  | Required | Description                     |
|-----------------|---------|----------|---------------------------------|
| `GEMINI_API_KEY`| `.env`  | Yes      | Google Gemini API key           |
| `--debug`       | CLI arg | No       | Enable debug output to stderr   |
| `--file`        | CLI arg | No       | Read URLs from a text file      |
