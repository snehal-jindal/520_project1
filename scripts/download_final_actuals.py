"""Preserve IEM final-test reports separately from all model inputs.

The default uses an existing verified snapshot without network access. A new
download requires --refresh; this preserves request details and a checksum.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/final/iem_rdu_final_actuals.csv'
MANIFEST = ROOT / 'reports/final/final_observation_manifest.json'
PARAMETERS = [('station', 'RDU'), ('network', 'NC_ASOS'),
              ('sts', '2026-09-17T04:00:00+00:00'),
              ('ets', '2026-10-01T04:00:00+00:00'),
              ('tz', 'UTC'), ('format', 'onlycomma'), ('missing', 'M'),
              ('trace', 'T'), ('direct', 'yes'), ('report_type', '3'),
              ('data', 'tmpf'), ('data', 'metar')]
URL = 'https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?' + urllib.parse.urlencode(PARAMETERS)


def verify_snapshot():
    record = json.loads(MANIFEST.read_text())
    if hashlib.sha256(OUTPUT.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Final observation snapshot checksum mismatch.')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true',
                        help='Explicitly retrieve the current mutable archive again.')
    args = parser.parse_args()
    if OUTPUT.exists() and not args.refresh:
        verify_snapshot()
        print('Verified saved final observations; no network request made.')
        return
    request = urllib.request.Request(URL, headers={'User-Agent': 'RDU-course-project-reproducibility/1.0'})
    with urllib.request.urlopen(request, timeout=90) as response:
        content = response.read()
        content_type = response.headers.get('Content-Type')
    if not content.startswith(b'station,valid,'):
        raise ValueError('Expected an IEM CSV response, not an error or HTML page.')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(content)
    record = {
        'source': 'Iowa Environmental Mesonet NC ASOS archive',
        'request_url': URL, 'request_parameters': PARAMETERS,
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'content_type': content_type, 'bytes': len(content),
        'sha256': hashlib.sha256(content).hexdigest(),
        'output_file': str(OUTPUT.relative_to(ROOT)),
        'temperature_unit': 'degF', 'report_type': '3 (routine METAR)',
        'purpose': 'Final evaluation only; never loaded by src/data_access.py or model fitting.',
        'request_end_exclusive_utc': '2026-10-01T04:00:00Z',
        'selection': 'Closest routine report to minute 51 within each UTC hour; earlier report breaks ties.',
        'provenance_limit': 'This is a new preserved retrieval verified against the committed evaluation, not the teammate\'s unretained original download. Archive observations may be revised.'
    }
    MANIFEST.write_text(json.dumps(record, indent=2) + '\n')
    print(f'Preserved {len(content)} bytes of evaluation-only observations and request metadata.')


if __name__ == '__main__':
    main()
