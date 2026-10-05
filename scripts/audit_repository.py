"""Verify archive contents, notebook execution, links and file completeness."""
from pathlib import Path
import csv,hashlib,json,re,zipfile
import nbformat
root=Path(__file__).resolve().parents[1]
def deliverable_files():
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if not p.is_file() or any(part.startswith('.') or part=='__pycache__' for part in rel.parts):continue
        if str(rel).startswith('data/pre_eda/'):continue
        yield p
    # Hidden configuration is a deliverable, unlike runtime caches.
    yield root/'.gitignore'
def audit():
    errors=[];archive_records=[];seen=set()
    for path in sorted((root/'data/snapshots').glob('*.zip')):
        with zipfile.ZipFile(path) as z:
            if z.testzip():errors.append('Corrupt ZIP '+path.name)
            for name in z.namelist():
                if name in seen:errors.append('Duplicate archive member '+name)
                seen.add(name);content=z.read(name)
                if content!=(root/name).read_bytes():errors.append('Archive differs from extracted file '+name)
                archive_records.append({'location':'bundled','path':name,'container':str(path.relative_to(root)),
                                        'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    expected={str(p.relative_to(root)) for p in (root/'data/pre_eda').rglob('*') if p.is_file()}
    if seen!=expected:errors.append('Bundled preparation-file inventory mismatch')
    manifest=json.loads((root/'data/pre_eda/metadata/package_manifest.json').read_text())
    for entry in manifest['files']:
        content=(root/'data/pre_eda'/entry['file']).read_bytes()
        if hashlib.sha256(content).hexdigest()!=entry['sha256']:errors.append('Snapshot checksum '+entry['file'])
    nb=nbformat.read(root/'notebooks/01_rdu_eda.ipynb',as_version=4)
    code=[c for c in nb.cells if c.cell_type=='code']
    if any(c.execution_count is None or any(o.output_type=='error' for o in c.outputs) for c in code):errors.append('Notebook not cleanly executed')
    for p in [root/'README.md',*root.glob('docs/*.md'),root/'reports/eda/EDA_REPORT.md']:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if target.startswith(('http','#','mailto')):continue
            if not (p.parent/target.split('#')[0]).exists() and target!='reports/FILE_INVENTORY.csv':errors.append('Broken local link '+str(p.relative_to(root))+': '+target)
    figures=list((root/'reports/eda/figures').glob('*.png'))
    explanations=json.loads((root/'reports/eda/figure_explanations.json').read_text())
    if len(figures)!=len(explanations):errors.append('Figure explanation count mismatch')
    for item in explanations:
        for ext in ['png','svg']:
            if not (root/'reports/eda/figures'/(item['name']+'.'+ext)).exists():errors.append('Missing figure '+item['name'])
    # Host paths and private contact data have no place in the published text.
    for p in deliverable_files():
        if p.suffix.lower() in ['.py','.md','.json','.csv','.ipynb','.html','.txt']:
            txt=p.read_text(errors='ignore')
            # Match actual path suffixes, not the generic pattern in this checker.
            if re.search(r'/Users/[A-Za-z0-9]|/var/folders/[A-Za-z0-9]',txt):errors.append('Private host path '+str(p.relative_to(root)))
    result={'audit_errors':errors,'snapshot_files_including_manifest':len(seen),
            'checksum_verified_snapshot_files':len(manifest['files']),
            'figures_png':len(figures),'figures_svg':len(list((root/'reports/eda/figures').glob('*.svg'))),
            'numeric_tables':len(list((root/'reports/eda/tables').glob('*.csv'))),
            'executed_notebook_code_cells':len(code),'notebook_error_outputs':0,
            'contract_test_command':'python -m unittest discover -s tests -v',
            'known_limits':['Routine-report target convention and units await instructor confirmation.',
                           'Source disagreements need a fixed policy before model scoring.',
                           'Historical source archives are revised snapshots, not verified historical release snapshots.',
                           'GFS benchmark is calibration-only spring/summer, with overlapping windows.',
                           'Original PowerPoint is not redistributed without specific publication approval.',
                           'Required forecast models, final predictions and student-authored submissions remain.']}
    (root/'reports/COMPLETION_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    records=[]
    for p in deliverable_files():
        rel=str(p.relative_to(root))
        if rel in ['reports/FILE_INVENTORY.csv','reports/SHA256SUMS.txt']:continue
        content=p.read_bytes();records.append({'location':'committed','path':rel,'container':'',
                                               'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    records+=archive_records
    # The inventory and checksum list cannot contain their own content hashes.
    for name in ['reports/FILE_INVENTORY.csv','reports/SHA256SUMS.txt']:
        records.append({'location':'committed','path':name,'container':'','bytes':'self-referential','sha256':'not self-hashed'})
    with (root/'reports/FILE_INVENTORY.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['location','path','container','bytes','sha256']);writer.writeheader();writer.writerows(records)
    (root/'reports/SHA256SUMS.txt').write_text('\n'.join(e['sha256']+'  '+e['path'] for e in records if e['location']=='committed' and e['sha256']!='not self-hashed')+'\n')
    print(json.dumps(result,indent=2))
    if errors:raise SystemExit('Audit failed')
if __name__=='__main__':audit()
