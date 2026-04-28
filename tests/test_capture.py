# tests/test_capture.py — TDD for llm-wiki capture subcommand
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers to build fixture jsonl files in-memory
# ---------------------------------------------------------------------------

def _make_jsonl(lines: list[dict], path: Path) -> Path:
    """Write list of dicts as newline-delimited JSON file."""
    path.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    return path


def _session_header(cwd: str) -> dict:
    """First line of a session jsonl — cwd field."""
    return {"cwd": cwd, "sessionId": "test-session-uuid", "ts": "2026-04-28T00:00:00Z"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_cwd(tmp_path: Path) -> Path:
    return tmp_path / "myproject"


@pytest.fixture
def wiki_out(tmp_path: Path) -> Path:
    out = tmp_path / "wiki-out"
    out.mkdir()
    return out


@pytest.fixture
def fixture_rationale(tmp_path: Path, project_cwd: Path) -> Path:
    """Session with a clear rationale message — should produce 1 candidate."""
    path = tmp_path / "session_rationale.jsonl"
    _make_jsonl([
        _session_header(str(project_cwd)),
        {
            "role": "user",
            "content": (
                "I decided to use JSON over YAML because the JSON format is "
                "supported natively and the rationale is that YAML has many edge "
                "cases with indentation that caused issues previously."
            ),
            "ts": "2026-04-28T10:00:00Z",
        },
    ], path)
    return path


@pytest.fixture
def fixture_secret(tmp_path: Path, project_cwd: Path) -> Path:
    """Session with a message containing a secret token — should produce 0 candidates."""
    path = tmp_path / "session_secret.jsonl"
    _make_jsonl([
        _session_header(str(project_cwd)),
        {
            "role": "user",
            "content": (
                "The design choice here is important. I decided to use sk-abcdefghij1234567890XYZ "
                "as the API key because this rationale makes the integration straightforward."
            ),
            "ts": "2026-04-28T10:01:00Z",
        },
    ], path)
    return path


@pytest.fixture
def fixture_short(tmp_path: Path, project_cwd: Path) -> Path:
    """Session with user message shorter than 50 chars — should produce 0 candidates."""
    path = tmp_path / "session_short.jsonl"
    _make_jsonl([
        _session_header(str(project_cwd)),
        {
            "role": "user",
            "content": "ok decided",  # <50 chars
            "ts": "2026-04-28T10:02:00Z",
        },
    ], path)
    return path


@pytest.fixture
def fixture_tool_only(tmp_path: Path, project_cwd: Path) -> Path:
    """Session with only tool/assistant messages — should produce 0 candidates."""
    path = tmp_path / "session_tool_only.jsonl"
    _make_jsonl([
        _session_header(str(project_cwd)),
        {
            "role": "assistant",
            "content": (
                "I decided to use JSON because it is natively supported and the "
                "rationale is that it has fewer edge cases than YAML for our use."
            ),
            "ts": "2026-04-28T10:03:00Z",
        },
    ], path)
    return path


@pytest.fixture
def fixture_no_keyword(tmp_path: Path, project_cwd: Path) -> Path:
    """User message long enough but no decision/rationale keyword — 0 candidates."""
    path = tmp_path / "session_no_keyword.jsonl"
    _make_jsonl([
        _session_header(str(project_cwd)),
        {
            "role": "user",
            "content": (
                "Please refactor the authentication module so that it separates "
                "concerns properly. The login logic should go into a service layer "
                "and we need to update all unit tests accordingly."
            ),
            "ts": "2026-04-28T10:04:00Z",
        },
    ], path)
    return path


# ---------------------------------------------------------------------------
# Import capture module (lazy, so we can test prior to full implementation)
# ---------------------------------------------------------------------------

def _import_capture():
    import importlib
    return importlib.import_module("my_llm_wiki.capture")


# ---------------------------------------------------------------------------
# Tests: enable-flag gate
# ---------------------------------------------------------------------------

class TestEnableFlag:
    def test_check_enabled_false_when_no_flag(self, wiki_out: Path):
        cap = _import_capture()
        assert cap._check_enabled(wiki_out) is False

    def test_enable_creates_flag_file(self, wiki_out: Path):
        cap = _import_capture()
        cap._enable(wiki_out)
        flag = wiki_out / "cache" / "capture-enabled"
        assert flag.exists()

    def test_check_enabled_true_after_enable(self, wiki_out: Path):
        cap = _import_capture()
        cap._enable(wiki_out)
        assert cap._check_enabled(wiki_out) is True

    def test_enable_is_idempotent(self, wiki_out: Path):
        cap = _import_capture()
        cap._enable(wiki_out)
        cap._enable(wiki_out)  # second call should not raise
        assert cap._check_enabled(wiki_out) is True


# ---------------------------------------------------------------------------
# Tests: filter pipeline — _iter_candidates
# ---------------------------------------------------------------------------

class TestFilterPipeline:
    def test_rationale_message_yields_one_candidate(self, fixture_rationale: Path):
        cap = _import_capture()
        candidates = list(cap._iter_candidates(fixture_rationale))
        assert len(candidates) == 1
        assert "rationale" in candidates[0]["text"].lower() or "decided" in candidates[0]["text"].lower()

    def test_secret_bearing_yields_zero(self, fixture_secret: Path):
        cap = _import_capture()
        candidates = list(cap._iter_candidates(fixture_secret))
        assert len(candidates) == 0

    def test_short_message_yields_zero(self, fixture_short: Path):
        cap = _import_capture()
        candidates = list(cap._iter_candidates(fixture_short))
        assert len(candidates) == 0

    def test_tool_only_yields_zero(self, fixture_tool_only: Path):
        cap = _import_capture()
        candidates = list(cap._iter_candidates(fixture_tool_only))
        assert len(candidates) == 0

    def test_no_keyword_yields_zero(self, fixture_no_keyword: Path):
        cap = _import_capture()
        candidates = list(cap._iter_candidates(fixture_no_keyword))
        assert len(candidates) == 0

    def test_candidate_has_required_fields(self, fixture_rationale: Path):
        cap = _import_capture()
        c = list(cap._iter_candidates(fixture_rationale))[0]
        assert "text" in c
        assert "ts" in c
        assert "session" in c


# ---------------------------------------------------------------------------
# Tests: secret patterns
# ---------------------------------------------------------------------------

class TestSecretDetection:
    def _has_secret(self, text: str) -> bool:
        cap = _import_capture()
        return cap._has_secret(text)

    def test_openai_key_detected(self):
        assert self._has_secret("key: sk-abcdefghijklmnopqrst12345") is True

    def test_github_pat_detected(self):
        assert self._has_secret("token: ghp_abc1234567890abcdefghijklm") is True

    def test_aws_key_detected(self):
        assert self._has_secret("AKIAIOSFODNN7EXAMPLE") is True

    def test_slack_token_detected(self):
        assert self._has_secret("xoxb-123456789-987654321-abcdef") is True

    def test_long_base64_blob_detected(self):
        blob = "A" * 40 + "BBBBcccc===="
        assert self._has_secret(blob) is True

    def test_normal_text_clean(self):
        assert self._has_secret("I decided to use JSON because it is simpler.") is False


# ---------------------------------------------------------------------------
# Tests: suggestion helpers
# ---------------------------------------------------------------------------

class TestSuggestions:
    def test_suggest_tags_decision_keyword(self):
        cap = _import_capture()
        tags = cap._suggest_tags("I decided to use JSON for the storage format.")
        assert "decision" in tags

    def test_suggest_tags_rationale_keyword(self):
        cap = _import_capture()
        tags = cap._suggest_tags("The rationale is that YAML has edge cases.")
        assert "rationale" in tags

    def test_suggest_tags_tradeoff_keyword(self):
        cap = _import_capture()
        tags = cap._suggest_tags("There is a trade-off between simplicity and flexibility.")
        assert "tradeoff" in tags

    def test_suggest_links_no_graph(self, tmp_path: Path):
        cap = _import_capture()
        links = cap._suggest_links("mention of [[SomeNode]] in text", graph_path=None)
        assert "SomeNode" in links

    def test_suggest_links_from_graph(self, tmp_path: Path):
        cap = _import_capture()
        graph = {
            "nodes": [
                {"id": "n1", "label": "AuthModule"},
                {"id": "n2", "label": "GraphStore"},
            ],
            "links": [],
        }
        gp = tmp_path / "graph.json"
        gp.write_text(json.dumps(graph), encoding="utf-8")
        text = "We need to update AuthModule to integrate with the new system."
        links = cap._suggest_links(text, graph_path=gp)
        assert "AuthModule" in links


# ---------------------------------------------------------------------------
# Tests: output writer
# ---------------------------------------------------------------------------

class TestOutputWriter:
    def test_write_pending_creates_file(self, tmp_path: Path):
        cap = _import_capture()
        candidates = [
            {
                "ts": "2026-04-28T10:00:00Z",
                "session": "abcd1234",
                "text": "I decided to use JSON because rationale is simplicity.",
                "suggested_links": ["GraphStore"],
                "suggested_tags": ["decision"],
            }
        ]
        out = tmp_path / "pending-notes.md"
        cap._write_pending(candidates, out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "abcd1234" in content
        assert "GraphStore" in content
        assert "decision" in content

    def test_write_pending_empty_candidates(self, tmp_path: Path):
        cap = _import_capture()
        out = tmp_path / "pending-notes.md"
        cap._write_pending([], out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "no candidates" in content.lower()


# ---------------------------------------------------------------------------
# Tests: main capture() function — enable-flag gate
# ---------------------------------------------------------------------------

class TestCaptureFunctionGate:
    def test_capture_exits_nonzero_without_flag(self, tmp_path: Path, capsys):
        cap = _import_capture()
        wiki_out = tmp_path / "wiki-out"
        wiki_out.mkdir()
        with pytest.raises(SystemExit) as exc_info:
            cap.capture(
                project_cwd=tmp_path,
                wiki_out=wiki_out,
                since_hours=24,
                enable=False,
                claude_home=tmp_path / "no-such-dir",
            )
        assert exc_info.value.code != 0
        captured = capsys.readouterr()
        assert "enable" in captured.out.lower() or "enable" in captured.err.lower()

    def test_capture_enable_flag_sets_flag(self, tmp_path: Path, capsys):
        cap = _import_capture()
        wiki_out = tmp_path / "wiki-out"
        wiki_out.mkdir()
        cap.capture(
            project_cwd=tmp_path,
            wiki_out=wiki_out,
            since_hours=24,
            enable=True,
            claude_home=tmp_path / "no-such-dir",
        )
        assert cap._check_enabled(wiki_out) is True

    def test_capture_runs_with_flag_no_sessions(self, tmp_path: Path, capsys):
        """With flag set but no sessions directory, should exit 0 with no-candidates message."""
        cap = _import_capture()
        wiki_out = tmp_path / "wiki-out"
        wiki_out.mkdir()
        cap._enable(wiki_out)
        # Run with a nonexistent claude_home — no sessions
        cap.capture(
            project_cwd=tmp_path,
            wiki_out=wiki_out,
            since_hours=24,
            enable=False,
            claude_home=tmp_path / "no-such-claude",
        )
        captured = capsys.readouterr()
        assert "no candidates" in captured.out.lower() or (wiki_out / "captured" / "pending-notes.md").exists()
