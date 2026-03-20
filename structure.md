# Codebase Structure

## Directory Layout

```
gemini-transcribe-reel/
├── transcribe.py          # Core CLI module — all business logic
├── app.py                 # Flask web server — thin HTTP wrapper
├── templates/
│   └── index.html         # Single-page web UI (HTML + CSS + JS)
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Dev dependencies (extends requirements.txt)
├── test_transcribe.py     # Unit test suite (48 tests, 13 classes)
├── test.sh                # Integration smoke tests (bash)
├── .env                   # API key (not committed, user-created)
├── README.md              # Quick-start guide
├── WEB_UI_README.md       # Web UI documentation
├── WINDOWS.md             # Windows-specific setup
├── TESTING.md             # Test workflow and CI/CD template
├── product.md             # Product vision and objectives
├── tech.md                # Technical architecture decisions
├── structure.md           # This file
├── htmlcov/               # Generated coverage report (gitignored)
├── __pycache__/           # Python bytecode cache (gitignored)
└── venv/                  # Virtual environment (gitignored)
```

## Module Architecture

### transcribe.py — Core Engine (~600 lines)

The single module containing all business logic. Every feature is a function; there are no classes.

| Function              | Responsibility                                                    |
|-----------------------|-------------------------------------------------------------------|
| `check_network()`     | DNS connectivity check (socket to 8.8.8.8:53)                    |
| `validate_url(url)`   | URL format validation (scheme, length ≤ 2048)                    |
| `check_dependencies()`| Verify yt-dlp and FFmpeg are on PATH                             |
| `download_reel(url)`  | Download video via yt-dlp subprocess (200 MB limit)              |
| `compress_video(path)`| FFmpeg compression for files > 20 MB (targets 18 MB)            |
| `transcribe_video(path)` | Upload to Gemini, poll until ACTIVE, generate transcription   |
| `process_url(url)`    | Orchestrate: download → compress → transcribe → cleanup         |
| `main()`              | CLI argument parsing, batch/file dispatch, error code routing    |
| `debug_print(msg)`    | Conditional stderr output when `--debug` is active               |

**Control flow:**

```
main()
 ├── parse args (single URL / multiple URLs / --file)
 ├── check_network()
 ├── check_dependencies()
 ├── load GEMINI_API_KEY from .env
 └── for each URL:
      └── process_url(url)
           ├── validate_url()
           ├── download_reel()    → temp video file
           ├── compress_video()   → (only if > 20 MB)
           ├── transcribe_video() → transcription text
           └── cleanup temp dir
```

### app.py — Web Server (~140 lines)

A thin Flask application with two routes. Contains no business logic — delegates everything to `transcribe.py`.

| Route             | Method | Behavior                                              |
|-------------------|--------|-------------------------------------------------------|
| `/`               | GET    | Serve `templates/index.html`                          |
| `/transcribe`     | POST   | Accept JSON `{urls: [...]}`, return transcription JSON |

**Response formats:**

- Single URL: `{success: true, transcription: "..."}` or `{success: false, error: "..."}`
- Batch: `{success: true, results: [{url, success, transcription, error}, ...]}`

### templates/index.html — Web UI (~300 lines)

Self-contained single-page app (no build step, no external assets).

| Section     | Purpose                                              |
|-------------|------------------------------------------------------|
| HTML        | Single URL input, batch textarea, transcribe button  |
| CSS         | Minimal inline styles, 600 px max-width, system fonts |
| JavaScript  | `transcribe()` async fetch, `showBatchResults()` formatter |

### test_transcribe.py — Test Suite (~700 lines)

48 unit tests organized into 13 classes, one per functional area:

| Test Class                    | Tests | Covers                                    |
|-------------------------------|-------|-------------------------------------------|
| `TestDebugPrint`              | 2     | Debug output on/off                       |
| `TestNetworkCheck`            | 2     | Socket connectivity mock                  |
| `TestURLValidation`           | 6     | Valid/invalid URLs, length limits          |
| `TestDependencyCheck`         | 2     | yt-dlp / FFmpeg presence                  |
| `TestDownloadReel`            | 4     | Success, timeout, no video, exceptions    |
| `TestTranscribeVideo`         | 6     | Upload, polling, rate limit, auth error   |
| `TestProcessURL`              | 5     | End-to-end single-URL flow                |
| `TestMainFunction`            | 13    | Arg parsing, batch, file, error paths     |
| `TestRateLimiting`            | 1     | 4-second delay enforcement                |
| `TestCheckAvailableModels`    | 2     | Model listing success/error               |
| `TestErrorCodes`              | 2     | All codes defined and unique              |
| `TestTemporaryFileHandling`   | 1     | Temp dir cleanup verification             |
| `TestOutputFormatting`        | 2     | Single vs batch output format             |

## Dependency Graph

```
app.py ──imports──► transcribe.py ──calls──► yt-dlp (subprocess)
                         │                    FFmpeg (subprocess)
                         │                    google-generativeai (API)
                         └──reads──► .env (python-dotenv)

test_transcribe.py ──imports──► transcribe.py (all external deps mocked)
```

## File Conventions

- **No classes in production code** — all functions at module level
- **Errors to stderr** — `print(..., file=sys.stderr)`
- **Transcription to stdout** — clean output for piping
- **Exit codes** — `sys.exit(N)` with codes 0–7
- **Temp files** — always inside `tempfile.TemporaryDirectory()` context managers
