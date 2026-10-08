from mcp.server import MCPServer
from registry import ALL_Tools

mcp = MCPServer("tool-server")

for t in ALL_Tools:
    mcp.add_tool(t)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8095)