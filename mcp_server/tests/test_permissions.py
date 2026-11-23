import os

import pytest

from iea_mcp.search import search_evidence

ALL = os.getenv("GROUP_ALLSTAFF_ID")
RESTRICTED = os.getenv("GROUP_RESTRICTED_ID")
RESTRICTED_DOCS = {"IREX-2024-SS-005", "IREX-2016-EV-002", "IREX-2022-EV-004", "IREX-2014-EV-005"}
QUERIES = [
    "Mandela Washington Fellowship young African leaders",
    "Albanian-American Development Foundation master's and internship program",
    "partner-led performance improvement guide",
    "Indigenous women leaders food insecurity El Salvador",
]

pytestmark = pytest.mark.skipif(
    not (ALL and RESTRICTED) or "example" in os.getenv("SEARCH_ENDPOINT", ""),
    reason="integration test: run with --env-file .env after az login",
)


@pytest.mark.parametrize("query", QUERIES)
def test_all_staff_never_sees_restricted(query):
    ids = {h["doc_id"] for h in search_evidence(query, [ALL], top=8)}
    assert not ids & RESTRICTED_DOCS, f"LEAK: {ids & RESTRICTED_DOCS}"


@pytest.mark.parametrize("query", QUERIES)
def test_restricted_user_can_see_restricted(query):
    ids = {h["doc_id"] for h in search_evidence(query, [ALL, RESTRICTED], top=8)}
    assert ids & RESTRICTED_DOCS