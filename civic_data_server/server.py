""" Civic Data MCP Server for the Liverpool Digital Commons 

https://www.liverpoolcivicdata.com/

"""

from fastmcp import FastMCP, Context
from typing import Annotated, Literal
from pydantic import Field
import requests
import httpx
from bs4 import BeautifulSoup
import pymupdf
from io import BytesIO

import os
ckan_user_api_key = os.getenv("CKAN_USER_API_KEY")



# Server ------------------------------------------------------------------------------------------------
mcp = FastMCP(
    "civic-data-server",
    instructions="""
        The Liverpool Digital Commons is a platform for sharing and exploring data about Liverpool.
        This server provides tools and resources to learn about the Liverpool Digital Commons, and to access, understand, and analyse the data available on the site.
    """,
    include_tags={"public"}, exclude_tags={"admin"}, # tags are optional, but can be used selectively expose components based on environments or users
    dependencies=[
        "beautifulsoup4",
        "httpx",
        "requests",
        "pymupdf",
    ]
)


# Tools ------------------------------------------------------------------------------------------------

# --- Get client id (not yet implemented, returns client_id: None)
@mcp.tool(
    tags={"public"},
)
async def request_info(ctx: Context) -> dict:
    """Return information about the current request."""
    return {
        "request_id": ctx.request_id,
        "client_id": ctx.client_id,
    }


