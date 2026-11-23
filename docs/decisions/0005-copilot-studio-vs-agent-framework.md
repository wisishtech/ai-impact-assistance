# 0005 Copilot Studio and a code-first agent side by side

**Status:** Accepted

## Context
Low-code agents are fast to ship into Teams; code-first agents give more control over approvals, testing and deployment.

## Decision
Build both on the same MCP server and the same `agent/instructions.md`:
- **Copilot Studio** for Teams, M365 Copilot and the web portal.
- **Microsoft Agent Framework** (Python) for a code-first version, where `submit_draft_for_review` is marked `always_require` and blocked until a person types *y*.

## Findings
| | Copilot Studio | Agent Framework |
|---|---|---|
| Time to first answer in Teams | Hours | Needs a host (not built) |
| Approval before writing | Instruction-based (model asks) | Enforced in code |
| Model | Managed | Chosen (gpt-4.1-mini) |
| Testing | Manual + eval of instructions | Unit-testable loop |
| Drafting quality on first try | Correctly excluded non-IREX figures | Overclaimed until rules were made explicit |

## Consequences
Copilot Studio is the main channel. The code-first agent shows the same tools can run under stricter, testable control, and it pushed the shared instructions to be more explicit, which improved both.
