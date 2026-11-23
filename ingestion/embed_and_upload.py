import json
import os
from itertools import batched
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from openai import AzureOpenAI

cred = DefaultAzureCredential()
aoai = AzureOpenAI(
    azure_endpoint=os.environ["AOAI_ENDPOINT"],
    api_version="2024-10-21",
    azure_ad_token_provider=get_bearer_token_provider(cred, "https://cognitiveservices.azure.com/.default"),
    max_retries=10,   # waits and retries if we hit the rate limit
)
search = SearchClient(os.environ["SEARCH_ENDPOINT"], os.environ["SEARCH_INDEX"], cred)

ALL = os.environ["GROUP_ALLSTAFF_ID"]
RESTRICTED = os.environ["GROUP_RESTRICTED_ID"]
GROUPS = {"IEA-AllStaff": [ALL, RESTRICTED], "IEA-Restricted": [RESTRICTED]}
KEEP = ["chunk_id", "doc_id", "title", "url", "page", "section", "content",
        "program", "country", "theme", "language", "doc_type", "year"]

chunks = [json.loads(line) for line in open("data/chunks.jsonl", encoding="utf-8")]
done = 0
for batch in batched(chunks, 16):
    vectors = aoai.embeddings.create(model=os.environ["AOAI_EMBED_DEPLOYMENT"],
                                     input=[c["content"] for c in batch])
    docs = [{**{k: c[k] for k in KEEP},
             "content_vector": v.embedding,
             "group_ids": GROUPS[c["access_group"]]}
            for c, v in zip(batch, vectors.data)]
    results = search.merge_or_upload_documents(docs)
    done += sum(r.succeeded for r in results)
    print(f"uploaded {done}/{len(chunks)}")
print("Finished")