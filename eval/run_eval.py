"""Score the Impact Evidence Assistant against eval/test_set.jsonl.

What it measures
- retrieval hit@5 and MRR: does search_evidence return the expected document?
- leakage: does program.officer (all staff) ever get a restricted document? Must be 0.
- restricted access: does restricted.reviewer get the restricted documents?
- groundedness (1-5), correctness and refusals, judged by gpt-4.1-mini on answers
  written from the retrieved passages using agent/instructions.md.

It calls your deployed MCP server as real users, so permission trimming is tested end to end.
Two browser sign-ins open: first program.officer, then restricted.reviewer.

Run:  uv run python eval/run_eval.py
"""
import asyncio
import csv
import json
import os
import statistics
import time
from pathlib import Path

import msal
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from openai import AzureOpenAI

from check_fresh import fingerprint

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
TEST_SET = ROOT / "eval" / "test_set.jsonl"
RESULTS = ROOT / "eval" / "results"
INSTRUCTIONS = (ROOT / "agent" / "instructions.md").read_text(encoding="utf-8")
MCP_URL = os.environ["MCP_URL"]
SCOPE = f"api://{os.environ['MCP_API_CLIENT_ID']}/Evidence.Read"
K = 5
USERS = {
    "allstaff": "program.officer@WisishTech.onmicrosoft.com",
    "restricted": "restricted.reviewer@WisishTech.onmicrosoft.com",
}

aoai = AzureOpenAI(
    azure_endpoint=os.environ["AOAI_ENDPOINT"],
    api_version="2024-10-21",
    azure_ad_token_provider=get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    ),
)
MODEL = os.environ["AOAI_CHAT_DEPLOYMENT"]