# --- Tools for exploring datasets on the site
@mcp.tool(
    tags={"public"},
)
async def dataset_search(
    query: Annotated[
        str,
        Field(description="The query to search for datasets.")
    ]
    ) -> str:
    """Search for datasets using a query string via a Liverpool Digital Commons API endpoint.
    """
    
    ckan_api_base_url = "https://www.liverpoolcivicdata.com/api/3"

    headers = {'Authorization': ckan_user_api_key}
    path = f"{ckan_api_base_url}/action/package_search?q={query}"


    try:
        response = requests.get(path, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("success") == True:
            return format_dataset_search_response(data)
        else:
            return f"Error retrieving dataset search results: {data.get('error')}"
    except requests.RequestException as e:
        return f"Error retrieving dataset search results: {str(e)}"

@mcp.tool(
    tags={"public"},
)
async def get_dataset_metadata(
    dataset_name: Annotated[
        str,    
        # CKAN dataset names are typically in a format like dataset-name or name-of-the-dataset-2023
        Field(description="The name (ID) of the dataset to get the metadata for.", pattern=r"^[a-z0-9-]+$")],
    ) -> dict:

    """Get the metadata for a dataset by calling an Liverpool Digital Commons API endpoint.
    Requires authentication via Authorization header with CKAN API key.
    """

    ckan_api_base_url = "https://www.liverpoolcivicdata.com/api/3"

    headers = {'Authorization': ckan_user_api_key}
    path = f"{ckan_api_base_url}/action/package_show?id={dataset_name}"


    try:
        response = requests.get(path, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        return data
    except requests.RequestException as e:
        return {"error": f"Error retrieving dataset metadata: {str(e)}"}


# --- Tools to boost utilisation of the server (sampling)
@mcp.tool(
    tags={"public"},
)
async def suggest_query_terms(
    user_message: str, 
    ctx: Context,
) -> dict:
    """Suggest query terms for a dataset search using the client's LLM.
    This tool is appropriate to use when the user has expressed interest in exploring the datasets on the site, but has not provided specific search parameters.
    """

    prompt = f"""Suggest query terms to search for datasets that are likely to be of relevance and interest to the user. 
    Infer the user's interest and intent from the message, and output a string of five appropriate search terms separated by commas.

    User message: {user_message}"""

    response = await ctx.sample(prompt) 

    # query_terms = response.text

    return {
        # "query_terms": query_terms,
    }



# Resources ---------------------------------------------------------------------------------------------
@mcp.resource(
    "pdf-resource://{resource_id}",
    tags={"public"},
)
async def pdf_resource(
    resource_id: str,
) -> str:
    """Get a PDF resource by ID. Return the text of the pdf as a string."""

    # Check if the resource has been read before
    path = f"civic_data_server/data/{resource_id}.txt"
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    
    # Get the pdf
    pdf_url = f"https://www.liverpoolcivicdata.com/api/3/action/resource_show?id={resource_id}"
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        metadata = response.json()
        url = metadata.get("result", {}).get("url")
        if not url:
            return f"Error retrieving PDF resource: {metadata.get('error')}"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        pdf_bytes = BytesIO(response.content)
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        pdf_text = ""
        for page in doc:
            pdf_text += page.get_text()

    except requests.Timeout:
        return "Error: Request timed out while downloading PDF"
    except requests.RequestException as e:
        return f"Error downloading PDF: {str(e)}"
    except Exception as e:
        return f"Error processing PDF request: {str(e)}"


    # Save the text of the pdf to a file
    os.makedirs("civic_data_server/data", exist_ok=True)
    with open(path, "w") as f:
        f.write(pdf_text)

    return pdf_text


@mcp.resource(
    "resource://about/{section}",
    tags={"public"},
)
async def information_about_the_liverpool_digital_commons(
    section: Annotated[Literal["mission", "what-we-do", "partners", "key-features", "get-involved"],
    Field(description="The section of the Liverpool Digital Commons to get information about.")]) -> str:
    
    """Get information about the Liverpool Digital Commons.
    """
    
    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.liverpoolcivicdata.com/about")
        response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Section mapping
    section_configs = {
        "mission": {
            "heading": "Our Mission",
            "extract": lambda section: section.find_all('p', class_='welcome-description'),
            "format": lambda items: '\n\n'.join([p.get_text().strip() for p in items])
        },
        "what-we-do": {
            "heading": "What We Do",
            "extract": lambda section: section.find_all('div', class_='box'),
            "format": lambda boxes: '\n\n'.join([
                f"{box.find('h3').get_text().strip()}\n{box.find('p').get_text().strip()}" 
                for box in boxes
            ])
        },
        "partners": {
            "heading": "Our Partners",
            "extract": lambda section: section.find_all('div', class_='box'),
            "format": lambda boxes: '\n\n'.join([
                f"{box.find('h3').get_text().strip()}\n{box.find('p').get_text().strip()}" 
                for box in boxes
            ])
        },
        "key-features": {
            "heading": "Platform Features",
            "extract": lambda section: section.find_all('div', class_='box'),
            "format": lambda boxes: "Key Features:\n" + '\n'.join([
                f"- {box.find('h3').get_text().strip()}" for box in boxes
            ])
        },
        "get-involved": {
            "heading": "Get Involved",
            "extract": lambda section: section.find_all('div', class_='box'),
            "format": lambda boxes: '\n\n'.join([
                f"{box.find('h3').get_text().strip()}\n{box.find('p').get_text().strip()}" 
                for box in boxes
            ])
        }
    }
    
    # Get configuration for the requested section
    config = section_configs.get(section)
    if not config:
        return f"Section '{section}' not found"
    
    # Find the section and extract content
    section_element = soup.find('h2', string=config["heading"])
    if not section_element:
        return f"{config['heading']} section not found"
    
    items = config["extract"](section_element.find_parent())
    return config["format"](items)

# Helper functions --------------------------------------------------------------------------------------

def format_dataset_search_response(response: dict) -> str:
    """
    Format the dataset search response into a string.
    """

    result = response.get("result", {})
    number_of_datasets_found = result.get("count", 0)
    datasets = result.get("results", [])

    result_string = ""
    for result in datasets:
        result_string += f""" Dataset name: {result.get("name")}
        Dataset title: {result.get("title")}
        Dataset notes: {result.get("notes")}
        Dataset url: {result.get("url")}
        Dataset organization: {result.get("organization")}
        Dataset tags: {result.get("tags")}
        \n\n"""


    if number_of_datasets_found == 0:
        return "No datasets found."
    
    return result_string


if __name__ == "__main__":
    import sys
    sys.exit(mcp.run(
        transport="http", 
        host="127.0.0.1", 
        port=8000, 
        path="/mcp", 
        log_level="debug"
        ))