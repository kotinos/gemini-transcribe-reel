# Design: Local Script Storage

## Overview

A new `db.py` module introduces SQLite-backed persistence for transcription results. Scripts are auto-saved after successful transcription and are viewable, editable, and deletable from the web UI. The database file lives alongside the application (`scripts.db`) and requires no setup — SQLite creates it on first access.

## Steering Document Alignment

### Technical Standards (tech.md)
- **Python-native storage**: SQLite ships with Python's standard library (`sqlite3`) — no new dependencies.
- **Stateless core preserved**: `transcribe.py` remains unchanged. Storage is a side-effect handled by `app.py` after `process_url()` returns.
- **Same error code contract**: Storage errors do not affect transcription exit codes (0–7). A database write failure is logged but does not fail the transcription response.
- **Testing**: All database logic is unit-tested with an in-memory SQLite database — no file I/O in tests.

### Project Structure (structure.md)
- `db.py` — new module (~80 lines), all database CRUD logic.
- `app.py` — add 4 routes (`GET /scripts`, `GET /scripts/<id>`, `PUT /scripts/<id>`, `DELETE /scripts/<id>`), add auto-save calls after transcription.
- `templates/index.html` — add script library section and edit UI.
- `test_db.py` — new test file for database CRUD.
- `test_app.py` — add tests for the 4 new routes.
- `scripts.db` — SQLite database file (gitignored).

## Code Reuse Analysis

### Existing Components to Leverage
- **`app.py` `/transcribe` route**: The auto-save hook is added inside the existing response path — after `process_url()` returns a successful result, call `db.save_script()`.
- **`templates/index.html` result card markup**: The script library list reuses the same visual style as batch result cards (bordered cards with URL headers).

### Integration Points
- **`POST /transcribe` route**: After a successful transcription, `db.save_script(url, transcription)` is called before the JSON response is returned.
- **`POST /regenerate` route** (if implemented): Same auto-save pattern — save/update after successful regeneration.

## Architecture

### Module Responsibilities

| Module | Change | Responsibility |
|--------|--------|----------------|
| `db.py` | **New** | SQLite connection management, schema init, CRUD functions |
| `app.py` | **Modified** | New routes for scripts API, auto-save after transcription |
| `templates/index.html` | **Modified** | Script library section, edit/delete UI, JS handlers |
| `transcribe.py` | **No change** | Core transcription logic — unaware of storage |

### Data Flow — Save on Transcription

```
POST /transcribe { urls: [...] }
  │
  ▼
app.py processes URLs via process_url()
  │
  ▼
For each successful result:
  ├── db.save_script(url, transcription)  ← NEW
  └── append to response JSON
  │
  ▼
Return JSON response (unchanged shape)
```

### Data Flow — Script Library

```
Page load or "View Scripts" click
  │
  ▼
JS sends GET /scripts
  │
  ▼
app.py calls db.get_all_scripts()
  │
  ▼
Return JSON [ {id, url, transcription, created_at, updated_at}, ... ]
  │
  ▼
JS renders script list in library section
```

### Data Flow — Edit Script

```
User clicks Edit on a script card
  │
  ▼
UI switches to editable textarea
  │
  ▼
User modifies text, clicks Save
  │
  ▼
JS sends PUT /scripts/<id> { transcription: "..." }
  │
  ▼
app.py calls db.update_script(id, transcription)
  │
  ▼
Return updated record JSON
  │
  ▼
JS updates card with new text, exits edit mode
```

## Data Model

### `scripts` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique record identifier |
| `url` | TEXT | NOT NULL | Source video URL |
| `transcription` | TEXT | NOT NULL | Transcription text (editable) |
| `created_at` | TEXT | NOT NULL, DEFAULT `datetime('now')` | ISO 8601 timestamp of initial save |
| `updated_at` | TEXT | NOT NULL, DEFAULT `datetime('now')` | ISO 8601 timestamp of last edit |

### Schema SQL

