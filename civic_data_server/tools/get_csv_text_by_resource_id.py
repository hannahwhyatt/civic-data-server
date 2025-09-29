import requests
import os
import csv
from io import BytesIO, StringIO
import pandas as pd

ckan_user_api_key = os.getenv("CKAN_USER_API_KEY")


def register(mcp):
    @mcp.tool(
    tags={"public"},
)
    async def get_csv_file_by_resource_id(
        resource_id: str,
    ) -> str:
        """Get a CSV or Excel resource by ID. Return the text content as a string."""
    # Check if the resource has been read before
        path = f"civic_data_server/data/{resource_id}.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            return df.to_string()
        
        # Get the resource metadata
        resource_url = f"https://www.liverpoolcivicdata.com/api/3/action/resource_show?id={resource_id}"
        try:
            response = requests.get(resource_url, timeout=30)
            response.raise_for_status()
            metadata = response.json()
            
            result = metadata.get("result", {})
            url = result.get("url")
            if not url:
                return f"Error retrieving resource: {metadata.get('error')}"
            
            # Check metadata for file type information
            file_format = (result.get("format") or "").lower()
            mimetype = (result.get("mimetype") or "").lower()
            name = (result.get("name") or "").lower()
            
            # Download the file
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Detect file type using CKAN metadata first, then content analysis
            content = response.content
            
            # Enhanced Excel file detection
            is_excel_file = (
                # Check format field
                file_format in ['xlsx', 'xlsm', 'xls', 'excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'] or
                # Check mimetype
                'excel' in mimetype or
                'spreadsheet' in mimetype or
                'vnd.openxmlformats-officedocument.spreadsheetml.sheet' in mimetype or
                'vnd.ms-excel' in mimetype or
                # Check filename extension
                name.endswith('.xlsx') or name.endswith('.xlsm') or name.endswith('.xls') or
                # Check URL extension
                url.lower().endswith('.xlsx') or url.lower().endswith('.xlsm') or url.lower().endswith('.xls') or
                # Check content magic bytes
                content.startswith(b'PK') or  # ZIP magic bytes (modern Excel files)
                content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')  # OLE magic bytes (older Excel files)
            )
            
            if is_excel_file:
                # Handle Excel file
                try:
                    excel_file = BytesIO(content)
                    # Try to read Excel file, use first sheet by default
                    df = pd.read_excel(excel_file, engine='openpyxl')
                except Exception as e:
                    try:
                        # Fallback to xlrd engine for older .xls files
                        excel_file = BytesIO(content)
                        df = pd.read_excel(excel_file, engine='xlrd')
                    except Exception as e2:
                        # If Excel parsing fails, try one more approach with no engine specified
                        try:
                            excel_file = BytesIO(content)
                            df = pd.read_excel(excel_file)
                        except Exception as e3:
                            return f"Error reading Excel file (Format:{file_format}, Mimetype:{mimetype}, URL:{url}): openpyxl error: {str(e)}, xlrd error: {str(e2)}, default error: {str(e3)}"
            
            else:
                # Handle as CSV/text file
                csv_content = None
                for encoding in ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']:
                    try:
                        csv_content = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if csv_content is None:
                    return "Error: Could not decode file with any common encoding"
                
                # Try a more robust approach using csv module first to clean the data
                df = None
                
                # Method 1: Try with csv.Sniffer to detect format
                try:
                    csv_file_like = StringIO(csv_content)
                    sample = csv_content[:1024]  # Sample for dialect detection
                    sniffer = csv.Sniffer()
                    dialect = sniffer.sniff(sample, delimiters=',;\t|')
                    
                    csv_file_like.seek(0)
                    df = pd.read_csv(csv_file_like, dialect=dialect)
                    
                except Exception:
                    # Method 2: Manual CSV parsing with different dialects
                    csv_dialects = [
                        csv.excel,
                        csv.excel_tab,
                        csv.unix_dialect,
                    ]
                    
                    for dialect in csv_dialects:
                        try:
                            csv_file_like = StringIO(csv_content)
                            reader = csv.reader(csv_file_like, dialect=dialect)
                            rows = []
                            headers = None
                            
                            for i, row in enumerate(reader):
                                if i == 0:
                                    headers = row
                                else:
                                    # Pad or truncate rows to match header length
                                    if len(row) < len(headers):
                                        row.extend([''] * (len(headers) - len(row)))
                                    elif len(row) > len(headers):
                                        row = row[:len(headers)]
                                    rows.append(row)
                            
                            if headers and rows:
                                df = pd.DataFrame(rows, columns=headers)
                                break
                                
                        except Exception:
                            continue
                    
                    # Method 3: Fallback with very permissive pandas options
                    if df is None:
                        try:
                            csv_file_like = StringIO(csv_content)
                            df = pd.read_csv(
                                csv_file_like,
                                engine='python',
                                sep=None,
                                quoting=csv.QUOTE_NONE,
                                on_bad_lines='skip',
                                skipinitialspace=True,
                                skip_blank_lines=True
                            )
                        except Exception:
                            # Method 4: Last resort - try to clean the content manually
                            try:
                                # Remove problematic characters and normalize line endings
                                cleaned_content = csv_content.replace('\r\n', '\n').replace('\r', '\n')
                                # Remove any null bytes that might cause issues
                                cleaned_content = cleaned_content.replace('\x00', '')
                                
                                csv_file_like = StringIO(cleaned_content)
                                df = pd.read_csv(
                                    csv_file_like,
                                    engine='python',
                                    sep=',',
                                    quotechar='"',
                                    doublequote=True,
                                    skipinitialspace=True,
                                    on_bad_lines='skip'
                                )
                            except Exception as e:
                                return f"Error: Could not parse CSV file with any method. Last error: {str(e)}"
                
                if df is None or df.empty:
                    return "Error: Could not parse file - no valid data found"
            
            # Save the CSV to a file for future use
            os.makedirs("civic_data_server/data", exist_ok=True)
            df.to_csv(path, index=False)
            
            return df.to_string()

        except requests.Timeout:
            return "Error: Request timed out while downloading CSV"
        except requests.RequestException as e:
            return f"Error downloading csv: {str(e)}"
        except Exception as e:
            return f"Error processing CSV request: {str(e)}"