# ---------- helpers ----------
def pick(d: dict, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def is_restricted(group: str) -> bool:
    return "restricted" in (group or "").lower()


def sign_in(username: str) -> str:
    app = msal.PublicClientApplication(
        os.environ["EVAL_CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}",
    )
    print(f"\nSign in as {username} in the browser window...")
    r = app.acquire_token_interactive([SCOPE], login_hint=username, prompt="select_account")
    if "access_token" not in r:
        raise SystemExit(f"Sign-in failed for {username}: {r.get('error_description')}")
    return r["access_token"]


def parse_passages(result) -> list[dict]:
    """Accept the shapes FastMCP may return: structuredContent, one JSON list, or one JSON item per block."""
    out: list = []
    sc = getattr(result, "structuredContent", None)
    if sc:
        sc = sc.get("result", sc)
        out = sc if isinstance(sc, list) else sc.get("results", sc.get("passages", [sc]))
        return [p for p in out if isinstance(p, dict)]
    for block in result.content:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            out.extend(data)
        elif isinstance(data, dict):
            out.extend(data.get("results", data.get("passages", [data])))
    return [p for p in out if isinstance(p, dict)]


async def search_all(token: str, questions: list[str]) -> list[list[dict]]:
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(MCP_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as s:
            await s.initialize()
            tools = {t.name: t for t in (await s.list_tools()).tools}
            props = tools["search_evidence"].inputSchema.get("properties", {})
            qarg = "query" if "query" in props else next(iter(props))
            results = []
            for i, q in enumerate(questions, 1):
                args = {qarg: q}
                if "top" in props:
                    args["top"] = K
                r = await s.call_tool("search_evidence", args)
                results.append(parse_passages(r)[:K])
                print(f"  searched {i}/{len(questions)}", end="\r")
            print()
            return results


def answer(question: str, passages: list[dict]) -> str:
    ctx = "\n\n".join(
        f"[{pick(p, 'title', 'doc_id')}, page {pick(p, 'page', 'page_number')}, {pick(p, 'url', default='')}]\n"
        f"{pick(p, 'content', 'text', 'chunk', default='')}"
        for p in passages
    ) or "(no passages returned)"
    r = aoai.chat.completions.create(
        model=MODEL, temperature=0,
        messages=[
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": f"Passages returned by search_evidence:\n{ctx}\n\nQuestion: {question}"},
        ],
    )
    return r.choices[0].message.content


JUDGE = """You grade an assistant's answer. Return JSON only:
{"refused": true|false, "grounded": 1-5, "correct": true|false, "reason": "short"}
- refused: the answer says the documents don't contain the information (or declines).
- grounded: 5 = every claim is supported by the passages; 1 = mostly unsupported. If refused, use 5.
- correct: the answer contains the key fact of the reference answer. If no reference, use false.

Question: {q}
Reference answer: {ref}
Passages:
{ctx}
Assistant answer:
{ans}"""


def judge(q: str, ref: str, passages: list[dict], ans: str) -> dict:
    ctx = "\n\n".join(pick(p, "content", "text", "chunk", default="")[:1500] for p in passages) or "(none)"
    prompt = JUDGE.replace("{q}", q).replace("{ref}", ref or "(none)").replace("{ctx}", ctx).replace("{ans}", ans)
    r = aoai.chat.completions.create(
        model=MODEL, temperature=0, response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(r.choices[0].message.content)


# ---------- main ----------
def main():
    rows = [json.loads(l) for l in TEST_SET.read_text(encoding="utf-8").splitlines() if l.strip()]
    with (ROOT / "data" / "sources.csv").open(encoding="utf-8") as f:
        restricted_docs = {r["doc_id"] for r in csv.DictReader(f) if is_restricted(r["access_group"])}

    tokens = {k: sign_in(u) for k, u in USERS.items()}

    print("\nSearching as program.officer (all questions)...")
    officer = asyncio.run(search_all(tokens["allstaff"], [r["question"] for r in rows]))
    restricted_rows = [r for r in rows if is_restricted(r["access_group"])]
    print("Searching as restricted.reviewer (restricted questions)...")
    reviewer = asyncio.run(search_all(tokens["restricted"], [r["question"] for r in restricted_rows]))
    reviewer_by_id = {r["id"]: p for r, p in zip(restricted_rows, reviewer)}

    details = []
    for i, (row, off_passages) in enumerate(zip(rows, officer), 1):
        print(f"  answering {i}/{len(rows)}", end="\r")
        off_docs = [pick(p, "doc_id") for p in off_passages]
        leaked = sorted(set(off_docs) & restricted_docs)

        # answer as the user who is allowed to see the expected document
        passages = reviewer_by_id.get(row["id"], off_passages)
        docs = [pick(p, "doc_id") for p in passages]
        rank = docs.index(row["expected_doc_id"]) + 1 if row.get("expected_doc_id") in docs else None

        ans = answer(row["question"], passages)
        grade = judge(row["question"], row.get("reference_answer", ""), passages, ans)
        details.append({**row, "returned_docs": docs, "rank": rank, "officer_leaked": leaked,
                        "answer": ans, **{f"judge_{k}": v for k, v in grade.items()}})
    print()

    answerable = [d for d in details if d["type"] == "answerable"]
    unanswerable = [d for d in details if d["type"] == "unanswerable"]
    restricted_q = [d for d in answerable if is_restricted(d["access_group"])]
    summary = {
        "run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fingerprint": fingerprint(),
        "questions": len(details),
        "hit_at_5": round(sum(d["rank"] is not None for d in answerable) / len(answerable), 3),
        "mrr": round(sum(1 / d["rank"] for d in answerable if d["rank"]) / len(answerable), 3),
        "leaked_questions": sum(bool(d["officer_leaked"]) for d in details),
        "restricted_hit_rate": round(sum(d["rank"] is not None for d in restricted_q) / max(len(restricted_q), 1), 3),
        "groundedness_avg": round(statistics.mean(d["judge_grounded"] for d in answerable), 2),
        "correctness": round(sum(bool(d["judge_correct"]) for d in answerable) / len(answerable), 3),
        "false_refusals": sum(bool(d["judge_refused"]) for d in answerable),
        "refusal_rate_unanswerable": round(sum(bool(d["judge_refused"]) for d in unanswerable) / max(len(unanswerable), 1), 3),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    with (RESULTS / f"details-{stamp}.jsonl").open("w", encoding="utf-8") as f:
        for d in details:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n===== Evaluation summary =====")
    for k, v in summary.items():
        print(f"{k:28} {v}")
    print(f"\nDetails: eval/results/details-{stamp}.jsonl")


if __name__ == "__main__":
    main()
