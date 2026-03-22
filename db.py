#!/usr/bin/env python3
"""
SQLite storage for transcription scripts.
All CRUD operations for the scripts table.
"""

import sqlite3

DB_PATH = 'scripts.db'


def init_db(db_path=None):
    """Create the scripts table if it doesn't exist."""
    conn = get_connection(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            transcription TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')
    conn.commit()
    conn.close()


def get_connection(db_path=None):
    """Return a connection with Row factory."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)


def save_script(url, transcription, db_path=None):
    """Insert a new script record. Returns the created record as a dict."""
    conn = get_connection(db_path)
    cursor = conn.execute(
        'INSERT INTO scripts (url, transcription) VALUES (?, ?)',
        (url, transcription)
    )
    script_id = cursor.lastrowid
    conn.commit()
    row = conn.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_all_scripts(db_path=None):
    """Return all scripts ordered by created_at DESC."""
    conn = get_connection(db_path)
    rows = conn.execute('SELECT * FROM scripts ORDER BY id DESC').fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_script(script_id, db_path=None):
    """Return a single script by ID, or None if not found."""
    conn = get_connection(db_path)
    row = conn.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def update_script(script_id, transcription, db_path=None):
    """Update a script's transcription. Returns updated dict or None if not found."""
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE scripts SET transcription = ?, updated_at = datetime('now') WHERE id = ?",
        (transcription, script_id)
    )
    conn.commit()
    row = conn.execute('SELECT * FROM scripts WHERE id = ?', (script_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def delete_script(script_id, db_path=None):
    """Delete a script by ID. Returns True if deleted, False if not found."""
    conn = get_connection(db_path)
    cursor = conn.execute('DELETE FROM scripts WHERE id = ?', (script_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0
