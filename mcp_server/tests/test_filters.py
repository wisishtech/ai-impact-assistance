from unittest.mock import patch

from iea_mcp import search


def build_body(groups=("g1",), **kwargs):
    """Run search_evidence with Azure mocked out and return the request body it would send."""
    with patch.object(search, "_cred") as cred, patch.object(search.httpx, "post") as post:
        cred.get_token.return_value.token = "fake-token"
        post.return_value.json.return_value = {"value": []}
        post.return_value.raise_for_status = lambda: None
        search.search_evidence("test question", list(groups), **kwargs)
        return post.call_args.kwargs["json"]


def test_group_filter_always_present():
    body = build_body(groups=["g1", "g2"])
    assert "group_ids/any(g: search.in(g, 'g1,g2'))" in body["filter"]


def test_no_groups_means_no_search():
    with patch.object(search.httpx, "post") as post:
        assert search.search_evidence("anything", []) == []
        post.assert_not_called()


def test_quotes_are_escaped():
    body = build_body(country="Cote d'Ivoire")
    assert "country eq 'Cote d''Ivoire'" in body["filter"]


def test_filters_combined_with_and():
    body = build_body(program="Leadership", year_from=2020, language="en")
    f = body["filter"]
    assert "program eq 'Leadership'" in f and "year ge 2020" in f and "language eq 'en'" in f
    assert f.count(" and ") == 3


def test_year_is_forced_to_number():
    body = build_body(year_from="2021")
    assert "year ge 2021" in body["filter"]


def test_top_is_capped_at_8():
    assert build_body(top=50)["top"] == 8