import httpx
from azure.identity import DefaultAzureCredential

from .config import settings

_cred = DefaultAzureCredential()
URL = f"{settings.search_endpoint}/indexes/{settings.search_index}/docs/search?api-version=2024-07-01"
FIELDS = ["doc_id", "title", "url", "page", "section", "content"]


def _q(value: str) -> str:
    """Escape quotes so user text can't break the filter."""
    return value.replace("'", "''")


def search_evidence(query: str, group_ids: list[str], program: str | None = None,
                    country: str | None = None, year_from: int | None = None,
                    language: str | None = None, top: int = 5) -> list[dict]:
    if not group_ids:
        return []   # no groups = no access
    filters = [f"group_ids/any(g: search.in(g, '{','.join(group_ids)}'))"]
    if program:
        filters.append(f"program eq '{_q(program)}'")
    if country:
        filters.append(f"country eq '{_q(country)}'")
    if year_from:
        filters.append(f"year ge {int(year_from)}")
    if language:
        filters.append(f"language eq '{_q(language)}'")

    body = {
        "search": query,
        "vectorQueries": [{"kind": "text", "text": query, "fields": "content_vector", "k": 30}],
        "filter": " and ".join(filters),
        "queryType": "semantic",
        "semanticConfiguration": "default",
        "select": ",".join(FIELDS),
        "top": min(int(top), 8),
    }
    token = _cred.get_token("https://search.azure.com/.default").token
    r = httpx.post(URL, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    r.raise_for_status()
    return [{k: d.get(k) for k in FIELDS} for d in r.json()["value"]]