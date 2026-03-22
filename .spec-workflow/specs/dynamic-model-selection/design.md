# Design: Dynamic Model Selection

## Overview

The model name `gemini-2.5-flash` is currently hardcoded on a single line in `transcribe_video()`. This change threads a `model_name` parameter through the transcription pipeline and exposes it to users via a `--model` CLI flag and a web UI dropdown populated by a new `GET /models` endpoint.

## Steering Document Alignment

### Technical Standards (tech.md)
- Uses the existing `genai.list_models()` call (already in `check_available_models()`) to discover models dynamically.
- The default model (`gemini-2.5-flash`) remains the fallback — no behavior change for users who don't opt in.
- Same error code contract (0–7) — an invalid model name triggers existing Gemini API error handling.
- No new dependencies.

### Project Structure (structure.md)
- `transcribe.py` — modify `transcribe_video()` and `process_url()` signatures to accept `model_name`; add `--model` to CLI parsing; refactor `check_available_models()` to return a list.
- `app.py` — add `GET /models` route; pass `model` from request JSON to `process_url()`.
- `templates/index.html` — add model dropdown, fetch models on page load, include model in transcribe request.
- `test_transcribe.py` — add/update tests for model parameter threading.
- `test_app.py` — add tests for `GET /models` route.

## Code Reuse Analysis

### Existing Components to Leverage
- **`check_available_models()`** in `transcribe.py`: Currently prints models in debug mode. Refactored to return a list of model name strings — retains debug printing behavior and gains a return value.
- **`transcribe_video(video_path, temp_dir)`**: Add `model_name` parameter with default `'gemini-2.5-flash'`. The single line `genai.GenerativeModel('gemini-2.5-flash')` becomes `genai.GenerativeModel(model_name)`.
- **`process_url(url, index, total)`**: Add `model_name` parameter, pass through to `transcribe_video()`.

### Integration Points
- **`POST /transcribe` route**: Reads optional `model` field from request JSON and passes it to `process_url()`.
- **CLI `main()`**: Parses `--model <name>` flag and passes it to `process_url()` calls.
- **Web UI transcribe function**: Includes selected model in the fetch body.

## Architecture

### Parameter Threading

```
CLI: --model gemini-2.0-flash
  │
  ▼
main(model_name='gemini-2.0-flash')
  │
  ▼
process_url(url, model_name='gemini-2.0-flash')
  │
  ▼
transcribe_video(path, temp_dir, model_name='gemini-2.0-flash')
  │
  ▼
genai.GenerativeModel('gemini-2.0-flash')
```

```
Web: POST /transcribe { urls: [...], model: "gemini-2.0-flash" }
  │
  ▼
app.py reads model from JSON (default: 'gemini-2.5-flash')
  │
  ▼
process_url(url, model_name='gemini-2.0-flash')
  │
  ▼
transcribe_video(path, temp_dir, model_name='gemini-2.0-flash')
  │
  ▼
genai.GenerativeModel('gemini-2.0-flash')
```

### Data Flow — Model List

```
Page load
  │
  ▼
JS sends GET /models
  │
  ▼
app.py calls check_available_models()
  │ (returns list of model name strings)
  ▼
Return JSON { models: ["gemini-2.5-flash", "gemini-2.0-flash", ...] }
  │
  ▼
JS populates <select> dropdown
```

### Default Constant

A module-level constant `DEFAULT_MODEL = 'gemini-2.5-flash'` in `transcribe.py` replaces the hardcoded string. All default parameter values and fallbacks reference this constant.

## Components and Interfaces

### Modified Function — `check_available_models()` (transcribe.py)

| Aspect | Before | After |
|--------|--------|-------|
| **Signature** | `() → None` | `() → list[str]` |
| **Behavior** | Prints models in debug mode | Returns list of model names supporting `generateContent`; still prints in debug mode |
| **Failure** | Prints error, returns nothing | Prints error, returns `[DEFAULT_MODEL]` |

### Modified Function — `transcribe_video()` (transcribe.py)

| Aspect | Before | After |
|--------|--------|-------|
| **Signature** | `(video_path, temp_dir=None)` | `(video_path, temp_dir=None, model_name=DEFAULT_MODEL)` |
| **Model line** | `genai.GenerativeModel('gemini-2.5-flash')` | `genai.GenerativeModel(model_name)` |

### Modified Function — `process_url()` (transcribe.py)

