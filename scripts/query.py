import argparse
import os
import httpx
from azure.identity import DefaultAzureCredential

p = argparse.ArgumentParser()
p.add_argument("query")
p.add_argument("--groups", required=True, help="comma-separated Entra group IDs")
a = p.parse_args()

token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
url = f"{os.environ['SEARCH_ENDPOINT']}/indexes/{os.environ['SEARCH_INDEX']}/docs/search?api-version=2024-07-01"
body = {
    "search": a.query,
    "vectorQueries": [{"kind": "text", "text": a.query, "fields": "content_vector", "k": 30}],
    "filter": f"group_ids/any(g: search.in(g, '{a.groups}'))",
    "queryType": "semantic",
    "semanticConfiguration": "default",
    "select": "doc_id,title,page,section",
    "top": 5,
}
r = httpx.post(url, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=60)
r.raise_for_status()
for d in r.json()["value"]:
    print(f"{d['doc_id']:20} p.{d['page']:<4} {d['title'][:60]}")