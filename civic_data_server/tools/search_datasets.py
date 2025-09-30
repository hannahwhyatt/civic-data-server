from typing import Annotated
from pydantic import Field
import requests
import os

ckan_user_api_key = os.getenv("CKAN_USER_API_KEY")


# Formatting API response ---------------------------------------------------------------------
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


# Tool --------------------------------------------------------------------------------------
def register(mcp):
    @mcp.tool(
        tags={"public"},
    )
    async def search_datasets(
        query: Annotated[
            str,
            Field(description="The query to search for datasets.")
        ]
        ) -> str:
        """Searches for datasets (collections of files) using keywords. Use this as your starting point for broad, thematic exploration when you want to discover what data collections are available about a topic like 'housing' or 'employment'. Returns a list of datasets with their IDs. If the query is empty, it returns a list of all available datasets.
        """
        
        ckan_api_base_url = "https://www.liverpoolcivicdata.com/api/3"

        headers = {'Authorization': ckan_user_api_key}
        path = f"{ckan_api_base_url}/action/package_search?q={query}"


        try:
            response = requests.get(path, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("success") == True:
                return format_dataset_search_response(data) + "\n\nEnd of results. Use ONLY the results that are relevant to the user's request."
            else:
                return f"Error retrieving dataset search results: {data.get('error')}"
        except requests.RequestException as e:
            return f"Error retrieving dataset search results: {str(e)}"