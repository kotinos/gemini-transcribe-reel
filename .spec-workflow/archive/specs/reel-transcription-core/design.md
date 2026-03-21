# Design: Reel Transcription Core

## Overview

`transcribe.py` is the single source of truth for all business logic. `app.py` is a thin Flask adapter that translates HTTP requests into function calls and formats JSON responses. There are no classes — every feature is a standalone function.

## Architecture

### Modules

- **`transcribe.py`** (~600 lines)
  - All business logic: validation, dependency checks, download, compression, transcription, batch orchestration, debug output
- **`app.py`** (~140 lines)
  - HTTP request parsing, JSON response formatting, delegated entirely to `transcribe.py`
- **`templates/index.html`** (~300 lines)
  - Self-contained single-page web UI (no build step, no external assets)

### Functions — `transcribe.py`

| Function | Signature | Responsibility |
|----------|-----------|----------------|
| `debug_print` | `(message, **kwargs)` | Conditional `[DEBUG]` output to stderr when `DEBUG` global is `True` |
| `check_network` | `()` → `bool` | Socket connection to `8.8.8.8:53` with 3-second timeout |
| `validate_url` | `(url)` → `bool` | Length ≤ 2048, scheme `http(s)://`, contains `.` |
| `check_dependencies` | `()` → `None` | Verify `yt-dlp` and `ffmpeg` on PATH via `where`; exits with code 2 |
| `download_reel` | `(url, output_dir)` → `str \| None` | yt-dlp download with 200 MB / 60-second limits |
| `compress_video` | `(input_path, output_path, target_size_mb=18)` → `str \| None` | FFmpeg compression: bitrate-targeted, 120-second timeout |
| `transcribe_video` | `(video_path, temp_dir=None)` → `str \| None` | Gemini upload → poll → generate → delete lifecycle |
| `check_available_models` | `()` → `None` | Lists `generateContent`-capable models (debug only) |
| `process_url` | `(url, index=None, total=None)` → `str \| None` | Orchestrate: validate → download → transcribe in temp dir |
| `main` | `()` → `None` | CLI entry: arg parsing, init checks, batch loop, output |

### Routes — `app.py`

| Route | Method | Behavior | Status Codes |
|-------|--------|----------|--------------|
| `/` | GET | Serve `templates/index.html` | 200 |
| `/transcribe` | POST | Process single or batch URLs | 200, 400, 500, 503 |

## Data Flow

### CLI Path

```
main()
 ├── Parse args: positional URLs / --file / --debug
 ├── Set global DEBUG flag
 ├── check_network() ──────────── exit 7 on failure
 ├── check_dependencies() ─────── exit 2 if yt-dlp or ffmpeg missing
 ├── load_dotenv() + read GEMINI_API_KEY ── exit 3 if absent
 ├── genai.configure(api_key)
 ├── check_available_models() ─── debug only
 └── for each URL (4s delay between):
      └── process_url(url, i, total)
           ├── validate_url(url) ──────── skip if invalid
           └── TemporaryDirectory(prefix='reel_'):
                ├── download_reel(url, temp_dir) ── skip if None
                └── transcribe_video(video_path, temp_dir)
                     ├── size > 20 MB? → compress_video()
                     ├── genai.upload_file(path)
                     ├── poll get_file() every 2s (max 60s)
                     ├── GenerativeModel('gemini-2.5-flash').generate_content()
                     └── video_file.delete() (fire-and-forget)
```

### Web Path

```
POST /transcribe
 ├── Parse JSON: urls[] or legacy url
 ├── Validate API key present ────── 500 if missing
 ├── check_network() ─────────────── 503 if down
 ├── check_dependencies() ────────── 500 if missing (catches SystemExit)
 └── for each URL (4s delay between):
      ├── validate_url() ──── record error result if invalid
      └── process_url() ──── record success/failure result
```

## Constants

| Constant | Value | Location |
|----------|-------|----------|
| `ERROR_INVALID_URL` | 1 | Module-level |
| `ERROR_DOWNLOAD` | 2 | Module-level |
| `ERROR_API_KEY` | 3 | Module-level |
| `ERROR_RATE_LIMIT` | 4 | Module-level |
| `ERROR_API` | 5 | Module-level |
| `ERROR_AUDIO` | 6 | Module-level (defined, unused) |
| `ERROR_NETWORK` | 7 | Module-level |
| URL max length | 2048 chars | `validate_url()` |
| Network check target | `8.8.8.8:53` | `check_network()` |
| Network check timeout | 3 seconds | `check_network()` |
| yt-dlp max file size | `200M` | `download_reel()` |
| yt-dlp timeout | 60 seconds | `download_reel()` |
| Compression trigger | > 20 MB | `transcribe_video()` |
| Compression target | 18 MB (default param) | `compress_video()` |
| Video bitrate factor | 0.8 (reserves 20% for audio) | `compress_video()` |
| Audio bitrate | 64 kbps | `compress_video()` |
| FFmpeg timeout | 120 seconds | `compress_video()` |
| ffprobe timeout | 10 seconds | `compress_video()` |
| Gemini model | `gemini-2.5-flash` | `transcribe_video()` |
| Upload poll interval | 2 seconds | `transcribe_video()` |
| Upload poll max wait | 60 seconds | `transcribe_video()` |
| Batch delay | 4 seconds | `main()` and `app.py` |
| Temp dir prefix | `reel_` | `process_url()` |

