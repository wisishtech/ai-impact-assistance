# 0003 Trim results by Entra group at query time

**Status:** Accepted

## Context
Some documents are restricted. Answers must never be built from passages a user may not read, including through citations or summaries.

## Decision
- Each indexed passage stores `group_ids` (from `access_group` in `sources.csv`).
- The MCP server reads the user's groups from the validated token and adds `group_ids/any(g: search.in(g, '...'))` to every query. No groups, no results.
- The agent is instructed to treat documents that were not returned as non-existent.

## Alternatives considered
- Copilot Studio SharePoint knowledge source: simpler, but less control over filtering, chunking and testing.
- Post-filtering results after search: risks leaking through ranking and empty pages.

## Consequences
- Verified: 0 leaks across 49 questions, 8 integration tests; the reviewer sees restricted documents, all-staff users do not.
- Group membership changes apply on the user's next token.
