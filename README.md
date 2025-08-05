# Civic Data Server
MCP server written in python for the Liverpool Digtal Commons


## Features
TBD


### Requirements

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Environment variables:

```
CKAN_API_KEY="YOUR_CKAN_API_KEY"
```

### Running the server

```bash
# Using uv
uv run -m civic_data_server

# Or directly with Python
python -m civic_data_server

# Or using fastmcp
fastmcp run civic_data_server/server.py -t http
```


### 
---

### Development resources 

1. **[FastMCP documentation](https://gofastmcp.com/getting-started/welcome)**
> FastMCP is the standard framework for working with the Model Context Protocol. FastMCP 1.0 was incorporated into the official MCP Python SDK in 2024, and FastMCP 2.0 is the actively maintained version that provides a complete toolkit for working with the MCP ecosystem.

2. **[MCP Documentation](https://modelcontextprotocol.io/introduction)**

### Tools for testing

1. **[User interface for testing MCP servers](https://github.com/modelcontextprotocol/inspector)**

Ensure Node.js: ^22.7.5 is installed and that the MCP server is running. Then, run:
``` bash
npx @modelcontextprotocol/inspector
```

### MCP JSON for clients (e.g. LM Studio, Cursor)

**`mcp.json`**
``` json
{
  "mcpServers": {
    "civic-data-server": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```


---
