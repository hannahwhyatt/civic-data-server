from .server import mcp


if __name__ == "__main__":

    import sys
    sys.exit(mcp.run(
        transport="http", 
        host="127.0.0.1", 
        port=8000, 
        path="/mcp", 
        log_level="debug"
        ))

