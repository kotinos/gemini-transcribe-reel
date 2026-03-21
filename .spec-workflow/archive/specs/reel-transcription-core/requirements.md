# Requirements: Reel Transcription Core

## Summary

Zero-cost video transcription tool that downloads Instagram Reels, TikTok videos, and Facebook videos, then transcribes them via Google's free Gemini API (`gemini-2.5-flash`). Provides a CLI for scripting and a Flask web UI for manual use, with identical core behavior across both interfaces.

## Goals

- Transcribe valid public social video URLs reliably across CLI and web UI
- Maintain consistent validation, processing, and error behavior between interfaces
- Surface clear, actionable error codes (0–7) for every failure mode
- Operate entirely on free-tier services with zero cost

## Non-Goals

- Real-time or streaming transcription
- User accounts, login, or persistent storage
- Caption burn-in or video editing
- Paid-tier API optimization or billing management

## User Stories

1. As a creator, I submit a valid Instagram Reel / TikTok / Facebook video URL and receive the transcription text.
2. As a user, I receive a specific error code and message when processing fails, so I know what to fix.
3. As a batch user, I process multiple URLs (via CLI args, `--file`, or web JSON) with 4-second pacing and independent per-item results.
4. As a web user, I see the same validation and output behavior as CLI users.
5. As a developer, I can enable `--debug` mode to see step-by-step diagnostic output to stderr.

## Functional Requirements

### Initialization

- Check network connectivity via socket to `8.8.8.8:53` (3-second timeout); exit code 7 on failure
- Verify `yt-dlp` and `ffmpeg` are on PATH; exit code 2 if missing
- Load `GEMINI_API_KEY` from `.env` via python-dotenv; exit code 3 if absent
- Configure `google-generativeai` client with the loaded key

### URL Intake

- Accept URLs from: CLI positional args, `--file <path>` (one URL per line), or web JSON body (`urls` array or legacy `url` string)
- Validate each URL via `validate_url()`: length ≤ 2048 characters, must start with `http://` or `https://`, must contain at least one `.`
- Skip lines starting with `#` and blank lines in file-based input
- Invalid URLs are skipped with an error message; processing continues for remaining URLs

### Download + Preprocessing

- Download video via `yt-dlp` subprocess with `--max-filesize 200M`, `--no-playlist`, `--quiet`, `--no-warnings` (60-second timeout)
- Locate downloaded file by scanning for extensions: `mp4`, `mkv`, `webm`, `mov`, `flv` (newest by mtime)
- If file > 20 MB, compress via `compress_video()`:
  - Get duration via `ffprobe` (10-second timeout)
  - Calculate video bitrate: `(target_size_mb × 8 × 1024² × 0.8) / duration` (target default: 18 MB)
  - Encode with `ffmpeg`: `libx264` at calculated bitrate, `aac` at 64 kbps, `-movflags +faststart` (120-second timeout)
  - Reject if compressed output still exceeds 20 MB
- All files in a `tempfile.TemporaryDirectory(prefix='reel_')` context — auto-cleaned on exit, including exceptions

### Transcription

- Upload video to Gemini via `genai.upload_file(path)`
- Poll `genai.get_file()` every 2 seconds until state is `ACTIVE` or `FAILED` (60-second max)
- Generate transcription via `GenerativeModel('gemini-2.5-flash').generate_content([prompt, file])`
- Prompt: _"Transcribe all spoken words from this video. If there are visible captions or text overlays, include them as well. Output only the complete transcription text."_
- Delete uploaded file via `video_file.delete()` (fire-and-forget, exceptions silenced)

### Error Handling

| Exit Code | Constant           | Trigger                                          |
|-----------|---------------------|--------------------------------------------------|
| 0         | —                   | Success                                          |
| 1         | `ERROR_INVALID_URL` | URL fails validation (also used for missing args)|
| 2         | `ERROR_DOWNLOAD`    | yt-dlp/ffmpeg missing or download failure        |
| 3         | `ERROR_API_KEY`     | `GEMINI_API_KEY` not found in `.env`             |
| 4         | `ERROR_RATE_LIMIT`  | Gemini rate limit detected (non-fatal in batch)  |
| 5         | `ERROR_API`         | API auth/config error (fatal)                    |
| 6         | `ERROR_AUDIO`       | Defined but currently unused                     |
| 7         | `ERROR_NETWORK`     | Network connectivity check fails                 |

- Fatal errors (2, 3, 5, 7) call `sys.exit()` immediately
- Non-fatal errors (1, 4) skip the current URL and continue batch processing
- All errors print to stderr; transcription output goes to stdout

### Batch Processing and Rate Limiting

- URLs processed sequentially with a 4-second `time.sleep()` between items (targets Gemini free tier: 15 req/min)
- Each URL produces an independent success/error result
- Partial failures do not stop the batch; remaining URLs are still processed
- Batch summary printed at end: `BATCH RESULTS: N/M successful`

### CLI Output

- Single URL: transcription text to stdout
- Batch: numbered results with `[i]` prefix, followed by summary separator
- All errors to stderr
- `--debug` flag enables `[DEBUG]` prefixed diagnostic messages to stderr

### Web Interface

- `POST /transcribe` accepts `{"urls": [...]}` or legacy `{"url": "..."}`
- Single URL success: `{"success": true, "transcription": "..."}`
- Single URL failure: `{"success": false, "error": "ERROR: ..."}`
- Batch response: `{"success": true, "results": [{"url", "success", "transcription", "error"}, ...]}`
- HTTP status codes: 200 (success), 400 (no URLs), 500 (API key missing / dependency error / transcription failure), 503 (no network)

## Quality Requirements

- CLI and web share the same validation, processing, and error paths via `transcribe.py`
- All external dependencies mocked in tests; no network, API, or filesystem side effects
- `tempfile.TemporaryDirectory` guarantees cleanup on all code paths
- 66 tests total (55 in `test_transcribe.py` across 13 classes + 11 in `test_app.py` across 2 classes) covering all error codes, batch behavior, rate limiting, output formatting, and HTTP routes

## Acceptance Criteria

1. Single valid URL returns transcription text in both CLI and web.
2. Batch input returns per-URL success/error outcomes with `[i]` labeling and summary.
3. URL exceeding 2048 chars, missing scheme, or missing dot is rejected with code 1.
4. Missing `GEMINI_API_KEY` exits with code 3 and a message naming `.env`.
5. 4-second delay is applied between batch items (verified in `TestRateLimiting`).
6. Temp directory is auto-cleaned for both success and failure paths (verified in `TestTemporaryFileHandling`).
7. All 66 tests pass (55 in `test_transcribe.py` + 11 in `test_app.py`) with coverage of `transcribe.py`.

## Dependencies

- Steering docs:
  - `.spec-workflow/steering/product.md`
  - `.spec-workflow/steering/tech.md`
  - `.spec-workflow/steering/structure.md`
- Runtime tools: FFmpeg, yt-dlp
- API: Google Gemini (`gemini-2.5-flash`)
- Python packages: `google-generativeai`, `python-dotenv`, `flask`, `yt-dlp`
- Dev packages: `pytest`, `pytest-cov`, `pytest-mock`
