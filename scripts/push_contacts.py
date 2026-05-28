"""Push scripts/contact_uploads/<slug>.json to worker /admin/contacts."""
import json, os, sys, urllib.request, urllib.error

WORKER_URL = os.environ.get('WORKER_URL', '').rstrip('/') or 'https://cool-darkness-dce5.tr6jz6v7wg.workers.dev'
ADMIN_KEY = os.environ.get('ADMIN_KEY', '')
SLUG = os.environ.get('SLUG', '').strip().lower()

print(f"WORKER_URL = {WORKER_URL}")
print(f"SLUG       = {SLUG}")
print(f"ADMIN_KEY  = {'set ('+str(len(ADMIN_KEY))+' chars)' if ADMIN_KEY else 'EMPTY'}")
if not ADMIN_KEY:
    print("::error::ADMIN_KEY env not set", file=sys.stderr); sys.exit(2)
if not SLUG:
    print("::error::SLUG env not set", file=sys.stderr); sys.exit(2)

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
