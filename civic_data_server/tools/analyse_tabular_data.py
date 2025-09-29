import pandas as pd
import json



def register(mcp):
    @mcp.tool(
    tags={"public"},
)
    async def analyse_tabular_data(
        resource_id: str,
    ) -> str:
        """Perform automated analysis on CSV or Excel data to understand its structure, data types, statistical properties, missing values, and potential issues. Returns column names, data types, basic statistics, row count, and data quality indicators. Use this after retrieving content to understand the data before writing custom analysis code."""
        
        df = pd.read_csv('civic_data_server/data/' + resource_id + '.csv')
    
        info = {}

        # Basic shape and columns
        info['shape'] = df.shape
        info['columns'] = list(df.columns)

        # Data types
        info['dtypes'] = df.dtypes.apply(lambda x: str(x)).to_dict()

        # Missing values
        info['missing_values'] = df.isnull().sum().to_dict()

        # Number of unique values (helps spot categorical vs. continuous)
        info['unique_counts'] = df.nunique().to_dict()

        # Example values (first 5 unique per column)
        info['sample_values'] = {
            col: df[col].dropna().unique()[:5].tolist() for col in df.columns
        }

        # Quick numeric stats
        info['numeric_summary'] = df.describe().to_dict()

        return json.dumps(info, default=str)