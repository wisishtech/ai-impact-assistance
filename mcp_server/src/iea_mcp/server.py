import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from . import indicators, search, telemetry
from .auth import EntraAuthMiddleware, current_user
from .config import settings

mcp = FastMCP(
    "impact-evidence",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[h.strip() for h in settings.allowed_hosts.split(",")],
    ),
)
OFF = "The assistant is temporarily unavailable. Please try again later."


def passages_result(hits: list[dict]) -> CallToolResult:
    """One readable text block per passage (what Copilot shows as the citation),
    plus the raw fields as structured content for code clients such as the eval."""
    if not hits:
        return CallToolResult(
            content=[TextContent(type="text", text="No passages found that this user may access.")],
            structuredContent={"passages": []},
        )
    blocks = [
        TextContent(
            type="text",
            text=(f"{h.get('title')}, page {h.get('page')} ({h.get('url')})\n"
                  f"doc_id: {h.get('doc_id')} | section: {h.get('section') or '-'}\n\n"
                  f"{h.get('content')}"),
        )
        for h in hits
    ]
    return CallToolResult(content=blocks, structuredContent={"passages": hits})


@mcp.tool()
def search_evidence(query: str, program: str | None = None, country: str | None = None,
                    year_from: int | None = None, language: str | None = None,
                    top: int = 5) -> CallToolResult:
    """Search IREX program reports, impact stories and insights that the signed-in user may access.
    Each passage starts with "Title, page X (URL)". Cite title, page and url for every claim."""
    if settings.maintenance_mode:
        return CallToolResult(content=[TextContent(type="text", text=OFF)])
    user = current_user()
    with telemetry.span("search_evidence", user, program=program, country=country) as s:
        hits = search.search_evidence(query, user.group_ids, program, country, year_from, language, top)
        s.set_attribute("iea.hits", len(hits))
        return passages_result(hits)


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


# PORTAL_ORIGIN may list several origins, comma-separated (local dev + hosted portal)
ORIGINS = [o.strip() for o in settings.portal_origin.split(",") if o.strip()]

app = mcp.streamable_http_app()          # MCP endpoint at /mcp
app.router.routes.append(Route("/api/my-drafts", my_drafts))
app.router.routes.append(Route("/healthz", healthz))
app = EntraAuthMiddleware(app)           # every request needs a valid token (except /healthz)
app = CORSMiddleware(app, allow_origins=ORIGINS, allow_methods=["GET", "POST"],
                     allow_headers=["Authorization", "Content-Type", "Mcp-Session-Id"])

if __name__ == "__main__":
    telemetry.setup()
    uvicorn.run(app, host="0.0.0.0", port=8000)