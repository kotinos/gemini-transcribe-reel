# Requirements: Dynamic Model Selection

## Introduction

Replace the hardcoded `gemini-2.5-flash` model with a user-selectable model. The web UI presents a dropdown of available Gemini models and the CLI accepts a `--model` flag. This lets users switch to newer, faster, or more capable models as Google releases them — without editing source code.

## Alignment with Product Vision

Reel Transcriber is built on Google's free Gemini API. Model availability and performance change frequently — new models launch, old ones deprecate, and different models produce different transcription quality. Letting the user choose the model keeps the tool future-proof and gives power users control over the quality/speed tradeoff.

## Requirements

### Requirement 1 — CLI Model Flag

**User Story:** As a CLI user, I want to specify which Gemini model to use so that I can try different models for better transcription quality.

#### Acceptance Criteria

1. WHEN the user passes `--model <name>` THEN the system SHALL use that model for all transcriptions in the session.
2. IF `--model` is not provided THEN the system SHALL default to `gemini-2.5-flash`.
3. WHEN `--model` is combined with `--file` or batch URLs THEN the selected model SHALL apply to every URL in the batch.
4. WHEN `--model` is passed with `--debug` THEN the system SHALL print the selected model name in debug output.

### Requirement 2 — Web UI Model Selector

**User Story:** As a web UI user, I want to pick a model from a dropdown before transcribing so that I can choose the best model for my video.

#### Acceptance Criteria

1. WHEN the page loads THEN the system SHALL fetch the list of available models and populate a dropdown selector.
2. WHEN the user selects a model and submits URLs THEN the system SHALL use that model for all transcriptions in the request.
3. IF the model list cannot be fetched (API key missing, network error) THEN the dropdown SHALL show only the default model (`gemini-2.5-flash`) and remain usable.
4. WHEN no model is explicitly selected THEN the system SHALL use the default (`gemini-2.5-flash`).

### Requirement 3 — Models API Endpoint

**User Story:** As a developer, I want an endpoint that returns available Gemini models so that the UI dropdown and external scripts can discover models programmatically.

#### Acceptance Criteria

1. `GET /models` SHALL return a JSON array of model names that support `generateContent`.
2. IF the API key is not configured THEN the endpoint SHALL return `{"models": ["gemini-2.5-flash"]}` (default only).
3. IF the Gemini API call fails THEN the endpoint SHALL return the default model list and not error out.

### Requirement 4 — Model Passed Through Transcription Pipeline

**User Story:** As a developer, I want the model name threaded through the transcription functions so that the selected model is used end-to-end.

#### Acceptance Criteria

1. WHEN `process_url()` is called THEN the model name SHALL be passed to `transcribe_video()`.
2. WHEN `transcribe_video()` creates the `GenerativeModel` instance THEN it SHALL use the provided model name instead of the hardcoded string.
3. IF no model name is provided to `process_url()` THEN `gemini-2.5-flash` SHALL be used as the default.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: Model selection is a parameter — `transcribe_video()` accepts a model name string. No model-selection logic inside the transcription function.
- **Backward Compatibility**: All existing call sites continue to work without changes by using the default parameter value.

### Performance
- Model list is fetched once per page load (not per transcription request).
- The `GET /models` endpoint caches nothing — each call queries Gemini. This is acceptable since it's called infrequently (page load only).

### Security
- No new attack surface — the model name is a string passed to `genai.GenerativeModel()`. Invalid model names produce a Gemini API error, which is already handled.

### Reliability
- If model listing fails, the system falls back to the hardcoded default — the feature degrades gracefully rather than breaking.
- An invalid model name selected by the user results in a Gemini API error caught by the existing error handling in `transcribe_video()`.

### Usability
- The dropdown defaults to `gemini-2.5-flash` so existing users see no change in behavior.
- Only models that support `generateContent` are shown — no confusing entries for embedding-only or chat-only models.
