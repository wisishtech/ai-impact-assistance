import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

DEFAULTS = {
    "AZURE_TENANT_ID": "00000000-0000-0000-0000-000000000000",
    "SEARCH_ENDPOINT": "https://example.search.windows.net",
    "SEARCH_INDEX": "test-index",
    "MCP_API_CLIENT_ID": "11111111-1111-1111-1111-111111111111",
    "SP_SITE_ID": "example.sharepoint.com,a,b",
    "SP_RESULTS_LIST_ID": "results",
    "SP_DRAFTS_LIST_ID": "drafts",
}
for key, value in DEFAULTS.items():
    os.environ.setdefault(key, value)