```sql
CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    transcription TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## Components and Interfaces

### `db.py` — Database Module

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `init_db()` | `(db_path: str = 'scripts.db') → None` | None | Create database and `scripts` table if they don't exist |
| `get_connection()` | `() → sqlite3.Connection` | Connection | Return a connection with `row_factory = sqlite3.Row` |
| `save_script(url, transcription)` | `(str, str) → dict` | `{id, url, transcription, created_at, updated_at}` | Insert a new script record |
| `get_all_scripts()` | `() → list[dict]` | List of script dicts | All scripts ordered by `created_at DESC` |
| `get_script(script_id)` | `(int) → dict \| None` | Script dict or `None` | Single script by ID |
| `update_script(script_id, transcription)` | `(int, str) → dict \| None` | Updated dict or `None` | Update transcription text and `updated_at` |
| `delete_script(script_id)` | `(int) → bool` | `True` if deleted, `False` if not found | Delete script by ID |

### New Routes — `app.py`

| Method | Path | Request | Success Response | Error Response |
|--------|------|---------|------------------|----------------|
| GET | `/scripts` | — | 200: `[{id, url, transcription, created_at, updated_at}, ...]` | — |
| GET | `/scripts/<id>` | — | 200: `{id, url, transcription, created_at, updated_at}` | 404: `{"error": "Script not found"}` |
| PUT | `/scripts/<id>` | `{"transcription": "..."}` | 200: updated script dict | 400: missing transcription, 404: not found |
| DELETE | `/scripts/<id>` | — | 204: no body | 404: `{"error": "Script not found"}` |

### UI Components — `templates/index.html`

| Component | Description |
|-----------|-------------|
| **Script Library section** | Collapsible section below the transcription form showing saved scripts |
| **Script card** | Card with URL header, transcription preview text, timestamp, Edit and Delete buttons |
| **Edit mode** | Replaces preview text with a textarea + Save/Cancel buttons |
| **Empty state** | "No saved scripts yet" message when the library is empty |

## Error Handling

### Error Scenarios

| Scenario | Handling | User Impact |
|----------|----------|-------------|
| Database file cannot be created (permissions) | `init_db()` raises exception; app logs error and continues without storage | Transcription still works; scripts are not saved; console warning printed |
| Save fails after transcription | Exception caught in route; transcription response still returned normally | User sees transcription result but it won't appear in script library |
| `PUT /scripts/<id>` with nonexistent ID | `update_script()` returns `None`; route returns 404 | Error message displayed in UI |
| `DELETE /scripts/<id>` with nonexistent ID | `delete_script()` returns `False`; route returns 404 | Error message displayed in UI |
| `PUT /scripts/<id>` with empty transcription | Route returns 400 before calling `update_script()` | Validation error shown in UI |

**Key invariant**: Database failures never break transcription. Storage is a best-effort enhancement — the core transcription pipeline is unaffected.

## Testing Strategy

### Unit Tests — `test_db.py`

| Test | Verifies |
|------|----------|
| `test_init_db_creates_table` | Table exists after `init_db()` |
| `test_save_script` | Returns dict with all fields; record retrievable |
| `test_get_all_scripts_ordering` | Most recent first |
| `test_get_all_scripts_empty` | Returns empty list when no records |
| `test_get_script_found` | Returns correct record by ID |
| `test_get_script_not_found` | Returns `None` for nonexistent ID |
| `test_update_script` | Text changes; `updated_at` advances |
| `test_update_script_not_found` | Returns `None` for nonexistent ID |
| `test_delete_script` | Record removed; returns `True` |
| `test_delete_script_not_found` | Returns `False` for nonexistent ID |

All tests use `sqlite3.connect(':memory:')` — no file I/O.

### Route Tests — `test_app.py`

| Test | Verifies |
|------|----------|
| `test_get_scripts_empty` | 200 with `[]` |
| `test_get_scripts_with_data` | 200 with records in descending order |
| `test_get_script_by_id` | 200 with correct record |
| `test_get_script_not_found` | 404 |
| `test_update_script_success` | 200 with updated text |
| `test_update_script_no_body` | 400 |
| `test_update_script_not_found` | 404 |
| `test_delete_script_success` | 204 |
| `test_delete_script_not_found` | 404 |
| `test_transcribe_auto_saves` | After POST `/transcribe`, record exists in DB |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Database file grows indefinitely | Disk usage increases over time | SQLite handles large files well; user can delete scripts from UI; future: add bulk delete |
| Concurrent writes from multiple browser tabs | Potential `SQLITE_BUSY` errors | SQLite WAL mode handles typical concurrency; Flask dev server is single-threaded anyway |
| User expects cloud sync or multi-device access | Confusion about "local" storage | UI clearly labels the library as "Local Scripts" — data stays on this machine |
| Database file accidentally committed to git | Leaks user data | Add `scripts.db` to `.gitignore` |

## Rollout Notes

- Add `scripts.db` to `.gitignore`.
- `init_db()` is called once at app startup in `app.py` (alongside `load_dotenv()` and `genai.configure()`).
- No migration system needed — single table, single schema version. If schema changes are needed later, a version table can be added.
