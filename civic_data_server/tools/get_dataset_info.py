from typing import Annotated
from pydantic import Field
import requests
import os
from random import sample

ckan_user_api_key = os.getenv("CKAN_USER_API_KEY")


# Formatting API response ---------------------------------------------------------------------
def format_dataset_metadata_response(response: dict) -> str:
    """
    Format the dataset metadata response into a string.
    """
    response = response.get("result", {})
    id = response.get("name", "")
    dataset_name = response.get("title", "")
    publishing_organization_name = response.get("organization", {}).get("title", "")
    url = response.get("url", "")
    tags = response.get("tags", "")
    license = response.get("license_title", "Not known")
    notes = response.get("notes", "")
    resources = response.get("resources", [])
    resource_list = []
    for resource in resources:
        resource_name = resource.get("name", "")
        resource_id = resource.get("id", "")
        resource_format = resource.get("format", "")
        resource_url = resource.get("url", "")
        resource_list.append(f"{resource_name} - {resource_id} - {resource_format} - {resource_url}")

    if len(resource_list) > 20:
        resource_list = ["Total number of resources found: " + str(len(resource_list)) + ". A random selection of 20 resources are shown."] + sample(resource_list, 20)

    result_string = f"""Dataset name: {dataset_name}
    Dataset title: {dataset_name}
    Dataset id: {id}
    Dataset notes: {notes}
    Dataset url: {url}
    Dataset organization: {publishing_organization_name}
    Dataset tags: {", ".join([tag.get("display_name") for tag in tags])}
    Dataset license: {license}
    Dataset resources (files): {",\n    ".join(resource_list)}
    """
    return result_string

# Tool --------------------------------------------------------------------------------------
def register(mcp):
    @mcp.tool(
    tags={"public"},
)
    async def get_dataset_info(
        dataset_name: Annotated[
            str,    
            Field(description="The name of the dataset to get the metadata for.")],
        ) -> str:

        """Retrieves complete metadata for a specific dataset using its ID. Use this after search_datasets to see all the files within a dataset, or after search_resources (using the package_id) to get more context about a specific file. It provides the list of all available resources (files) with their resource IDs and formats, which are required to access their content.
        """

        ckan_api_base_url = "https://www.liverpoolcivicdata.com/api/3"

        headers = {'Authorization': ckan_user_api_key}

        def dataset_search_and_get_id(dataset_name: str) -> str:
            path = f"{ckan_api_base_url}/action/package_search?q={dataset_name}"
            try:
                response = requests.get(path, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                if data.get("success") == True:
                    print(data.get("result", {}).get("results", [])[0].get("id"))
                    return data.get("result", {}).get("results", [])[0].get("id")
                else:
                    return f"Error retrieving dataset search results: {data.get('error')}"
            except requests.RequestException as e:
                return f"Error retrieving dataset search results: {str(e)}"

        try:
            # First, peform a dataset search to get the id of the dataset
            dataset_id = dataset_search_and_get_id(dataset_name)

            if not dataset_id:
                return f"Error retrieving dataset metadata: No dataset found with name {dataset_name}"
            
            path = f"{ckan_api_base_url}/action/package_show?id={dataset_id}"

            response = requests.get(path, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("success") == True:
                return format_dataset_metadata_response(data)
            else:
                return f"Error retrieving dataset metadata: {data.get('error')}"
            
        except requests.RequestException as e:
            return {"error": f"Error retrieving dataset metadata: {str(e)}"}