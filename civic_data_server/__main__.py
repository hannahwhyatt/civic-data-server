import os
import sys

# Add project root to Python path
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)

try:
    from civic_data_server.server import mcp
except ImportError:
    from .server import mcp

if __name__ == "__main__":
    import os
    sys.exit(mcp.run(
        transport="http", 
        host=os.getenv("MCP_HOST", "127.0.0.1"), 
        port=int(os.getenv("MCP_PORT", "8000")), 
        path="/mcp", 
        log_level="debug"
        ))

