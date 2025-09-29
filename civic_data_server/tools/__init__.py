import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from civic_data_server.tools.run_python import register as register_run_python
from civic_data_server.tools.search_datasets import register as register_search_datasets
from civic_data_server.tools.get_dataset_info import register as register_get_dataset_info
from civic_data_server.tools.get_resource_content import register as register_get_resource_content
from civic_data_server.tools.analyse_tabular_data import register as register_analyse_tabular_data
from civic_data_server.tools.search_resources import register as register_search_resources

def register_all(mcp):  
    register_search_datasets(mcp)    
    register_search_resources(mcp)
    register_get_dataset_info(mcp)
    register_get_resource_content(mcp)
    register_analyse_tabular_data(mcp)
    register_run_python(mcp)
