from __future__ import annotations

import pytest

from mechdsl_workbench.compiler.diagnostics import build_source_excerpt, normalize_exception

pytestmark = pytest.mark.unit


class LocatedParseError(Exception):
    line = 3
    column = 2


def test_source_excerpt_marks_location() -> None:
    source = "one\ntwo\nthree\nfour\nfive"
    excerpt = build_source_excerpt(source, 3, 2)
    assert "> 3 | three" in excerpt
    assert "^" in excerpt


def test_normalize_exception_uses_explicit_location_attributes() -> None:
    diagnostic = normalize_exception(LocatedParseError("broken"), source="a\nb\nc")
    assert diagnostic.line == 3
    assert diagnostic.column == 2
    assert diagnostic.message == "broken"
    assert diagnostic.source_excerpt is not None


def test_normalize_does_not_invent_location_from_message() -> None:
    diagnostic = normalize_exception(ValueError("failure at line 99 column 7"), source="a\nb")
    assert diagnostic.line is None
    assert diagnostic.column is None
