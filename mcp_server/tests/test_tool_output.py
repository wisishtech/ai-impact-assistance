"""search_evidence output: readable citation text for Copilot + structured passages for code clients."""
from iea_mcp.server import ORIGINS, passages_result

HIT = {"doc_id": "IREX-2015-EV-003", "title": "Women and Technology", "url": "https://www.irex.org/x",
       "page": 6, "section": "Findings", "content": "Girls choose libraries because they feel safe."}


def test_text_starts_with_citation_not_json():
    r = passages_result([HIT])
    text = r.content[0].text
    assert text.startswith("Women and Technology, page 6 (https://www.irex.org/x)")
    assert not text.lstrip().startswith("{")


def test_structured_content_keeps_fields():
    r = passages_result([HIT, {**HIT, "page": 7}])
    assert [p["page"] for p in r.structuredContent["passages"]] == [6, 7]
    assert len(r.content) == 2


def test_no_hits():
    r = passages_result([])
    assert r.structuredContent == {"passages": []}
    assert "No passages" in r.content[0].text


def test_origins_parsed():
    assert all(o.startswith("http") for o in ORIGINS)