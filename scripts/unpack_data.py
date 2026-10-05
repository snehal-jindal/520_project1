"""Restore bundled source/prepared snapshots and verify every file checksum."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[1]
def unpack():
    for archive in sorted((root/'data/snapshots').glob('*.zip')):
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                destination=(root/member.filename).resolve()
                if not destination.is_relative_to(root/'data/pre_eda'):
                    raise ValueError('Unexpected archive destination')
            z.extractall(root)
    manifest=root/'data/pre_eda/metadata/package_manifest.json'
    if not manifest.exists():raise FileNotFoundError('Data snapshots are missing.')
    entries=json.loads(manifest.read_text())['files']
    for entry in entries:
        p=root/'data/pre_eda'/entry['file']
        if p.stat().st_size!=entry['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Checksum mismatch: '+entry['file'])
    print(f'All {len(entries)} snapshot files verified.')
if __name__=='__main__':unpack()
