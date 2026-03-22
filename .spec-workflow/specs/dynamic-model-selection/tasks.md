# Tasks: Dynamic Model Selection

## 1.0 Core — Thread Model Name Through Pipeline

- [x] 1.1 Add `DEFAULT_MODEL = 'gemini-2.5-flash'` constant to `transcribe.py`
  - Replace the hardcoded string on the `GenerativeModel(...)` line with this constant
  - _Requirements: 4.2, 4.3_

- [x] 1.2 Add `model_name` parameter to `transcribe_video()` in `transcribe.py`
  - Signature: `transcribe_video(video_path, temp_dir=None, model_name=DEFAULT_MODEL)`
  - Use `model_name` in `genai.GenerativeModel(model_name)`
  - _Requirements: 4.2_

- [x] 1.3 Add `model_name` parameter to `process_url()` in `transcribe.py`
  - Signature: `process_url(url, index=None, total=None, model_name=DEFAULT_MODEL)`
  - Pass `model_name` through to `transcribe_video()`
  - _Requirements: 4.1_

- [x] 1.4 Refactor `check_available_models()` to return a list
  - Return list of model name strings (filtered to `generateContent` support)
  - On error, return `[DEFAULT_MODEL]`
  - Retain existing debug printing behavior
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 1.5 Add unit tests for model threading in `test_transcribe.py`
  - Tests: `test_transcribe_video_custom_model`, `test_transcribe_video_default_model`, `test_process_url_passes_model`, `test_check_available_models_returns_list`, `test_check_available_models_error_returns_default`
  - _Requirements: 4.1, 4.2, 4.3_

## 2.0 CLI — `--model` Flag

- [x] 2.1 Add `--model <name>` flag parsing to `main()` in `transcribe.py`
  - Same manual parsing pattern as `--debug` and `--file`: find in args, take next value, remove both
  - Error if `--model` present without a value (print usage, exit 1)
  - Default to `DEFAULT_MODEL` if not provided
  - Pass to all `process_url()` calls
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2.2 Update usage string in `main()` to show `[--model <name>]`
  - _Requirements: 1.1_

- [x] 2.3 Add `test_main_model_flag` test in `test_transcribe.py`
  - Verify `--model` is parsed and threaded to `process_url()`
  - _Requirements: 1.1, 1.4_

## 3.0 Backend — `/models` Endpoint and Transcribe Model Pass-Through

- [x] 3.1 Add `GET /models` route to `app.py`
  - Call `transcribe.check_available_models()`, return `{"models": [...]}`
  - Always return 200 — fallback to `[DEFAULT_MODEL]` on any error
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3.2 Add `model` field support to `POST /transcribe` in `app.py`
  - Read optional `model` from request JSON, default to `DEFAULT_MODEL`
  - Pass to all `process_url()` calls
  - _Requirements: 4.1, 4.2_

- [x] 3.3 Add route tests to `test_app.py`
  - Tests: `test_get_models_success`, `test_get_models_no_api_key`, `test_transcribe_with_model`, `test_transcribe_without_model`
  - _Requirements: 3.1, 3.2, 3.3, 4.1_

## 4.0 Frontend — Model Dropdown

- [x] 4.1 Add `<select id="model-select">` dropdown to `templates/index.html`
  - Place above the Transcribe button
  - Default option: `gemini-2.5-flash`
  - _Requirements: 2.1, 2.4_

- [x] 4.2 Fetch model list on page load
  - `GET /models` → populate dropdown `<option>` elements
  - On fetch error, keep default option only
  - _Requirements: 2.1, 2.3_

- [x] 4.3 Include selected model in transcribe request
  - `transcribe()` JS function reads `model-select` value, adds `model: value` to POST body
  - _Requirements: 2.2_

## 5.0 Verification

- [x] 5.1 Run full test suite: `pytest test_transcribe.py test_app.py -v --tb=short`
- [x] 5.2 Confirm all existing tests still pass (no regressions) and all new tests pass
- [x] 5.3 Manual smoke test: select a different model in dropdown, transcribe a URL, verify it uses the selected model

## Definition of Done

- [x] `DEFAULT_MODEL` constant replaces hardcoded `'gemini-2.5-flash'` string
- [x] `transcribe_video()` and `process_url()` accept `model_name` parameter with backward-compatible default
- [x] `check_available_models()` returns a list of model name strings
- [x] `--model <name>` CLI flag works and threads through to `GenerativeModel`
- [x] `GET /models` endpoint returns available models (degrades to default on error)
- [x] Web UI dropdown populated on page load; selected model sent with transcription request
- [x] All new and existing tests pass
