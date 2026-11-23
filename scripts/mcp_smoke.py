# import asyncio
# import json
# import os
# import sys

# from mcp import ClientSession
# from mcp.client.streamable_http import streamablehttp_client


# async def main(question: str):
#     headers = {"Authorization": f"Bearer {os.environ['TOKEN']}"}
#     async with streamablehttp_client("http://localhost:8000/mcp", headers=headers) as (read, write, _):
#         async with ClientSession(read, write) as session:
#             await session.initialize()
#             tools = await session.list_tools()
#             print("Tools:", [t.name for t in tools.tools])
#             result = await session.call_tool("search_evidence", {"query": question, "top": 3})
#             for item in result.content:
#                 try:
#                     for hit in json.loads(item.text) if item.text.startswith("[") else [json.loads(item.text)]:
#                         print(f"- {hit['doc_id']} p.{hit['page']}: {hit['title'][:60]}")
#                 except Exception:
#                     print(item.text[:500])


# asyncio.run(main(sys.argv[1]))



import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = os.environ.get("MCP_URL", "http://localhost:8000/mcp")


def parse(result) -> list:
    """Turn an MCP tool result into a list of Python objects."""
    items = []
    for c in result.content:
        text = getattr(c, "text", "")
        try:
            data = json.loads(text)
            items.extend(data if isinstance(data, list) else [data])
        except (json.JSONDecodeError, TypeError):
            items.append(text)
    return items


async def main(question: str):
    headers = {"Authorization": f"Bearer {os.environ['TOKEN']}"}
    print(f"Server: {URL}\n")
    async with streamablehttp_client(URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])

            print(f"\nsearch_evidence: {question}")
            hits = parse(await session.call_tool("search_evidence", {"query": question, "top": 3}))
            for h in hits:
                if isinstance(h, dict):
                    print(f"  - {h['doc_id']} p.{h['page']}: {h['title'][:60]}")
                else:
                    print(f"  {h[:300]}")

            print("\nget_indicators: Leadership")
            for i in parse(await session.call_tool("get_indicators", {"program": "Leadership"})):
                if isinstance(i, dict):
                    print(f"  - {i['indicator_id']}: {i['indicator']} (target {i['target']})")
                else:
                    print(f"  {i[:300]}")


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "leadership programs"))