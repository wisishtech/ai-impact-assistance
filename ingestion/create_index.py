import json
import os
import sys
import httpx
from azure.identity import DefaultAzureCredential

schema = json.load(open("ingestion/index_schema.json", encoding="utf-8"))
if len(sys.argv) > 1:
    schema["name"] = sys.argv[1]

token = DefaultAzureCredential().get_token("https://search.azure.com/.default").token
url = f"{os.environ['SEARCH_ENDPOINT']}/indexes/{schema['name']}?api-version=2024-07-01"

r = httpx.put(url, json=schema, headers={"Authorization": f"Bearer {token}"}, timeout=60)
if r.status_code >= 300:
    print("Error", r.status_code, r.text)
    sys.exit(1)
print("Index ready:", schema["name"])