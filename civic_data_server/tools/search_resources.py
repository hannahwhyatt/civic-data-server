from typing import Annotated
from pydantic import Field
import requests
import os

ckan_user_api_key = os.getenv("CKAN_USER_API_KEY")


# Formatting API response ---------------------------------------------------------------------
def format_resource_search_response(response: dict) -> str:
    """
    Format the dataset search response into a string.
    """

    result = response.get("result", {})
    number_of_resources_found = result.get("count", 0)
    resources = result.get("results", [])

    result_string = ""
    for result in resources:
        result_string += f""" 
        Resource name: {result.get("name")}
        Resource format: {result.get("format")}
        Resource url: {result.get("url")}
        Resource id: {result.get("id")}
        Dataset id: {result.get("package_id")}
        \n\n"""
    if number_of_resources_found == 0:
        return "No resources found."
    
    return result_string    


# Tool --------------------------------------------------------------------------------------
def register(mcp):
    @mcp.tool(
        tags={"public"},
    )
    async def search_resources(
        query: Annotated[
            str,
            Field(description="The query to search for resources.")
        ]
        ) -> str:
        """Searches directly for individual files (resources) like CSVs or PDFs using keywords. Use this as a shortcut when the user asks for a specific file, report, or data format. Returns the resource name, format, URL, resource ID, and the ID of the dataset it belongs to (package_id).
        """
        
        ckan_api_base_url = "https://www.liverpoolcivicdata.com/api/3"

        query_words = query.split(" ")
    

        headers = {'Authorization': ckan_user_api_key}

        result_list = []
        for word in query_words:
            path = f"{ckan_api_base_url}/action/resource_search?query=name:{word}"
            response = requests.get(path, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("success") == True:
                result_list.append(format_resource_search_response(data))
            else:
                continue

        return "\n\n".join(result_list)