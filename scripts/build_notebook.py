"""Build and execute an explained EDA notebook from the reproducible analysis."""
from pathlib import Path
import nbformat
from nbclient import NotebookClient
root=Path(__file__).resolve().parents[1]
def build():
    report=(root/'reports/eda/EDA_REPORT.md').read_text()
    report=report.replace('](figures/','](../reports/eda/figures/').replace('](../../docs/','](../docs/')
    cells=[nbformat.v4.new_markdown_cell('# Reproducible RDU EDA\n\nRun all cells after installing requirements and unpacking data. The first cell regenerates the complete reports, figures and numeric tables from the saved snapshot. Later cells explain results and display selected tables. The module source is in `src/eda.py`; data boundary rules are in `src/data_access.py`. No final observed outcomes are loaded.'),
           nbformat.v4.new_code_cell("from pathlib import Path\nimport sys\nroot = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p/'src/eda.py').exists())\nsys.path.insert(0, str(root))\nfrom src.eda import run_eda\nsummary, explanations = run_eda(root)\nsummary")]
    for chunk in report.split('\n### '):
        cells.append(nbformat.v4.new_markdown_cell(chunk if chunk.startswith('#') else '### '+chunk))
    for name,description in [('temperature_distributions','Distribution counts and quantiles for the training scopes'),
                             ('elapsed_lag_correlations','Selected elapsed-time lag correlations, never concatenated seasonal rows'),
                             ('seasonal_feature_availability','Weather-input missingness'),
                             ('gfs_calibration_metrics_by_day','Calibration-only GFS routine-report errors by forecast day')]:
        cells.append(nbformat.v4.new_markdown_cell('## '+description))
        code=f"import pandas as pd\ntable = pd.read_csv(root/'reports/eda/tables/{name}.csv')\n"
        code += "table.loc[table.lag_hours.isin([1, 24, 72, 168, 336])]" if name=='elapsed_lag_correlations' else 'table'
        cells.append(nbformat.v4.new_code_cell(code))
    nb=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}})
    client=NotebookClient(nb,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(root/'notebooks')}})
    client.execute()
    # The first code cell regenerates the report. Refresh Markdown from that
    # result so an old saved report cannot leave stale status text in the notebook.
    report=(root/'reports/eda/EDA_REPORT.md').read_text()
    report=report.replace('](figures/','](../reports/eda/figures/').replace('](../../docs/','](../docs/')
    for i,chunk in enumerate(report.split('\n### ')):
        nb.cells[i+2].source=chunk if chunk.startswith('#') else '### '+chunk
    nbformat.write(nb,root/'notebooks/01_rdu_eda.ipynb')
    print(f'Executed notebook: {len(cells)} cells; no error outputs.')
if __name__=='__main__':build()
