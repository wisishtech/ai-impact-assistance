import httpx
from azure.identity import DefaultAzureCredential

from .config import settings

_cred = DefaultAzureCredential()
BASE = f"https://graph.microsoft.com/v1.0/sites/{settings.sp_site_id}/lists"


def _headers() -> dict:
    token = _cred.get_token("https://graph.microsoft.com/.default").token
    return {"Authorization": f"Bearer {token}"}


def _items(list_id: str) -> list[dict]:
    r = httpx.get(f"{BASE}/{list_id}/items?expand=fields&$top=500", headers=_headers(), timeout=60)
    r.raise_for_status()
    return [{"id": i["id"], **i["fields"]} for i in r.json()["value"]]


def get_indicators(program: str) -> list[dict]:
    rows = _items(settings.sp_results_list_id)
    return [{"indicator_id": x.get("IndicatorId"), "indicator": x.get("Title"),
             "period": x.get("Period"), "baseline": x.get("Baseline"), "target": x.get("Target")}
            for x in rows if (x.get("Program") or "").lower() == program.lower()]


def submit_draft(user, indicator_id: str, program: str, draft_text: str, citations: list[str]) -> dict:
    body = {"fields": {"Title": f"{program} {indicator_id}", "IndicatorId": indicator_id,
                       "Program": program, "Draft": draft_text, "Citations": "\n".join(citations),
                       "SubmittedBy": user.name, "Status": "Pending"}}
    r = httpx.post(f"{BASE}/{settings.sp_drafts_list_id}/items", headers=_headers(), json=body, timeout=60)
    r.raise_for_status()
    return {"item_id": r.json()["id"], "status": "Pending"}


def list_drafts(submitted_by: str) -> list[dict]:
    rows = _items(settings.sp_drafts_list_id)
    return [{"id": x["id"], "IndicatorId": x.get("IndicatorId"), "Program": x.get("Program"),
             "Status": x.get("Status"), "ReviewerComment": x.get("ReviewerComment"),
             "DecisionDate": x.get("DecisionDate")}
            for x in rows if x.get("SubmittedBy") == submitted_by]