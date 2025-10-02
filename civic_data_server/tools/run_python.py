from typing import Annotated
from pydantic import Field
import asyncio
import tempfile
import sys
import json
import os
import uuid
import shutil
from pathlib import Path
import dotenv

dotenv.load_dotenv()
base_url = os.getenv("BACKEND_DOMAIN")
if not base_url:
    base_url = "https://www.liverpoolcivicdata.com"

current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(current_dir))
image_default_path = os.path.join(tempfile.gettempdir(), "plot")

def register(mcp):
    @mcp.tool(
        tags={"public"},
    )
    async def run_python(
        code: Annotated[
            str,
            Field(description="""Python code to run. For data analysis workflow:
1. First use 'get_resource_content' to fetch and cache a resource.
2. Then use 'analyse_tabular_data' to understand its structure.
3. Finally, use this tool for custom analysis and visualization.

In general, start all scripts with the following line:
    import os
    os.environ['MPLCONFIGDIR'] = os.getcwd() + "/configs/"

For tabular files, construct the path to the cached file in the temp directory, like this:
    import os
    os.environ['MPLCONFIGDIR'] = os.getcwd() + "/configs/"
    import tempfile
    import pandas as pd
    # resource_id must be defined and the file must be cached
    resource_id = "your_resource_id"
    path = os.path.join(tempfile.gettempdir(), f"{resource_id}.csv")
    df = pd.read_csv(path)

For plots:
- Use matplotlib for visualizations
- Figures will be automatically saved as PNG images and referenced by URL
"""),
        ],
        timeout_seconds: Annotated[int, Field(description="Maximum time in seconds to allow execution.")]=60,
        capture_plots: Annotated[
            bool,
            Field(description="If true, collect matplotlib figures and return them as URLs to PNG images saved on the server.")
        ] = True,
        return_markdown: Annotated[
            bool,
            Field(description="If true, also return a ready-to-render markdown block combining stdout/stderr and any plots.")
        ] = True,
        save_images: Annotated[
            bool,
            Field(description="If true, save captured plots as PNG files on the server and return URLs.")
        ] = True,
        image_path: Annotated[
            str,
            Field(description="Directory to save images if save_images=True. Defaults to project's temp/plot directory.")
        ] = image_default_path,
        debug: Annotated[
            bool,
            Field(description="If true, emit extra debug logs to stderr during execution.")
        ] = False,
    ) -> dict:
        """Run Python code in a subprocess and return a structured result suitable for chat UIs.

        Returns a dict with:
        - stdout: text captured from standard output
        - stderr: text captured from standard error
        - exit_code: integer process return code
        - plots: list of plot descriptors. Each item has format:
          - {type: 'base64', title: '...', url: '/path/to/image.png'}
          Each plot also includes a convenience 'markdown' field when return_markdown=True.
        - markdown: (optional) a single ready-to-render markdown block combining stdout/stderr and all figures
        - debug_info: internal counters for troubleshooting
        """

        # Validate inputs
        try:
            timeout_seconds = int(timeout_seconds)
        except Exception:
            timeout_seconds = 60
        if timeout_seconds <= 0:
            timeout_seconds = 60

        plot_collector = (
            "\n"
            "# --- MCP plot collector ---\n"
            "try:\n"
            "    import matplotlib\n"
            "    matplotlib.use('Agg')  # Non-interactive backend for server environments\n"
            "    import matplotlib.pyplot as plt\n"
            "    import matplotlib._pylab_helpers as pylab_helpers\n"
            "    import json as _json\n"
            "    import io, base64, sys, os\n"
            "    _DEBUG = os.environ.get('MCP_RUN_PY_DEBUG') == '1'\n"
            "    _plots = []\n"
            "    if _DEBUG: print('DEBUG: Starting plot collection...', file=sys.stderr)\n"
            "    # Force matplotlib to materialize figures (no-op in Agg)\n"
            "    try:\n"
            "        plt.show(block=False)\n"
            "    except Exception as _e:\n"
            "        if _DEBUG: print(f'DEBUG: plt.show() error: {_e}', file=sys.stderr)\n"
            "    fig_managers = list(pylab_helpers.Gcf.get_all_fig_managers())\n"
            "    if _DEBUG: print(f'DEBUG: Found {len(fig_managers)} matplotlib figure managers', file=sys.stderr)\n"
            "    for i, _fm in enumerate(fig_managers):\n"
            "        try:\n"
            "            fig = _fm.canvas.figure\n"
            "            if _DEBUG: print(f'DEBUG: Processing matplotlib figure {i+1}', file=sys.stderr)\n"
            "            # Save as PNG image with optimised settings for smaller file size\n"
            "            _buf = io.BytesIO()\n"
            "            # Set standard figure size and lower DPI for smaller file size\n"
            "            fig.set_size_inches(8, 6)\n"
            "            fig.savefig(_buf, format='png', bbox_inches='tight', dpi=100)\n"
            "            _title = ''\n"
            "            try:\n"
            "                _title = fig.axes[0].get_title() if getattr(fig, 'axes', None) and len(fig.axes) > 0 else 'Plot'\n"
            "            except Exception:\n"
            "                _title = 'Plot'\n"
            "            _plots.append({'type': 'base64', 'data': 'data:image/png;base64,' + base64.b64encode(_buf.getvalue()).decode('ascii'), 'title': _title})\n"
            "            if _DEBUG: print(f'DEBUG: Added base64 plot {i+1}', file=sys.stderr)\n"
            "        except Exception as _e:\n"
            "            if _DEBUG: print(f'DEBUG: Error processing matplotlib figure {i+1}: {_e}', file=sys.stderr)\n"
            "            try:\n"
            "                _buf = io.BytesIO()\n"
            "                # Set standard figure size and lower DPI for smaller file size\n"
            "                fig.set_size_inches(8, 6)\n"
            "                fig.savefig(_buf, format='png', bbox_inches='tight', dpi=72)\n"
            "                _plots.append({'type': 'base64', 'data': 'data:image/png;base64,' + base64.b64encode(_buf.getvalue()).decode('ascii'), 'title': 'Plot'})\n"
            "                if _DEBUG: print(f'DEBUG: Added fallback base64 plot {i+1}', file=sys.stderr)\n"
            "            except Exception as __e:\n"
            "                if _DEBUG: print(f'DEBUG: Failed to create fallback plot {i+1}: {__e}', file=sys.stderr)\n"
            "                pass\n"
            "    # Check for Plotly figures and convert them to PNG\n"
            "    if _DEBUG: print('DEBUG: Checking for Plotly figures in global scope...', file=sys.stderr)\n"
            "    try:\n"
            "        import plotly\n"
            "        import plotly.io as pio\n"
            "        plotly_found = 0\n"
            "        for name, obj in list(globals().items()):\n"
            "            try:\n"
            "                if hasattr(obj, 'to_image') and callable(getattr(obj, 'to_image', None)) and hasattr(obj, '_data') and hasattr(obj, 'layout'):\n"
            "                    if _DEBUG: print(f'DEBUG: Found Plotly figure: {name}', file=sys.stderr)\n"
            "                    # Convert Plotly to PNG\n"
            "                    _title = 'Plotly Plot'\n"
            "                    try:\n"
            "                        if hasattr(obj, 'layout') and hasattr(obj.layout, 'title') and getattr(obj.layout.title, 'text', None):\n"
            "                            _title = obj.layout.title.text\n"
            "                    except Exception:\n"
            "                        pass\n"
            "                    # Convert to PNG with optimized settings\n"
            "                    img_bytes = obj.to_image(format='png', width=800, height=600, scale=1.0)\n"
            "                    _plots.append({'type': 'base64', 'data': 'data:image/png;base64,' + base64.b64encode(img_bytes).decode('ascii'), 'title': _title})\n"
            "                    plotly_found += 1\n"
            "                    if _DEBUG: print(f'DEBUG: Added Plotly plot as PNG: {name}', file=sys.stderr)\n"
            "            except Exception as e:\n"
            "                if _DEBUG: print(f'DEBUG: Error processing {name}: {e}', file=sys.stderr)\n"
            "                continue\n"
            "        if _DEBUG: print(f'DEBUG: Found {plotly_found} Plotly figures', file=sys.stderr)\n"
            "    except ImportError:\n"
            "        if _DEBUG: print('DEBUG: Plotly not available for figure detection', file=sys.stderr)\n"
            "    except Exception as e:\n"
            "        if _DEBUG: print(f'DEBUG: Error in Plotly detection: {e}', file=sys.stderr)\n"
            "    if _DEBUG: print(f'DEBUG: Total plots collected: {len(_plots)}', file=sys.stderr)\n"
            "    print()\n"
            "    print('__MCP_PLOTS__=' + _json.dumps(_plots))\n"
            "except Exception as _e:\n"
            "    try:\n"
            "        import sys\n"
            "        print(f'DEBUG: Plot collector error: {_e}', file=sys.stderr)\n"
            "        import json as _json\n"
            "        print('__MCP_PLOTS__=' + _json.dumps([]))\n"
            "    except Exception:\n"
            "        pass\n"
        )

        if capture_plots:
            wrapped_code = f"{code}\n\n{plot_collector}\n"

        else:
            wrapped_code = code

        # Write to a temporary file to avoid shell quoting issues
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(wrapped_code)
            tmp_path = tmp.name

        env = os.environ.copy()
        if debug:
            env["MCP_RUN_PY_DEBUG"] = "1"
        else:
            env.pop("MCP_RUN_PY_DEBUG", None)

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            stdout_bytes, stderr_bytes = b"", f"Timed out after {timeout_seconds} seconds".encode()
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")

        marker = "__MCP_PLOTS__="
        marker_found = marker in stdout_text

        plots = []
        if marker_found:
            lines = stdout_text.splitlines()
            remaining_lines = []
            for line in lines:
                if line.startswith(marker):
                    try:
                        plots = json.loads(line[len(marker):])
                    except Exception:
                        plots = []
                else:
                    remaining_lines.append(line)
            stdout_text = "\n".join(remaining_lines)

        # Save images to disk if requested
        image_urls = []
        if save_images and plots:
            # Try to create directory and verify writability
            try:
                os.makedirs(image_path, exist_ok=True)
                dir_ready = os.access(image_path, os.W_OK)
            except Exception as e:
                if debug:
                    print(f"Warning: Could not create image directory {image_path}: {e}", file=sys.stderr)
                dir_ready = False

            if not dir_ready:
                if debug:
                    print(f"Warning: Image directory {image_path} is not writable; falling back to base64 only.", file=sys.stderr)
                save_images = False
            else:
                # Determine if this directory is publicly served (project temp/plot)
                public_plot_dir = os.path.join(project_dir, "temp", "plot")
                is_public_served = os.path.abspath(image_path) == os.path.abspath(public_plot_dir)

                # Save each plot as a file
                for i, p in enumerate(plots):
                    if p.get('type') == 'base64' and p.get('data'):
                        try:
                            # Extract the base64 data (remove the data:image/png;base64, prefix)
                            img_data = p['data'].split(',', 1)[1]

                            # Generate a unique filename
                            filename = f"plot_{uuid.uuid4().hex}.png"

                            filepath = os.path.join(image_path, filename)

                            # Write the file
                            import base64
                            with open(filepath, 'wb') as f:
                                f.write(base64.b64decode(img_data))
                            # Ensure file is readable by web server
                            os.chmod(filepath, 0o644)

                            # Add URL only if saving to publicly served directory
                            if is_public_served:
                                base = (base_url or "").rstrip('/')
                                url_path = f"{base}/temp/plot/{filename}"
                                p['url'] = url_path
                                image_urls.append(url_path)
                                # Remove the base64 data to reduce payload size when URL is available
                                if 'data' in p:
                                    del p['data']

                            if debug:
                                print(f"Saved image to {filepath}", file=sys.stderr)
                        except Exception as e:
                            if debug:
                                print(f"Error saving image: {e}", file=sys.stderr)

        # Optionally compose a markdown block that a chatbot can render directly
        markdown = None
        if return_markdown:
            parts = []
            parts.append("### Python Execution Result")
            if stdout_text.strip():
                parts.append("#### Stdout\n\n```text\n" + stdout_text.rstrip() + "\n```")
            else:
                parts.append("#### Stdout\n\n```text\n<no output>\n```")
            if stderr_text.strip():
                parts.append("#### Stderr (warnings/errors)\n\n```text\n" + stderr_text.rstrip() + "\n```")
            if plots:
                parts.append("### Figures")
                for i, p in enumerate(plots, start=1):
                    title = p.get('title') or f'Plot {i}'
                    if p.get('url'):
                        # Use the URL if available
                        md_img = f"![{title}]({p['url']})"
                        parts.append(f"#### {title}\n\n" + md_img)
                        p['markdown'] = md_img
                    elif not save_images and p.get('type') == 'base64' and p.get('data'):
                        # Only use base64 if explicitly requested not to save images
                        md_img = f"![{title}]({p['data']})"
                        parts.append(f"#### {title}\n\n" + md_img)
                        p['markdown'] = md_img
                    else:
                        # No URL and no data, just add a placeholder
                        parts.append(f"#### {title}\n\n(Image not available)")
                        p['markdown'] = f"(Image not available)"
            markdown = "\n\n".join(parts)

        # Create a clean version of plots without base64 data for the response
        clean_plots = []
        for p in plots:
            # Create a copy of the plot without the base64 data
            clean_plot = {k: v for k, v in p.items() if k != 'data'}
            clean_plots.append(clean_plot)
            
        return {
            "stdout": stdout_text,
            "stderr": stderr_text,
            "exit_code": proc.returncode,
            "plots": clean_plots,  # Use the clean version without base64 data
            "markdown": markdown,
            "debug_info": {
                "plots_found": len(plots),
                "plot_types": [p.get('type', 'unknown') for p in plots] if plots else [],
                "marker_found": marker_found,
                "stdout_length": len(stdout_text),
                "stderr_length": len(stderr_text),
                "images_saved": len(image_urls) if save_images else 0,
                "image_path": image_path if save_images else None
            }
        }