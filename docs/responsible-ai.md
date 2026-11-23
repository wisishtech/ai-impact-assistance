# Responsible AI card: Impact Evidence Assistant

## Purpose
Help IREX program, M&E and communications staff find evidence in IREX documents and draft results-framework progress sections faster, while keeping people responsible for what is reported.

## Intended users and uses
- Program officers and M&E staff looking up what reports say about a program, country or result.
- Drafting a first version of a progress paragraph per indicator for a human reviewer.

## Out of scope
- Final donor or public reporting without human review.
- Questions outside IREX program evidence (general knowledge, news, creative writing). The agent declines these.
- Decisions about people (staff, participants, grantees).

## How it reduces harm

| Risk | Control | Evidence |
|---|---|---|
| Showing restricted documents to the wrong person | Search filters by the user's Entra groups at query time; server validates the user's token | 0 leaks in 49-question eval; 8 permission integration tests |
| Made-up facts | Answers only from retrieved passages, with a citation per claim; refuses when passages don't answer | Groundedness 5.0/5; correctness 1.0 |
| Overclaiming progress | Drafting rules: only IREX results matching the indicator; "No evidence found" when none; no invented numbers | Before/after test on AI-1 draft |
| Unreviewed content reaching reports | User must confirm; code-first agent blocks submission in code until a human types *y*; reviewer approval in Power Automate | Approve/reject flow tested end to end |
| Misuse for unrelated tasks | Scope rule; no tools called for out-of-scope requests | 10/10 out-of-scope prompts refused |

## Data
- 20 public IREX documents (annual reports, evaluations, success stories, insights), 750 passages.
- Four documents are marked restricted for testing only.
- Results-framework targets are illustrative, not IREX data.
- No personal data is indexed. Draft submissions record the submitter's name and email for notifications.

## Models
- Generation: Azure OpenAI gpt-4.1-mini (code-first agent and evaluation); Copilot Studio's managed model for the low-code agent.
- Embeddings: text-embedding-3-small.
- Judge (evaluation only): gpt-4.1-mini.

## Known limitations
- The evaluation questions were generated from the indexed passages, so they are easier than real questions.
- Citations point to the document and page, not an exact paragraph.
- English-first: other languages have not been evaluated.
- The assistant is only as current as the indexed documents.

## Human oversight
Every draft goes to a named reviewer, who can approve or request changes. The author is notified in Teams, and the status is visible in the portal.

## Monitoring
Tool calls are traced to Application Insights (user ID, tool, hit count; no document text). The evaluation runs before each release and fails the release if any gate is missed.

## Contact and feedback
Users can rate answers (thumbs up/down) in Teams and the portal. Issues go to the repository owner.
