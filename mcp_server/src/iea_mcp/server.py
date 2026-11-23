import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from . import indicators, search, telemetry
from .auth import EntraAuthMiddleware, current_user
from .config import settings

mcp = FastMCP("impact-evidence", stateless_http=True)
OFF = "The assistant is temporarily unavailable. Please try again later."


@mcp.tool()
def search_evidence(query: str, program: str | None = None, country: str | None = None,
                    year_from: int | None = None, language: str | None = None,
                    top: int = 5) -> list[dict] | str:
    """Search IREX program reports, impact stories and insights that the signed-in user may access.
    Returns passages with doc_id, title, page, section and url. Cite title, page and url for every claim."""
    if settings.maintenance_mode:
        return OFF
    user = current_user()
    with telemetry.span("search_evidence", user, program=program, country=country) as s:
        hits = search.search_evidence(query, user.group_ids, program, country, year_from, language, top)
        s.set_attribute("iea.hits", len(hits))
        return hits


@mcp.tool()
def get_indicators(program: str) -> list[dict] | str:
    """List results-framework indicators (indicator_id, indicator, period, baseline, target) for a program,
    e.g. 'Leadership', 'Future-Ready Workforce', 'Education', 'AI for Education'."""
    if settings.maintenance_mode:
        return OFF
    with telemetry.span("get_indicators", current_user(), program=program):
        return indicators.get_indicators(program)


@mcp.tool()
def submit_draft_for_review(indicator_id: str, program: str, draft_text: str,
                            citations: list[str]) -> dict | str:
    """Send one drafted progress paragraph to human reviewers. Only call after the user has confirmed the draft."""
    if settings.maintenance_mode:
        return OFF
    user = current_user()
    with telemetry.span("submit_draft_for_review", user, program=program):
        return indicators.submit_draft(user, indicator_id, program, draft_text, citations)


async def my_drafts(request):
    return JSONResponse(indicators.list_drafts(current_user().name))


async def healthz(request):
    return PlainTextResponse("ok")


app = mcp.streamable_http_app()          # MCP endpoint at /mcp
app.router.routes.append(Route("/api/my-drafts", my_drafts))
app.router.routes.append(Route("/healthz", healthz))
app = EntraAuthMiddleware(app)           # every request needs a valid token (except /healthz)
app = CORSMiddleware(app, allow_origins=[settings.portal_origin], allow_methods=["GET", "POST"],
                     allow_headers=["Authorization", "Content-Type", "Mcp-Session-Id"])

if __name__ == "__main__":
    telemetry.setup()
    uvicorn.run(app, host="0.0.0.0", port=8000)