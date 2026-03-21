# Tasks: Reel Transcription Core

## 1.0 Input and Validation

- [ ] 1.1 Verify `validate_url()` applies all three checks (length ≤ 2048, `http(s)://` scheme, contains `.`) identically in CLI and web paths
- [ ] 1.2 Confirm `--file` parsing skips `#` comment lines and blank lines; verify via `TestMainFunction` file-input tests
- [ ] 1.3 Verify malformed and boundary-case URLs are rejected (empty string, no scheme, no dot, exactly 2048 chars, 2049 chars) via `TestURLValidation` (6 tests)

## 2.0 Download and Media Prep

- [ ] 2.1 Confirm `download_reel()` maps errors correctly: `TimeoutExpired` → `None`, no video files found → `None`, generic exception → `None`; verify via `TestDownloadReel` (4 tests)
- [ ] 2.2 Validate compression behavior: `transcribe_video()` triggers at > 20 MB, `compress_video()` targets 18 MB with bitrate factor 0.8 and 64k audio, rejects if still > 20 MB post-compression
- [ ] 2.3 Confirm `TemporaryDirectory(prefix='reel_')` in `process_url()` cleans up on success, download failure, and transcription failure; verify via `TestTemporaryFileHandling` (1 test)

## 3.0 Gemini Transcription Flow

- [ ] 3.1 Validate `transcribe_video()` lifecycle: `genai.upload_file()` → poll `get_file()` every 2s / 60s max → `generate_content()` with `gemini-2.5-flash` → `video_file.delete()` fire-and-forget; verify via `TestTranscribeVideo` (6 tests)
- [ ] 3.2 Confirm timeout path returns `None` when elapsed ≥ 60s, and `FAILED` state returns `None` immediately
- [ ] 3.3 Verify missing API key exits with `ERROR_API_KEY` (code 3) and prints message referencing `.env`; verify via `TestMainFunction` API key tests

## 4.0 Batch and Rate Limiting

- [ ] 4.1 Confirm 4-second `time.sleep()` is applied between batch items in both `main()` and `/transcribe` route (not after last item); verify via `TestRateLimiting` (1 test)
- [ ] 4.2 Confirm batch results contain per-item `{url, success, transcription, error}` structures in both CLI output and web JSON
- [ ] 4.3 Verify a rate-limit error (code 4) on one URL does not stop the batch — remaining URLs are still processed; verify via `TestMainFunction` batch tests

## 5.0 CLI + Web Output Consistency

- [ ] 5.1 Confirm CLI errors go to stderr and transcriptions to stdout; verify via `TestOutputFormatting` (2 tests)
- [ ] 5.2 Confirm web `/transcribe` returns HTTP 400 for no URLs, 500 for API key / dependency / transcription errors, 503 for network failure
- [ ] 5.3 Confirm single-URL web response uses `{success, transcription}` shape and batch uses `{success, results: [...]}` shape; both validated against `app.py` route logic

## 6.0 Verification

- [ ] 6.1 Run full test suite: `pytest test_transcribe.py -v --cov=transcribe --cov-report=html`
- [ ] 6.2 Confirm all 48 tests pass across 13 test classes
- [ ] 6.3 Verify coverage report shows 100% of `transcribe.py` — check `htmlcov/index.html`

## Definition of Done

- [ ] All 48 tests in `test_transcribe.py` pass
- [ ] 100% coverage of `transcribe.py` with no major regression
- [ ] Error code contract (0–7) matches `steering/product.md`
- [ ] Steering alignment maintained with:
  - `.spec-workflow/steering/product.md`
  - `.spec-workflow/steering/tech.md`
  - `.spec-workflow/steering/structure.md`
