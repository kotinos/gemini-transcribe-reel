# Requirements: Regenerate Script

## Introduction

Add a regenerate capability so users can re-run the Gemini transcription for any previously transcribed URL. When the AI model hallucinates or produces a bad transcription, the user should be able to trigger a fresh transcription call with a single click from the web UI, replacing the old result.

## Alignment with Product Vision

Reel Transcriber's core value is accurate, low-friction transcription. Gemini can occasionally hallucinate — producing inaccurate, incomplete, or fabricated text. Without regeneration, the user's only option is to manually re-submit the same URL, losing any association with the previous result. This feature closes that gap by keeping the workflow inside the UI.

## Requirements

### Requirement 1 — Regenerate from Web UI

**User Story:** As a user viewing a transcription result, I want to click a "Regenerate" button so that the system re-runs the transcription and replaces the bad output without me having to re-paste the URL.

#### Acceptance Criteria

1. WHEN the user clicks "Regenerate" on a displayed transcription result THEN the system SHALL re-download the video from the original URL AND re-transcribe it using Gemini.
2. WHEN regeneration succeeds THEN the system SHALL replace the displayed transcription text with the new result.
3. WHEN regeneration is in progress THEN the system SHALL show a loading indicator on that specific result and disable the Regenerate button.
4. IF regeneration fails (download error, API error, rate limit, network error) THEN the system SHALL display the error message and preserve the previous transcription text.

### Requirement 2 — Regenerate in Batch Results

**User Story:** As a user who submitted a batch of URLs, I want to regenerate individual results from the batch without re-processing the entire batch.

#### Acceptance Criteria

1. WHEN a batch result is displayed THEN each individual result card SHALL have its own Regenerate button.
2. WHEN the user clicks Regenerate on one batch item THEN only that URL SHALL be re-processed; other results SHALL remain unchanged.
3. WHEN regeneration of a batch item succeeds THEN the result card SHALL update to show the new transcription and its status SHALL change to success (green border).

### Requirement 3 — Regenerate via API

**User Story:** As a developer, I want a dedicated API endpoint for regeneration so that scripts and integrations can programmatically retry failed or bad transcriptions.

#### Acceptance Criteria

1. WHEN a POST request is sent to `/regenerate` with `{"url": "..."}` THEN the system SHALL re-download and re-transcribe the URL.
2. WHEN regeneration succeeds THEN the endpoint SHALL return `{"success": true, "transcription": "..."}` with status 200.
3. IF the URL is invalid THEN the endpoint SHALL return `{"success": false, "error": "..."}` with status 400.
4. IF regeneration fails due to download, API, or network errors THEN the endpoint SHALL return the appropriate error status (500 or 503) following the existing error code contract.

### Requirement 4 — CLI Regenerate

**User Story:** As a CLI user, I want to re-run a transcription for the same URL(s) by simply re-running the command, so that regeneration works naturally without any new flags.

#### Acceptance Criteria

1. The CLI already supports re-running any URL — no changes needed. This requirement exists to confirm the CLI path is inherently idempotent and needs no modification.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: Regeneration reuses `process_url()` — no new business logic in `app.py`.
- **Modular Design**: The Regenerate button is a UI-only addition; the backend call is identical to the initial transcription call.

### Performance
- Regeneration follows the same rate-limit rules (4-second delay if batched).
- No caching of previous results — each regeneration is a full re-download and re-transcription.

### Security
- No new attack surface — regeneration uses the same `process_url()` path with the same URL validation.
- The `/regenerate` endpoint validates URLs identically to `/transcribe`.

### Reliability
- A failed regeneration never destroys the previous result — the old transcription text is preserved until a successful replacement.
- Temp files follow the same `TemporaryDirectory` lifecycle as initial transcription.

### Usability
- The Regenerate button is clearly visible on each result card but not intrusive.
- Loading state is scoped to the specific result being regenerated, not the entire page.
