# Operations log

Newest first. One line per change, incident or review.

| Date | Type | What happened | Evidence |
|---|---|---|---|
| 2026-11-23 | Release | Server 0.1.4 released through GitHub Actions (gate → build → deploy → health check). | Release MCP server #1, revision `v0-1-4-1` |
| 2026-11-23 | Infra | Bicep added; what-if against dev runs in CI with OIDC (no stored secrets). | Infra what-if (dev) #3 |
| 2026-11-23 | Eval | 49 questions: 0 leaks, hit@5 1.0, groundedness 5.0, correctness 1.0, refusals 1.0. Fingerprint recorded. | `eval/results/summary.json` |
| 2026-11-23 | Fix | Drafting rules tightened after code-first agent overclaimed progress and used non-IREX figures. | decision 0005 |
| 2026-11-23 | Fix | Agent wrote a poem for an out-of-scope request; scope rule added. Refusals 0.9 → 1.0. | eval details |
| 2026-11-23 | Release | Portal hosted on Static Web Apps; CORS fixed (portal origin was empty). | runbook known issues |
| 2026-11-23 | Release | Server 0.1.3: readable citations, multi-origin CORS. | decision 0008 |
| 2026-11-23 | Test | End-to-end: program.officer cannot see restricted project page; reviewer can; draft approved and notified in Teams. | `docs/screenshots/` |
