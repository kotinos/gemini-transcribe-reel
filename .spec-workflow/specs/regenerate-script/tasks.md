# Tasks: Regenerate Script

## 1.0 Backend — `/regenerate` Route

- [x] 1.1 Add `POST /regenerate` route to `app.py`
  - Accept JSON `{"url": "..."}`, validate URL, run pre-checks (API key, network, dependencies), call `process_url(url)`, return single-URL JSON response shape
  - Return 400 for missing/invalid URL, 500 for API key / dependency / transcription errors, 503 for network failure
  - _Leverage: existing `/transcribe` route pattern, `transcribe.process_url()`, `transcribe.validate_url()`_
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 1.2 Add unit tests for `/regenerate` in `test_app.py`
  - Add `TestRegenerateEndpoint` class with tests: `test_regenerate_success`, `test_regenerate_no_url`, `test_regenerate_invalid_url`, `test_regenerate_missing_api_key`, `test_regenerate_no_network`, `test_regenerate_transcription_failure`
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

## 2.0 Frontend — Regenerate Button on Single Result

- [x] 2.1 Add a Regenerate button to the single-URL result display in `templates/index.html`
  - Button appears below the transcription text after a successful or failed transcription
  - Store the original URL in a `data-url` attribute on the result container
  - _Requirements: 1.1_

- [x] 2.2 Add `regenerate(url, resultElement)` JavaScript function
  - POST to `/regenerate` with the URL
  - Show loading state (disable button, change text to "Regenerating…")
  - On success: replace transcription text, restore button
  - On failure: show error message, preserve old transcription, restore button
  - _Requirements: 1.2, 1.3, 1.4_

## 3.0 Frontend — Regenerate Button on Batch Results

- [x] 3.1 Add a Regenerate button to each batch result card in `templates/index.html`
  - Each card's button is wired to that card's URL via `data-url`
  - Regeneration scoped to individual card — other cards unaffected
  - _Requirements: 2.1, 2.2_

- [x] 3.2 Handle batch card update on regeneration success
  - Update the card's transcription text, flip status to success (green border), update summary bar count if status changed from failure to success
  - _Requirements: 2.3_

## 4.0 Verification

- [x] 4.1 Run full test suite: `pytest test_transcribe.py test_app.py -v --tb=short`
- [x] 4.2 Confirm all existing tests still pass (no regressions) and new `/regenerate` tests pass
- [x] 4.3 Manual smoke test: transcribe a URL via web UI, click Regenerate, verify result updates in-place

## Definition of Done

- [x] `POST /regenerate` route exists in `app.py` with correct status codes and JSON shape
- [x] All new and existing tests pass
- [x] Regenerate button visible on single-URL and batch result cards in the web UI
- [x] Button disabled during regeneration; old transcription preserved on failure
- [x] No changes to `transcribe.py` — regeneration reuses `process_url()` as-is
