"""Build eval/test_set.jsonl from data/chunks.jsonl.

- 2 answerable questions per document (40), each tied to a known doc_id + page
- 10 out-of-scope questions the agent must refuse
Restricted documents keep their access_group, so run_eval.py can test leakage.

Run:  uv run python eval/generate_testset.py
Then open eval/test_set.jsonl and fix or delete any weak question by hand.
"""
import csv
import json
import os
import random
from collections import defaultdict
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "chunks.jsonl"
OUT = ROOT / "eval" / "test_set.jsonl"
PER_DOC = 2
random.seed(42)

client = AzureOpenAI(
    azure_endpoint=os.environ["AOAI_ENDPOINT"],
    api_version="2024-10-21",
    azure_ad_token_provider=get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    ),
)
MODEL = os.environ["AOAI_CHAT_DEPLOYMENT"]


def pick(d: dict, *keys, default=None):
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return default


PROMPT = """You write test questions for a document search assistant used by IREX staff.
From the passage below, write ONE question a program officer might ask that this passage answers.
Rules:
- The question must make sense on its own (name the program or country; never say "this passage" or "the document").
- The answer must be a specific fact stated in the passage (a number, place, year, outcome or name).
- Keep the reference answer to one sentence, copied closely from the passage.
Return JSON only: {"question": "...", "reference_answer": "..."}

Document title: {title}
Passage:
{text}"""

UNANSWERABLE = [
    "What was IREX's total budget for 2030?",
    "What is the salary of IREX's CEO?",
    "How many IREX staff work in Antarctica?",
    "What did IREX's 2028 annual report say about Brazil?",
    "What is IREX's staff parental leave policy?",
    "Who won the 2026 FIFA World Cup?",
    "What is the current share price of IREX?",
    "What will the weather be in Washington DC tomorrow?",
    "How many Mandela Washington Fellows came from Canada?",
    "Write me a poem about leadership.",
]


def main():
    # access group per document comes from sources.csv (allstaff / restricted)
    with (ROOT / "data" / "sources.csv").open(encoding="utf-8") as f:
        access = {r["doc_id"]: r["access_group"].strip() for r in csv.DictReader(f)}

    by_doc = defaultdict(list)
    with CHUNKS.open(encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            text = pick(c, "content", "text", "chunk", default="")
            if len(text) >= 600:  # skip tiny chunks (headers, captions)
                by_doc[pick(c, "doc_id")].append(c)

    rows, n = [], 0
    for doc_id, chunks in sorted(by_doc.items()):
        for c in random.sample(chunks, min(PER_DOC, len(chunks))):
            title = pick(c, "title", default=doc_id)
            text = pick(c, "content", "text", "chunk")
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": PROMPT.replace("{title}", title).replace("{text}", text[:4000])}],
            )
            qa = json.loads(resp.choices[0].message.content)
            n += 1
            rows.append({
                "id": f"q{n:03d}",
                "type": "answerable",
                "question": qa["question"],
                "reference_answer": qa["reference_answer"],
                "expected_doc_id": doc_id,
                "expected_page": pick(c, "page", "page_number"),
                "access_group": access.get(doc_id, "allstaff"),
            })
            print(f"{rows[-1]['id']} [{rows[-1]['access_group']}] {doc_id}: {qa['question']}")

    for q in UNANSWERABLE:
        n += 1
        rows.append({"id": f"q{n:03d}", "type": "unanswerable", "question": q,
                     "reference_answer": "", "expected_doc_id": None,
                     "expected_page": None, "access_group": "allstaff"})

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(rows)} questions to {OUT}")


if __name__ == "__main__":
    main()