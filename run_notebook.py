"""Execute the coursework notebook using a local Jupyter kernel."""
from pathlib import Path
import os
import nbformat
from nbclient import NotebookClient
root = Path(__file__).resolve().parent
os.environ.setdefault('JUPYTER_RUNTIME_DIR', '/tmp/retail-jupyter')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/retail-matplotlib')
path = root / 'science_work_simple.ipynb'
notebook = nbformat.read(path, as_version=4)
NotebookClient(notebook, timeout=180,
               resources={'metadata': {'path': str(root)}}).execute()
nbformat.write(notebook, path)
print('Notebook executed successfully')
