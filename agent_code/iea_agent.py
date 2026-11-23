"""Code-first Impact Evidence Assistant (Microsoft Agent Framework).

Same MCP server, same instructions and same permission trimming as the Copilot Studio agent.
Differences: runs as a terminal chat, and submit_draft_for_review needs your explicit y/n approval
in code (human-in-the-loop), not just the model's judgment.

Run (from the project root):
    cd agent_code
    uv sync
    uv run python iea_agent.py                      # sign in as any user
    uv run python iea_agent.py --user program.officer@WisishTech.onmicrosoft.com
"""
import argparse
import asyncio
import os
import warnings
from pathlib import Path

import msal
from agent_framework import Agent, MCPStreamableHTTPTool, Message
from agent_framework.openai import OpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
warnings.filterwarnings("ignore", message=".*ping is removed.*")  # harmless library notice
INSTRUCTIONS = (ROOT / "agent" / "instructions.md").read_text(encoding="utf-8")


def sign_in(user: str | None) -> str:
    """Delegated token for the MCP server, so the server trims results to this user's groups."""
    app = msal.PublicClientApplication(
        os.environ["EVAL_CLIENT_ID"],  # iea-eval public client, already consented for Evidence.Read
        authority=f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}",
    )
    scope = [f"api://{os.environ['MCP_API_CLIENT_ID']}/Evidence.Read"]
    r = app.acquire_token_interactive(scope, login_hint=user, prompt="select_account")
    if "access_token" not in r:
        raise SystemExit(f"Sign-in failed: {r.get('error_description')}")
    print(f"Signed in as {r['id_token_claims'].get('preferred_username')}\n")
    return r["access_token"]


def ask_approval(req) -> bool:
    call = req.function_call
    print("\n--- Approval needed ---")
    print(f"Tool: {call.name}")
    print(f"Arguments: {call.arguments}")
    return input("Approve? (y/n): ").strip().lower() == "y"


async def main(user: str | None) -> None:
    token = sign_in(user)

    client = OpenAIChatCompletionClient(
        azure_endpoint=os.environ["AOAI_ENDPOINT"],
        model=os.environ["AOAI_CHAT_DEPLOYMENT"],
        credential=DefaultAzureCredential(),
    )
    iea = MCPStreamableHTTPTool(
        name="iea",
        url=os.environ["MCP_URL"],
        static_headers={"Authorization": f"Bearer {token}"},
        # reading is safe; anything that writes to SharePoint needs a human yes
        approval_mode={"always_require_approval": ["submit_draft_for_review"], "default": "never_require"},
    )

    async with iea:
        agent = Agent(client=client, name="impact-evidence-assistant",
                      instructions=INSTRUCTIONS, tools=iea)
        session = agent.create_session()
        print("Ask about IREX evidence or say 'draft AI for Education AI-1'. Type 'exit' to quit.\n")

        while True:
            text = input("You: ").strip()
            if text.lower() in {"exit", "quit"}:
                break
            if not text:
                continue
            result = await agent.run(text, session=session)

            # human-in-the-loop: keep looping while the agent waits on approvals
            while result.user_input_requests:
                replies = [
                    Message("user", [req.to_function_approval_response(ask_approval(req))])
                    for req in result.user_input_requests
                ]
                result = await agent.run(replies, session=session)

            print(f"\nAssistant: {result.text}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--user", help="login hint, e.g. program.officer@WisishTech.onmicrosoft.com")
    asyncio.run(main(p.parse_args().user))
