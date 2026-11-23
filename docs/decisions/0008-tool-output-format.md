# 0008 Readable tool output for citations

**Status:** Accepted

## Context
`search_evidence` returned a list of dicts, which FastMCP sent as one JSON text block per passage. Copilot Studio used that text as the citation label, so users saw `{ "doc_id": ... }`.

## Decision
Return a `CallToolResult` with one readable text block per passage, starting with `Title, page X (URL)`, plus the raw fields in `structuredContent` for code clients (evaluation, Agent Framework).

## Consequences
Citations read naturally in Teams; programmatic clients keep exact fields. Covered by `test_tool_output.py`.
