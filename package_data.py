"""Rebuild public snapshots from an unpacked, audited preparation directory."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[1];base=root/'data/pre_eda'
def package():
    records=[]
    for p in sorted(base.rglob('*')):
        if p.is_file() and p.name!='package_manifest.json':
            records.append({'file':str(p.relative_to(base)),'bytes':p.stat().st_size,
                            'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (base/'metadata/package_manifest.json').write_text(json.dumps({'snapshot':'Public reproducible preparation snapshot',
        'public_copy_change':'Only source-deck local path removed; measurement files unchanged. Manifest refreshed.',
        'files':records},indent=2)+'\n')
    for label,dirs in [('raw',['raw']),('prepared',['prepared']),('records',['metadata','reports','reproducibility'])]:
        dest=root/'data/snapshots'/('pre_eda_'+label+'.zip')
        with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for d in dirs:
                for p in sorted((base/d).rglob('*')):
                    if p.is_file():z.write(p,str(p.relative_to(root)))
            if label=='records':
                for p in sorted(base.glob('*.md')):z.write(p,str(p.relative_to(root)))
        print(dest.name,dest.stat().st_size)
if __name__=='__main__':package()
