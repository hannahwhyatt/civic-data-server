from .server import mcp


if __name__ == "__main__":

    import sys
    sys.exit(mcp.run(
        transport="http", 
        host="0.0.0.0", 
        port=8000, 
        path="/mcp", 
        log_level="debug"
        ))

