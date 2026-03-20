# Requirements: Reel Transcription Core

## Summary

Improve the core transcription workflow so users get reliable, predictable results across CLI and Web UI while staying within Gemini free-tier limits.

## Goals

- Improve success rate for valid public social video URLs
- Keep behavior consistent between CLI and web endpoint
- Preserve clear error semantics for user-facing troubleshooting
- Maintain zero-cost operation on free-tier services

## Non-Goals

- Real-time streaming transcription
- User accounts, login, or persistence
- Caption burn-in / video editing
- Paid-tier optimization

## User Stories

1. As a creator, I can submit a valid Reel/TikTok/Facebook URL and receive transcript text.
2. As a user, I receive clear error messages and codes when processing fails.
3. As a batch user, I can process multiple URLs with predictable pacing and per-item results.
4. As a web user, I see the same validation and output behavior as CLI users.

## Functional Requirements

### URL Intake

- Accept one or many URLs (CLI args, CLI file input, web JSON body)
- Validate URL format before download
- Skip comments/empty lines in file-based batch input

### Download + Preprocessing

- Download video from supported providers using yt-dlp
- Enforce maximum download constraints
- Compress videos above Gemini upload threshold
- Clean up all temporary files after each item

### Transcription

- Upload media to Gemini
- Poll until media is available or timeout
- Request transcription response text
- Delete remote uploaded file after completion/failure where possible

### Error Handling

- Maintain existing exit-code contract (1-7)
- Provide actionable message per failure class
- Continue per-item reporting in batch mode

### Rate Limiting

- Enforce delay between batch requests to respect free-tier limits
- Keep behavior deterministic and testable

## Quality Requirements

- CLI and web parity for validation and core processing behavior
- Deterministic, test-covered error handling paths
- No regression in temporary-file cleanup guarantees

## Acceptance Criteria

1. Single valid URL returns transcript text in CLI and web.
2. Batch input returns per-URL success/error outcomes.
3. Invalid URL returns the expected validation failure path.
4. Missing API key path is surfaced clearly.
5. Rate-limit delay is applied in batch processing.
6. Temp files are cleaned for both success and failure cases.
7. Existing tests remain green or are updated with equivalent coverage.

## Dependencies

- Steering docs:
  - `.spec-workflow/steering/product.md`
  - `.spec-workflow/steering/tech.md`
  - `.spec-workflow/steering/structure.md`
- Runtime tools: FFmpeg, yt-dlp
- API: Google Gemini
