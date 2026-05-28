"""Push scripts/contact_uploads/<slug>.json to worker /admin/contacts."""
import json, os, sys, urllib.request, urllib.error

WORKER_URL = os.environ['WORKER_URL'].rstrip('/')
ADMIN_KEY = os.environ['ADMIN_KEY']
SLUG = os.environ['SLUG'].strip().lower()

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'scripts', 'contact_uploads', f'{SLUG}.json')
if not os.path.exists(path):
    print(f"::error::missing {path}", file=sys.stderr); sys.exit(1)

with open(path) as f:
    contacts = json.load(f)
print(f"Loaded {len(contacts)} contacts for slug={SLUG}")

payload = json.dumps({
    'slug': SLUG,
    'contacts': contacts,
    'filename': 'Connections.csv',
    'source': 'admin-csv-upload',
}).encode('utf-8')

req = urllib.request.Request(
    f'{WORKER_URL}/admin/contacts',
    data=payload,
    method='POST',
    headers={
        'X-Admin-Key': ADMIN_KEY,
        'Content-Type': 'application/json',
        'User-Agent': 'getmemyjob-push-contacts/1.0',
    },
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode('utf-8', errors='replace')
        print(f"HTTP {r.status}")
        print(body)
        if r.status != 200:
            sys.exit(2)
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}")
    print(e.read().decode('utf-8', errors='replace'))
    sys.exit(2)
except Exception as e:
    print(f"::error::{type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(2)