## Interface Contracts

### CLI

- **Inputs:** positional URL args, `--file <path>`, `--debug`
- **Outputs:** transcription text to stdout, errors to stderr, process exit code (0–7)
- **Batch output format:**
  ```
  ============================================================
  BATCH RESULTS: N/M successful
  ============================================================

  [1] <url>
  <transcription or (FAILED)>
  ```

### Web

- **Input JSON:**
  - Batch: `{ "urls": ["...", "..."] }`
  - Legacy single: `{ "url": "..." }`
- **Output JSON (single):**
  ```json
  { "success": true, "transcription": "..." }
  { "success": false, "error": "ERROR: ..." }
  ```
- **Output JSON (batch):**
  ```json
  {
    "success": true,
    "results": [
      { "url": "...", "success": true, "transcription": "...", "error": null },
      { "url": "...", "success": false, "transcription": null, "error": "Transcription failed" }
    ]
  }
  ```
- **HTTP status codes:**
  - 200 — successful transcription
  - 400 — no URLs in request body
  - 500 — API key missing, dependency check failed, or single-URL transcription error
  - 503 — network connectivity check failed

## Error Strategy

### Fatal vs Non-Fatal

| Behavior | Error Codes | Effect |
|----------|-------------|--------|
| **Fatal** — `sys.exit()` immediately | 2, 3, 5, 7 | Stops all processing |
| **Non-fatal** — skip URL, continue batch | 1, 4 | URL recorded as failed; remaining URLs processed |

### Error Detection in `transcribe_video()`

API exceptions are classified by keyword matching on the error message:
- **Rate limit** (`rate`, `quota`, `limit`, `429`): non-fatal, skip video
- **Auth** (`api`, `key`, `auth`, `401`, `403`): fatal, exit with code 5
- **Other**: non-fatal, skip video

### Unused Code

`ERROR_AUDIO` (exit code 6) is defined at module level but never raised. It is reserved for a future "video has no audio track" path per the error code contract in `steering/product.md`.

## Rate-Limit Strategy

- 4-second `time.sleep()` inserted between batch URLs (both CLI and web paths)
- Targets the Gemini free tier of 15 requests per minute
- Delay applied after each URL except the last
- Implemented identically in `main()` and `/transcribe` route to prevent drift

## Temp File Lifecycle

```python
with tempfile.TemporaryDirectory(prefix='reel_') as temp_dir:
    # download, compress, transcribe all happen inside
    # auto-cleaned on context exit — including exceptions
```

- All downloaded and compressed files live inside this directory
- Python's context manager guarantees cleanup on normal exit and exceptions
- No orphaned files possible under normal operation

## Security and Privacy

- No persistent user data, no database, no analytics
- API key loaded from `.env` — never logged or returned via HTTP
- URL length capped at 2048 characters to prevent DoS via validation
- Temp files auto-deleted after each URL
- Remote Gemini uploads deleted after transcription (fire-and-forget)
- Web server binds to `127.0.0.1` only (not exposed externally by default)

## Test Strategy

- **Framework:** pytest + pytest-mock + pytest-cov
- **Coverage target:** 100% of `transcribe.py`
- **Test suite:** 66 tests total — 55 across 13 classes in `test_transcribe.py`, 11 across 2 classes in `test_app.py`
- **Run command:** `pytest test_transcribe.py -v --cov=transcribe --cov-report=html`
- **Mocking:** All external dependencies fully mocked (Gemini API, yt-dlp subprocess, socket, file I/O)
- **Integration smoke tests:** `test.sh` exercises real error paths against the live CLI

| Test Class | Count | Coverage Area |
|------------|-------|---------------|
| `TestDebugPrint` | 2 | Debug output on/off |
| `TestNetworkCheck` | 2 | Socket connectivity mocking |
| `TestURLValidation` | 9 | Valid/invalid URLs, length limits, boundary cases |
| `TestDependencyCheck` | 2 | yt-dlp/FFmpeg presence |
| `TestDownloadReel` | 4 | Success, timeout, no video, exceptions |
| `TestTranscribeVideo` | 9 | Upload, polling, compression, rate limit, auth errors |
| `TestProcessURL` | 5 | End-to-end single-URL flow |
| `TestMainFunction` | 13 | Arg parsing, batch, file, error paths |
| `TestRateLimiting` | 1 | 4-second delay enforcement |
| `TestCheckAvailableModels` | 2 | Model listing success/error |
| `TestErrorCodes` | 2 | All codes defined and unique |
| `TestTemporaryFileHandling` | 1 | Temp dir cleanup |
| `TestOutputFormatting` | 2 | Single vs batch output format |

## Risks and Mitigations

1. **Provider download changes** (yt-dlp extractor shifts)
   - Mitigation: clear error surfacing via exit code 2 + dependency checks at startup
2. **API quota spikes**
   - Mitigation: 4-second pacing + explicit rate-limit detection and messaging
3. **Large media files**
   - Mitigation: 200 MB download cap + 20 MB compression trigger + 18 MB target
4. **Gemini file processing stalls**
   - Mitigation: 60-second polling timeout with `FAILED` state detection

## Rollout Notes

- Backward compatible with all existing CLI invocations and web API consumers
- Error code semantics (0–7) are frozen — no code reassignment without a major version bump
- `app.py` response shapes are stable — single and batch JSON formats preserved
