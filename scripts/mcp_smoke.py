import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main(question: str):
    headers = {"Authorization": f"Bearer {os.environ['TOKEN']}"}
    async with streamablehttp_client("http://localhost:8000/mcp", headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])
            result = await session.call_tool("search_evidence", {"query": question, "top": 3})
            for item in result.content:
                try:
                    for hit in json.loads(item.text) if item.text.startswith("[") else [json.loads(item.text)]:
                        print(f"- {hit['doc_id']} p.{hit['page']}: {hit['title'][:60]}")
                except Exception:
                    print(item.text[:500])


asyncio.run(main(sys.argv[1]))