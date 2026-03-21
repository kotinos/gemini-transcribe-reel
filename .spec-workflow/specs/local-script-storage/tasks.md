# Tasks: Local Script Storage

## 1.0 Database Module

- [ ] 1.1 Create `db.py` with SQLite schema and CRUD functions
  - Create `scripts` table (id, url, transcription, created_at, updated_at)
  - Implement `init_db()`, `get_connection()`, `save_script()`, `get_all_scripts()`, `get_script()`, `update_script()`, `delete_script()`
  - Use parameterized queries for all SQL; `row_factory = sqlite3.Row` for dict-like access
  - _Leverage: Python `sqlite3` stdlib module_
  - _Requirements: 1.1, 5.1, 5.2, 5.3, 5.4_

- [ ] 1.2 Create `test_db.py` with unit tests for all CRUD functions
  - Use `:memory:` SQLite database — no file I/O
  - Tests: `test_init_db_creates_table`, `test_save_script`, `test_get_all_scripts_ordering`, `test_get_all_scripts_empty`, `test_get_script_found`, `test_get_script_not_found`, `test_update_script`, `test_update_script_not_found`, `test_delete_script`, `test_delete_script_not_found`
  - _Requirements: 1.1, 3.2, 4.1, 5.1–5.4_

- [ ] 1.3 Add `scripts.db` to `.gitignore`
  - _Requirements: non-functional (security)_

## 2.0 Backend — Script API Routes

- [ ] 2.1 Call `init_db()` at app startup in `app.py`
  - Add `import db` and call `db.init_db()` alongside existing `load_dotenv()` / `genai.configure()`
  - _Leverage: `app.py` startup pattern_
  - _Requirements: 1.1_

- [ ] 2.2 Add auto-save to `POST /transcribe` route in `app.py`
  - After each successful `process_url()` call, call `db.save_script(url, transcription)`
  - Wrap in try/except so a database error never breaks the transcription response
  - Handle both single-URL and batch paths
  - _Leverage: existing `/transcribe` route, `db.save_script()`_
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 2.3 Add `GET /scripts` route to `app.py`
  - Return JSON array of all scripts via `db.get_all_scripts()`, ordered by most recent first
  - _Leverage: `db.get_all_scripts()`_
  - _Requirements: 2.1, 5.1_

- [ ] 2.4 Add `GET /scripts/<id>` route to `app.py`
  - Return single script as JSON; 404 if not found
  - Validate that `id` is an integer
  - _Leverage: `db.get_script()`_
  - _Requirements: 2.3, 5.2_

- [ ] 2.5 Add `PUT /scripts/<id>` route to `app.py`
  - Accept `{"transcription": "..."}`, update record, return updated dict; 400 if no transcription, 404 if not found
  - _Leverage: `db.update_script()`_
  - _Requirements: 3.1, 3.2, 3.4, 5.3_

- [ ] 2.6 Add `DELETE /scripts/<id>` route to `app.py`
  - Delete record, return 204; 404 if not found
  - _Leverage: `db.delete_script()`_
  - _Requirements: 4.1, 4.2, 5.4_

- [ ] 2.7 Add route tests to `test_app.py`
  - Add `TestScriptsEndpoints` class with tests: `test_get_scripts_empty`, `test_get_scripts_with_data`, `test_get_script_by_id`, `test_get_script_not_found`, `test_update_script_success`, `test_update_script_no_body`, `test_update_script_not_found`, `test_delete_script_success`, `test_delete_script_not_found`, `test_transcribe_auto_saves`
  - _Requirements: 1.1, 5.1–5.4_

## 3.0 Frontend — Script Library UI

- [ ] 3.1 Add script library section to `templates/index.html`
  - Collapsible "Saved Scripts" section below the transcription form
  - Fetch and display scripts on page load via `GET /scripts`
  - Show empty state ("No saved scripts yet") when list is empty
  - Each card shows URL, transcription preview (~100 chars), and timestamp
  - _Requirements: 2.1, 2.2_

- [ ] 3.2 Add "View full" interaction to script cards
  - Clicking a card expands it to show the full transcription text
  - _Requirements: 2.3_

- [ ] 3.3 Add Edit functionality to script cards
  - Edit button switches card to textarea + Save/Cancel buttons
  - Save sends `PUT /scripts/<id>` and updates card on success
  - Cancel reverts to previous text without API call
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 3.4 Add Delete functionality to script cards
  - Delete button sends `DELETE /scripts/<id>` and removes card from DOM on success
  - _Requirements: 4.1, 4.2_

- [ ] 3.5 Auto-refresh script library after new transcription
  - After `POST /transcribe` returns successfully, re-fetch the script list so new entries appear
  - _Requirements: 1.1_

## 4.0 Verification

- [ ] 4.1 Run full test suite: `pytest test_transcribe.py test_app.py test_db.py -v --tb=short`
- [ ] 4.2 Confirm all existing tests still pass (no regressions) and all new tests pass
- [ ] 4.3 Manual smoke test: transcribe a URL, verify it appears in script library, edit the text, delete it

## Definition of Done

- [ ] `db.py` exists with SQLite CRUD functions and parameterized queries
- [ ] `scripts.db` is gitignored
- [ ] Auto-save works: transcription results appear in script library without manual action
- [ ] Scripts are editable from the UI (textarea + Save/Cancel)
- [ ] Scripts are deletable from the UI
- [ ] All new and existing tests pass
- [ ] No changes to `transcribe.py` — storage is handled entirely at the `app.py` layer
