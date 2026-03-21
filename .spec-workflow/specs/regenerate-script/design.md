# Design: Regenerate Script

## Overview

Regeneration lets a user re-run the Gemini transcription for a URL that has already been processed. The backend work is identical to the original transcription — call `process_url()` — so no new business logic is needed in `transcribe.py`. The changes are concentrated in three areas: a new `/regenerate` Flask route, a Regenerate button in the UI, and client-side JavaScript to handle per-result re-fetching.

## Steering Document Alignment

### Technical Standards (tech.md)
- Reuses the existing `process_url()` pipeline — no new transcription logic.
- Follows the stateless request model: each regeneration is a self-contained download → compress → transcribe → cleanup cycle.
- Same error code contract (0–7) applies to regeneration failures.
- Same rate-limit rules: if regeneration is fired manually one URL at a time, no delay is needed; the 4-second batch delay only applies to multi-URL batch calls.

### Project Structure (structure.md)
- `transcribe.py` — no changes.
- `app.py` — add one route (`POST /regenerate`).
- `templates/index.html` — add Regenerate button + JS handler.
- `test_app.py` — add tests for the new route.

## Code Reuse Analysis

### Existing Components to Leverage
- **`transcribe.process_url(url)`**: The entire regeneration pipeline. Called identically to the initial transcription.
- **`transcribe.validate_url(url)`**: URL validation before regeneration attempt.
- **`transcribe.check_network()`**: Network connectivity check, same as `/transcribe`.
- **`transcribe.check_dependencies()`**: Dependency verification, same as `/transcribe`.

### Integration Points
- **`POST /transcribe` route**: The `/regenerate` route mirrors its structure — same pre-checks (API key, network, dependencies), same call to `process_url()`, same JSON response shape.
- **UI result cards**: The existing batch result card markup is extended with a Regenerate button.

## Architecture

The regeneration flow is intentionally simple: it's the same transcription flow triggered from a different entry point.

### Data Flow — Web Regenerate

```
User clicks "Regenerate" on result card
  │
  ▼
JS sends POST /regenerate { url: "..." }
  │
  ▼
app.py /regenerate route
  ├── validate API key  → 500 if missing
  ├── check_network()   → 503 if down
  ├── check_dependencies() → 500 if missing
  └── process_url(url)
        ├── validate_url()
        ├── download_reel()
        ├── transcribe_video()
        └── cleanup temp dir
  │
  ▼
Return JSON { success: true/false, transcription/error }
  │
  ▼
JS updates the specific result card in-place
```

### Why a Separate `/regenerate` Endpoint?

The `/transcribe` endpoint handles both single and batch URLs and returns different response shapes for each. A dedicated `/regenerate` endpoint is simpler:
- Always accepts exactly one URL.
- Always returns the single-URL response shape: `{success, transcription}` or `{success, error}`.
- Makes the API intention explicit — callers know this is a retry, not a new submission.
- Avoids overloading `/transcribe` with additional parameters like `regenerate: true`.

## Components and Interfaces

### New Route — `POST /regenerate` (app.py)

| Aspect | Detail |
|--------|--------|
| **Method** | POST |
| **Request body** | `{"url": "https://..."}` |
| **Success response** | `{"success": true, "transcription": "..."}` (200) |
| **URL invalid** | `{"success": false, "error": "Invalid URL"}` (400) |
| **API key missing** | `{"success": false, "error": "..."}` (500) |
| **Network down** | `{"success": false, "error": "..."}` (503) |
| **Dependencies missing** | `{"success": false, "error": "..."}` (500) |
| **Transcription failed** | `{"success": false, "error": "..."}` (500) |

### UI Component — Regenerate Button

| Aspect | Detail |
|--------|--------|
| **Placement** | Inside each result card (single and batch), next to the transcription text |
| **Label** | "Regenerate" (or a refresh icon ↻ with tooltip) |
| **Loading state** | Button text changes to "Regenerating…", button disabled, card shows subtle loading indicator |
| **Success behavior** | Card transcription text replaced, status updated to success styling |
| **Failure behavior** | Error message shown on the card, previous transcription text preserved |

### JavaScript — `regenerate(url, cardElement)` Function

| Aspect | Detail |
|--------|--------|
| **Input** | URL string, reference to the DOM result card |
| **Action** | `fetch('/regenerate', {method: 'POST', body: JSON.stringify({url})})` |
| **Success** | Update card's transcription text, set green success border |
| **Failure** | Show error text on card, keep previous transcription visible, restore button |

## Error Handling

### Error Scenarios

| Scenario | HTTP Status | User Impact |
|----------|-------------|-------------|
| URL field empty/missing in request | 400 | Error message displayed on card |
| Invalid URL format | 400 | Error message displayed on card |
| API key not configured | 500 | Error message displayed on card |
| Network unreachable | 503 | Error message displayed on card |
| yt-dlp / FFmpeg missing | 500 | Error message displayed on card |
| Download fails (timeout, video not found) | 500 | Error message displayed, old transcription kept |
| Gemini rate limit | 500 | Error message displayed, old transcription kept |
| Gemini API error | 500 | Error message displayed, old transcription kept |

**Key invariant**: A failed regeneration never destroys the previous transcription. The old text remains visible until explicitly replaced by a successful result.

## Testing Strategy

### Unit Tests — `test_app.py`

| Test | Verifies |
|------|----------|
| `test_regenerate_success` | 200 response with `{success: true, transcription}` |
| `test_regenerate_no_url` | 400 when request body has no `url` field |
| `test_regenerate_invalid_url` | 400 when URL fails validation |
| `test_regenerate_missing_api_key` | 500 when API key is not set |
| `test_regenerate_no_network` | 503 when `check_network()` returns `False` |
| `test_regenerate_transcription_failure` | 500 when `process_url()` returns `None` |

### Manual Testing
- Regenerate a single-URL result — verify text updates in-place.
- Regenerate one item in a batch — verify only that card updates, others remain unchanged.
- Regenerate when network is down — verify error shown, old text preserved.
- Rapid-click Regenerate — verify button is disabled during loading (no duplicate requests).

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| User spams Regenerate, hitting Gemini rate limit | Exhausts free-tier quota | Disable button during request; show rate-limit error clearly |
| Video becomes unavailable between original transcription and regeneration | Download fails, no result | Show clear error; old transcription is preserved |
| Regeneration produces a worse result than original | User loses the better transcription | Future enhancement: version history. For now, the user can regenerate again. |