| Aspect | Before | After |
|--------|--------|-------|
| **Signature** | `(url, index=None, total=None)` | `(url, index=None, total=None, model_name=DEFAULT_MODEL)` |
| **Passes to** | `transcribe_video(video_path, temp_dir)` | `transcribe_video(video_path, temp_dir, model_name=model_name)` |

### New Route — `GET /models` (app.py)

| Aspect | Detail |
|--------|--------|
| **Method** | GET |
| **Success response** | 200: `{"models": ["gemini-2.5-flash", "gemini-2.0-flash", ...]}` |
| **API key missing** | 200: `{"models": ["gemini-2.5-flash"]}` (fallback to default) |
| **Gemini API error** | 200: `{"models": ["gemini-2.5-flash"]}` (fallback to default) |

Note: This endpoint always returns 200 — it degrades gracefully rather than erroring, since a failed model list should not prevent the user from transcribing.

### Modified Route — `POST /transcribe` (app.py)

| Aspect | Detail |
|--------|--------|
| **New optional field** | `model` in request JSON (string) |
| **Default** | `gemini-2.5-flash` if `model` not provided |
| **Passed to** | `process_url(url, i, total, model_name=model)` |

### UI Component — Model Dropdown (templates/index.html)

| Aspect | Detail |
|--------|--------|
| **Element** | `<select id="model-select">` above the Transcribe button |
| **Population** | On page load, `fetch('/models')` → populate `<option>` elements |
| **Default selected** | `gemini-2.5-flash` |
| **Fallback** | If fetch fails, dropdown contains only `gemini-2.5-flash` |
| **Included in request** | `transcribe()` JS function reads selected value and adds `model: value` to POST body |

### CLI — `--model` Flag (transcribe.py main())

| Aspect | Detail |
|--------|--------|
| **Syntax** | `python transcribe.py <url> --model gemini-2.0-flash` |
| **Default** | `gemini-2.5-flash` if not provided |
| **Parsing** | Same manual pattern as `--debug` and `--file`: find `--model` in args, take next arg as value, remove both from args list |
| **Usage output** | Updated to show `[--model <name>]` |

## Error Handling

### Error Scenarios

| Scenario | Handling | User Impact |
|----------|----------|-------------|
| Invalid model name passed to Gemini | `genai.GenerativeModel(name)` or `generate_content()` raises exception → caught by existing error handling in `transcribe_video()` | Transcription fails with API error; same as any other Gemini error |
| `GET /models` fails (no API key) | Return `{"models": ["gemini-2.5-flash"]}` | Dropdown shows default only — user can still transcribe |
| `GET /models` fails (network error) | Return `{"models": ["gemini-2.5-flash"]}` | Dropdown shows default only |
| `--model` flag without value | Print usage and `sys.exit(1)` | Same pattern as `--file` without filename |
| Model deprecated by Google | Gemini returns error at transcription time | Error displayed to user; they can pick a different model |

## Testing Strategy

### Unit Tests — `test_transcribe.py`

| Test | Verifies |
|------|----------|
| `test_transcribe_video_custom_model` | `GenerativeModel` called with provided model name |
| `test_transcribe_video_default_model` | `GenerativeModel` called with `DEFAULT_MODEL` when no model specified |
| `test_process_url_passes_model` | `transcribe_video` receives model_name from `process_url` |
| `test_check_available_models_returns_list` | Returns list of model name strings |
| `test_check_available_models_error_returns_default` | Returns `[DEFAULT_MODEL]` on exception |
| `test_main_model_flag` | `--model` flag parsed and threaded to `process_url` |

### Route Tests — `test_app.py`

| Test | Verifies |
|------|----------|
| `test_get_models_success` | 200 with list of model names |
| `test_get_models_no_api_key` | 200 with default model fallback |
| `test_transcribe_with_model` | Model from request JSON passed to `process_url` |
| `test_transcribe_without_model` | Default model used when not specified |

### Manual Testing
- Select a non-default model in the dropdown, transcribe a URL, verify it works.
- Refresh the page, verify dropdown repopulates.
- Disconnect network, verify dropdown shows default only and transcription still works with default.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| User picks a model that doesn't support video input | Transcription fails | Gemini API error is caught; user sees clear error message and can pick another model |
| `list_models()` returns models with different naming conventions | Confusing dropdown entries | Filter to only models containing "gemini" and supporting `generateContent` |
| Model list API call is slow | Dropdown empty during page load | Show "Loading models…" placeholder; fallback to default after timeout |
