Initialize the Wrydeco content runtime. Use only the `wrydeco-scraper` MCP server.
Call `queue_status` exactly once to verify the MCP connection. Do not claim or process a
content task during this turn. Then reply with exactly:
WRYDECO_AGENT_READY
