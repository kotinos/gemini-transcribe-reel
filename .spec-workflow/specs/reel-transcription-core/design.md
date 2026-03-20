# Design: Reel Transcription Core

## Overview

This design keeps `transcribe.py` as the single source of truth for core processing while `app.py` remains a thin HTTP adapter. The flow remains:

1. Validate input
2. Download media
3. Compress if needed
4. Upload + transcribe via Gemini
5. Return output and clean temp artifacts

## Architecture

### Modules

- `transcribe.py`
  - Owns validation, dependency checks, download, compression, transcription, and batch orchestration
- `app.py`
  - Owns request parsing and JSON response formatting
  - Delegates all business logic to `transcribe.py`

### Data Flow

- CLI path: `main()` -> `process_url()` -> `download_reel()` -> `compress_video()` -> `transcribe_video()`
- Web path: `/transcribe` route -> shared functions in `transcribe.py`

## Interface Contracts

### CLI

- Inputs: URL args, `--file`, `--debug`
- Outputs: transcript to stdout, errors to stderr, process exit code

### Web

- Input JSON:
  - single: `{ "url": "..." }` (legacy support)
  - batch: `{ "urls": ["...", "..."] }`
- Output JSON:
  - single: `{ success, transcription? , error? }`
  - batch: `{ success, results: [{ url, success, transcription?, error? }] }`

## Error Strategy

- Keep existing numeric error-code taxonomy (1-7)
- Preserve user-actionable messages
- Ensure batch behavior records independent per-item outcomes

## Rate-Limit Strategy

- Keep fixed inter-request delay for batch operations
- Implement in one location to avoid drift between CLI and web behavior

## Security and Privacy

- No persistent user data storage
- Temporary local files deleted after processing
- Remote uploaded artifacts cleaned after transcription
- API key loaded from local environment only

## Test Strategy

- Unit tests continue to mock external dependencies
- Preserve/expand tests for:
  - URL validation
  - download failures/timeouts
  - Gemini polling timeout and API errors
  - batch delay enforcement
  - temp file cleanup invariants

## Risks and Mitigations

1. Provider download changes (yt-dlp extractor shifts)
   - Mitigation: clear error surfacing + dependency checks
2. API quota spikes
   - Mitigation: deterministic pacing and explicit rate-limit messaging
3. Large media files
   - Mitigation: compression threshold + bitrate targeting

## Rollout Notes

- Keep backward compatibility for existing CLI and web users
- Prefer additive changes and avoid breaking error-code semantics
