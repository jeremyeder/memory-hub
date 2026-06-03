"""Tests for compact output formatting."""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

from memoryhub_cli.main import _print_compact


def _capture_compact(memories, project_id=None) -> str:
    """Call _print_compact and capture stdout."""
    import sys
    buf = StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        _print_compact(memories, project_id)
    finally:
        sys.stdout = old
    return buf.getvalue()


class TestPrintCompact:
    def test_basic_output(self):
        mems = [
            SimpleNamespace(content="Use Podman, not Docker", stub=None),
            SimpleNamespace(content="FIPS compliance required", stub=None),
        ]
        out = _capture_compact(mems, "memory-hub")
        assert '<memoryhub-context project="memory-hub">' in out
        assert "- Use Podman, not Docker" in out
        assert "- FIPS compliance required" in out
        assert "</memoryhub-context>" in out

    def test_no_project_id(self):
        mems = [SimpleNamespace(content="some memory", stub=None)]
        out = _capture_compact(mems)
        assert "<memoryhub-context>" in out
        assert 'project=' not in out

    def test_stub_fallback(self):
        mems = [SimpleNamespace(content=None, stub="stub text here")]
        out = _capture_compact(mems)
        assert "- stub text here" in out

    def test_empty_memories(self):
        out = _capture_compact([])
        assert "<memoryhub-context>" in out
        assert "</memoryhub-context>" in out
        lines = out.strip().splitlines()
        assert len(lines) == 2

    def test_multiline_content(self):
        mems = [SimpleNamespace(content="line one\nline two", stub=None)]
        out = _capture_compact(mems)
        assert "- line one" in out
        assert "- line two" in out

    def test_no_metadata_in_output(self):
        mems = [SimpleNamespace(
            content="the memory text",
            stub=None,
            id="abc-123",
            weight=0.9,
            scope="project",
        )]
        out = _capture_compact(mems)
        assert "abc-123" not in out
        assert "0.9" not in out
        assert "scope" not in out
        assert "- the memory text" in out
