# Requirements: Local Script Storage

## Introduction

Add local database storage so transcription results ("scripts") are automatically saved and can be viewed, edited, and deleted from the web UI. Currently the app is fully stateless — once a transcription result leaves the screen it is gone. This feature gives users a persistent library of their transcriptions without relying on any external service.

## Alignment with Product Vision

Reel Transcriber targets content creators and accessibility advocates who transcribe videos for captions, repurposing, or archival. Losing a transcription because the browser tab was closed or the page was refreshed is a common friction point. Local storage closes that gap while preserving the project's zero-cost, zero-account, privacy-first principles — data never leaves the user's machine.

## Requirements

### Requirement 1 — Auto-Save on Transcription

**User Story:** As a user, I want my transcription results saved automatically so that I don't lose them when I close the browser or refresh the page.

#### Acceptance Criteria

1. WHEN a transcription completes successfully (single or batch) THEN the system SHALL save each result to the local database with the source URL, transcription text, and timestamp.
2. WHEN a batch transcription completes THEN each successful result in the batch SHALL be saved as a separate record.
3. IF a transcription fails THEN the system SHALL NOT create a database record for that URL.

### Requirement 2 — View Saved Scripts

**User Story:** As a user, I want to browse all my saved transcriptions so that I can find and reuse them later.

#### Acceptance Criteria

1. WHEN the user navigates to the web UI THEN the system SHALL display a list of all saved scripts, ordered by most recent first.
2. WHEN scripts exist THEN each entry in the list SHALL show the source URL, a preview of the transcription text (first ~100 characters), and the saved timestamp.
3. WHEN the user clicks on a script entry THEN the system SHALL display the full transcription text.

### Requirement 3 — Edit Saved Scripts

**User Story:** As a user, I want to edit a saved transcription so that I can fix errors, remove hallucinated content, or add notes.

#### Acceptance Criteria

1. WHEN the user views a saved script THEN the system SHALL provide an Edit button that switches the transcription text to an editable text area.
2. WHEN the user modifies the text and clicks Save THEN the system SHALL update the record in the database with the new text.
3. WHEN the user clicks Cancel during editing THEN the system SHALL discard changes and revert to the previously saved text.
4. WHEN a script is saved THEN the system SHALL update the timestamp to reflect the last-modified time.

### Requirement 4 — Delete Saved Scripts

**User Story:** As a user, I want to delete scripts I no longer need so that my library stays manageable.

#### Acceptance Criteria

1. WHEN the user clicks Delete on a saved script THEN the system SHALL remove the record from the database.
2. WHEN deletion succeeds THEN the script SHALL disappear from the list immediately.

### Requirement 5 — API Endpoints for Script CRUD

**User Story:** As a developer, I want REST endpoints for listing, reading, updating, and deleting scripts so that scripts can be managed programmatically.

#### Acceptance Criteria

1. `GET /scripts` SHALL return a JSON array of all saved scripts ordered by most recent first.
2. `GET /scripts/<id>` SHALL return a single script record as JSON (404 if not found).
3. `PUT /scripts/<id>` with `{"transcription": "..."}` SHALL update the transcription text and return the updated record (404 if not found).
4. `DELETE /scripts/<id>` SHALL delete the record and return 204 (404 if not found).

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: Database logic lives in a new `db.py` module — `app.py` and `transcribe.py` remain focused on their existing responsibilities.
- **Modular Design**: `db.py` exposes simple CRUD functions; `app.py` calls them from routes.
- **Clear Interfaces**: `db.py` functions accept/return plain dicts — no ORM objects leak into routes.

### Performance
- SQLite is embedded and requires no server process. Reads/writes for the expected volume (hundreds of scripts) are sub-millisecond.
- The script list endpoint returns all records. Pagination is a non-goal for v1 but the schema supports it via `created_at` ordering.

### Security
- SQL queries use parameterized statements — no string interpolation.
- Script IDs are integers; the API validates that `<id>` is numeric before querying.
- No authentication — the app runs locally and is not exposed to the public internet.

### Reliability
- The database file is created automatically on first use if it doesn't exist.
- Database writes happen after a successful transcription — a crash during write loses only that one record, not the transcription output (which is still displayed in the UI).
- Editing a script overwrites in-place; there is no version history (non-goal for v1).

### Usability
- Scripts are saved automatically — no "Save" button needed after transcription.
- The script library is accessible from the main page without navigating to a separate URL.
- Edit mode uses a standard textarea with Save/Cancel — no rich text editor complexity.
