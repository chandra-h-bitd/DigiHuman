import pytest
from app.main import normalize_text, smart_chunk, approx_tokens


def test_normalize_text_basic():
    text = "Header\n1\n\nThis is   a   test.\n\n2\nFooter"
    out = normalize_text(text)
    assert "This is a test." in out
    assert "Header" not in out


def test_smart_chunk_small():
    text = "This is a short paragraph." * 10
    chunks = smart_chunk(text, "doc.pdf")
    assert len(chunks) >= 1
    assert all('text' in c for c in chunks)


def test_approx_tokens():
    assert approx_tokens("hello world") == 2
