"""
Tests for save_to_loreconvo.py -- fallback LoreConvo script.

Covers: --read-id flag, --search, --read, save workflow,
and the error-surface support added in commit 6e8fc5a.

MEG-NNN reference: new tests added 2026-04-06.
"""
import json
import sqlite3
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
import argparse
import pytest

# Locate script under test
SCRIPTS_ROOT = Path(__file__).resolve().parent.parent.parent / "ron_skills" / "loreconvo" / "scripts"
SCRIPT_PATH = SCRIPTS_ROOT / "save_to_loreconvo.py"

# Also support the monorepo-root copy
MONO_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "save_to_loreconvo.py"

sys.path.insert(0, str(SCRIPTS_ROOT))


def _make_temp_db():
    """Create a minimal LoreConvo SQLite DB for testing (mirrors real schema)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            surface TEXT,
            project TEXT,
            title TEXT,
            summary TEXT,
            decisions TEXT,
            artifacts TEXT,
            open_questions TEXT,
            tags TEXT,
            start_date TEXT,
            end_date TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        INSERT INTO sessions (id, surface, project, title, summary, decisions, tags)
        VALUES (
            'test-uuid-1234-abcd-5678',
            'qa',
            'side_hustle',
            'Meg QA test session',
            'Test summary content here.',
            '["Decision A", "Decision B"]',
            '["agent:meg"]'
        )
    """)
    conn.execute("""
        INSERT INTO sessions (id, surface, project, title, summary, tags)
        VALUES (
            'error-uuid-9999-xxxx-0000',
            'error',
            'side_hustle',
            'agent:meg error 2026-04-06',
            'ERROR: test failure | IMPACT: none | CONTEXT: test only',
            '["agent:meg", "error"]'
        )
    """)
    conn.commit()
    conn.close()
    return tmp.name


@pytest.fixture
def temp_db():
    db_path = _make_temp_db()
    yield db_path
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Import the script module dynamically
# ---------------------------------------------------------------------------

import importlib.util

def _load_script(path):
    spec = importlib.util.spec_from_file_location("save_to_loreconvo", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def script():
    return _load_script(SCRIPT_PATH)


# ---------------------------------------------------------------------------
# Tests: read_session_by_id (new --read-id flag)
# ---------------------------------------------------------------------------

class TestReadById:
    """MEG-048: Tests for the new --read-id flag added in commit 6e8fc5a."""

    def test_read_existing_id_prints_output(self, script, temp_db, capsys):
        args = argparse.Namespace(
            read_id="test-uuid-1234-abcd-5678",
            db_path=temp_db,
        )
        script.read_session_by_id(args)
        out = capsys.readouterr().out
        assert "Meg QA test session" in out
        assert "test-uuid-1234-abcd-5678" in out
        assert "Test summary content here." in out

    def test_read_existing_id_shows_decisions(self, script, temp_db, capsys):
        args = argparse.Namespace(
            read_id="test-uuid-1234-abcd-5678",
            db_path=temp_db,
        )
        script.read_session_by_id(args)
        out = capsys.readouterr().out
        assert "Decision A" in out
        assert "Decision B" in out

    def test_read_existing_id_shows_project(self, script, temp_db, capsys):
        args = argparse.Namespace(
            read_id="test-uuid-1234-abcd-5678",
            db_path=temp_db,
        )
        script.read_session_by_id(args)
        out = capsys.readouterr().out
        assert "side_hustle" in out

    def test_read_nonexistent_id_exits_with_error(self, script, temp_db):
        args = argparse.Namespace(
            read_id="does-not-exist-uuid",
            db_path=temp_db,
        )
        with pytest.raises(SystemExit) as exc_info:
            script.read_session_by_id(args)
        assert exc_info.value.code == 1

    def test_read_error_surface_session(self, script, temp_db, capsys):
        """Error-surface sessions are stored and retrievable by ID."""
        args = argparse.Namespace(
            read_id="error-uuid-9999-xxxx-0000",
            db_path=temp_db,
        )
        script.read_session_by_id(args)
        out = capsys.readouterr().out
        assert "error" in out.lower()
        assert "agent:meg error" in out


# ---------------------------------------------------------------------------
# Tests: error surface support in --surface arg
# ---------------------------------------------------------------------------

class TestErrorSurface:
    """MEG-049: Verify the 'error' surface is accepted and saved correctly."""

    def test_error_surface_saves_to_db(self, script, temp_db):
        args = argparse.Namespace(
            title="agent:meg error test",
            surface="error",
            summary="ERROR: test | IMPACT: none | CONTEXT: unit test",
            project="side_hustle",
            decisions=None,
            artifacts=None,
            open_questions=None,
            tags='["agent:meg", "error"]',
            start_date=None,
            end_date=None,
            db_path=temp_db,
        )
        script.save_session(args)
        conn = sqlite3.connect(temp_db)
        row = conn.execute(
            "SELECT surface, title FROM sessions WHERE surface='error' AND title LIKE '%meg error test%'"
        ).fetchone()
        conn.close()
        assert row is not None, "Error-surface session was not saved to the database"
        assert row[0] == "error"

    def test_pipeline_surface_saves_to_db(self, script, temp_db):
        args = argparse.Namespace(
            title="pipeline test session",
            surface="pipeline",
            summary="Pipeline scan results.",
            project="side_hustle",
            decisions=None,
            artifacts=None,
            open_questions=None,
            tags='["agent:scout"]',
            start_date=None,
            end_date=None,
            db_path=temp_db,
        )
        script.save_session(args)
        conn = sqlite3.connect(temp_db)
        row = conn.execute(
            "SELECT surface FROM sessions WHERE surface='pipeline'"
        ).fetchone()
        conn.close()
        assert row is not None, "Pipeline-surface session was not saved"


# ---------------------------------------------------------------------------
# Tests: read_sessions with surface filter
# ---------------------------------------------------------------------------

class TestReadSessions:
    """Basic smoke tests for --read flag."""

    def test_read_returns_qa_sessions(self, script, temp_db, capsys):
        args = argparse.Namespace(
            surface="qa",
            limit=5,
            db_path=temp_db,
        )
        script.read_sessions(args)
        out = capsys.readouterr().out
        assert "Meg QA test session" in out

    def test_read_filters_by_surface(self, script, temp_db, capsys):
        args = argparse.Namespace(
            surface="cowork",
            limit=5,
            db_path=temp_db,
        )
        script.read_sessions(args)
        out = capsys.readouterr().out
        # cowork sessions not present in temp db
        assert "Meg QA test session" not in out


# ---------------------------------------------------------------------------
# Tests: search_sessions
# ---------------------------------------------------------------------------

class TestSearchSessions:
    """Smoke tests for --search flag."""

    def test_search_finds_matching_session(self, script, temp_db, capsys):
        args = argparse.Namespace(
            search="Test summary content",
            limit=10,
            db_path=temp_db,
        )
        script.search_sessions(args)
        out = capsys.readouterr().out
        assert "Meg QA test session" in out

    def test_search_returns_nothing_for_nonmatch(self, script, temp_db, capsys):
        args = argparse.Namespace(
            search="xyzzy_no_match_12345",
            limit=10,
            db_path=temp_db,
        )
        script.search_sessions(args)
        out = capsys.readouterr().out
        assert "Meg QA test session" not in out
