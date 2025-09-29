""" Civic Data MCP Server for the Liverpool Digital Commons 

https://www.liverpoolcivicdata.com/

"""

from fastmcp import FastMCP
import os
import sys


project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)
# Try absolute import first, then relative import as fallback
try:
    from civic_data_server.tools import register_all
except ImportError:
    from .tools import register_all


mcp = FastMCP(
    "civic-data-server",
    instructions="""
The Liverpool Digital Commons Research Assistant provides powerful tools to explore, understand, and analyze civic data about Liverpool. 
There is a focus on the Liverpool City Region, which is made up of the following local authorities:
- Liverpool City Council
- Sefton Council
- St. Helens Borough Council
- Wirral Council
- Halton Borough Council
- Knowsley Council

This server enables you to:

1. DISCOVER data through intelligent search across all available datasets
2. EXPLORE metadata to understand what resources are available
3. ACCESS the actual data from CSV, Excel, and PDF files
4. ANALYZE data using built-in analysis tools or custom Python code
5. VISUALIZE findings through charts and graphs

You can approach tasks in two primary ways:

A) Dataset-First (Broad Exploration): Best when the user has a general topic in mind.
    Workflow: search_datasets → get_dataset_info → get_resource_content → run_python

B) Resource-First (Targeted Search): Best when the user asks for a specific file, report, or data format.
    Workflow (Shortcut): search_resources → get_resource_content → run_python
    Workflow (With Context): search_resources → get_dataset_info (using the file's package_id) → get_resource_content

The server handles all the complexity of data access, allowing you to focus on finding insights about Liverpool's civic data, from demographics and economics to environment and public services.
""",
    include_tags={"public"}, exclude_tags={"admin"}, 
    dependencies=[
        "beautifulsoup4",
        "httpx",
        "requests",
        "pymupdf",
        "matplotlib",
    ],
    stateless_http=True,
)

register_all(mcp)


if __name__ == "__main__":
    import sys
    sys.exit(mcp.run(
        transport="http", 
        host="127.0.0.1", 
        port=8000, 
        path="/mcp", 
        log_level="debug"
        ))
