# Sustained use: from prototype to operation

The assistant counts as "in operation" when it is used regularly, measured, owned and improved. This checklist is reviewed monthly; evidence goes in [operations-log.md](operations-log.md).

## Checklist

| # | Item | How we show it | Status |
|---|---|---|---|
| 1 | Named owner and backup | Runbook header | ✅ |
| 2 | Users can get access without the builder | Entra groups + connection link in runbook | ✅ |
| 3 | Works in daily tools | Teams, Microsoft 365 Copilot, web portal | ✅ |
| 4 | Quality gate before every release | `check_fresh.py` + `check_thresholds.py` in CI and release | ✅ |
| 5 | Safe release and rollback | Release workflow with health check and auto-rollback | ✅ |
| 6 | Kill switch | `MAINTENANCE_MODE` | ✅ |
| 7 | Usage measured | App Insights queries below, reviewed monthly | ⬜ first review due |
| 8 | User feedback collected | Thumbs up/down in Teams and portal; reviewer comments on drafts | ⬜ first review due |
| 9 | Real questions added to the test set | 10 hand-written questions per month from real use | ⬜ |
| 10 | Costs tracked | Budget alert + monthly cost check | ✅ alert set |
| 11 | Secrets rotated | Runbook schedule | ⬜ due in 6 months |
| 12 | Training / quick guide for staff | One-page "how to ask" guide | ⬜ |

## Monthly review (30 minutes)
1. Usage: queries below.
2. Quality: re-run the eval; compare with last month.
3. Feedback: read thumbs-down answers and "Changes requested" drafts; turn the top 3 into instruction fixes or test questions.
4. Cost: Azure Cost Management for `rg-iea-dev`.
5. Log the results in `operations-log.md`.

## Usage queries (Application Insights → Logs)
Tool calls per day:
```kusto
union dependencies, requests
| where timestamp > ago(30d)
| where name in ("search_evidence", "get_indicators", "submit_draft_for_review")
| summarize calls = count() by name, bin(timestamp, 1d)
| render columnchart
```
Distinct users per week:
```kusto
union dependencies, requests
| where timestamp > ago(90d)
| where name == "search_evidence"
| summarize users = dcount(user_AuthenticatedId) by bin(timestamp, 7d)
```
Searches that returned nothing (content gaps):
```kusto
union dependencies, requests
| where timestamp > ago(30d) and name == "search_evidence"
| where toint(customDimensions["iea.hits"]) == 0
| summarize count() by bin(timestamp, 1d)
```
Field names depend on how spans are exported; if a query returns nothing, open one `search_evidence` row and adjust the names.
