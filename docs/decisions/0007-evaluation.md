# 0007 Evaluation and release gate

**Status:** Accepted

## Decision
- Test set: 2 generated questions per document (reviewed by hand), plus 10 out-of-scope prompts. Each answerable question records its expected document and access group.
- `run_eval.py` signs in as an all-staff user and a restricted reviewer, calls the deployed MCP server, then answers with the shared instructions and grades with an LLM judge.
- `check_thresholds.py` fails the release if any gate is missed. Permission leaks must be 0.

## Results (latest)
hit@5 1.00, MRR 0.987, leaks 0, restricted hit rate 1.00, groundedness 5.0, correctness 1.00, out-of-scope refusals 1.00.

## Limitations
Generated questions overlap with source wording; answer metrics bypass Copilot Studio orchestration. Next: hand-written questions from staff and a periodic sample of real conversations.
