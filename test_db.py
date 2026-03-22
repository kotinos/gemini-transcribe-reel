#!/usr/bin/env python3
"""
Unit tests for db.py SQLite CRUD functions.
All tests use in-memory SQLite — no file I/O.
Run with: python -m pytest test_db.py -v
"""

import pytest
import db


@pytest.fixture
def mem_db(tmp_path):
    """Initialize an in-memory database and return its path."""
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    return db_path


class TestDatabase:
    """Test all db.py CRUD functions"""

    def test_init_db_creates_table(self, mem_db):
        """init_db creates the scripts table"""
        conn = db.get_connection(mem_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scripts'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_save_script(self, mem_db):
        """save_script returns a dict with all expected fields"""
        result = db.save_script('https://example.com/video', 'Hello world', mem_db)
        assert result['id'] == 1
        assert result['url'] == 'https://example.com/video'
        assert result['transcription'] == 'Hello world'
        assert result['created_at'] is not None
        assert result['updated_at'] is not None

    def test_get_all_scripts_ordering(self, mem_db):
        """get_all_scripts returns most recent first"""
        db.save_script('https://example.com/1', 'First', mem_db)
        db.save_script('https://example.com/2', 'Second', mem_db)
        scripts = db.get_all_scripts(mem_db)
        assert len(scripts) == 2
        assert scripts[0]['url'] == 'https://example.com/2'
        assert scripts[1]['url'] == 'https://example.com/1'

    def test_get_all_scripts_empty(self, mem_db):
        """get_all_scripts returns empty list when no records"""
        scripts = db.get_all_scripts(mem_db)
        assert scripts == []

    def test_get_script_found(self, mem_db):
        """get_script returns correct record by ID"""
        saved = db.save_script('https://example.com/video', 'Content', mem_db)
        result = db.get_script(saved['id'], mem_db)
        assert result['id'] == saved['id']
        assert result['url'] == 'https://example.com/video'
        assert result['transcription'] == 'Content'

    def test_get_script_not_found(self, mem_db):
        """get_script returns None for nonexistent ID"""
        result = db.get_script(999, mem_db)
        assert result is None

    def test_update_script(self, mem_db):
        """update_script changes transcription text"""
        saved = db.save_script('https://example.com/video', 'Original', mem_db)
        updated = db.update_script(saved['id'], 'Edited text', mem_db)
        assert updated['transcription'] == 'Edited text'
        assert updated['url'] == 'https://example.com/video'

    def test_update_script_not_found(self, mem_db):
        """update_script returns None for nonexistent ID"""
        result = db.update_script(999, 'Text', mem_db)
        assert result is None

    def test_delete_script(self, mem_db):
        """delete_script removes the record and returns True"""
        saved = db.save_script('https://example.com/video', 'Content', mem_db)
        assert db.delete_script(saved['id'], mem_db) is True
        assert db.get_script(saved['id'], mem_db) is None

    def test_delete_script_not_found(self, mem_db):
        """delete_script returns False for nonexistent ID"""
        assert db.delete_script(999, mem_db) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
