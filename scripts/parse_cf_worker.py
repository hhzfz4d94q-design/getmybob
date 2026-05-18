"""Parse the multipart body that Cloudflare returns for a Worker script.

Usage:
    python3 scripts/parse_cf_worker.py <multipart_raw_path> <out_js_path>
"""
import re
import sys

if len(sys.argv) != 3:
    print("usage: parse_cf_worker.py <in_multipart> <out_js>", file=sys.stderr)
    sys.exit(2)

with open(sys.argv[1], "rb") as f:
    body = f.read()

# Find the multipart boundary
m = re.search(rb'--([A-Za-z0-9\-]+)\r\n', body)
if not m:
    print("Could not find multipart boundary; raw response saved.", file=sys.stderr)
    sys.stderr.buffer.write(body[:500] + b"\n")
    sys.exit(1)
boundary = m.group(1)
parts = body.split(b"--" + boundary)

# Find the part that contains the JS module — heuristic: the largest part that
# looks like JS (has `export default` or `async fetch` or is just big).
best = None
for p in parts:
    if b"\r\n\r\n" not in p:
        continue
    head, _, payload = p.partition(b"\r\n\r\n")
    if b"export default" in payload or b"async fetch" in payload or len(payload) > 2000:
        if best is None or len(payload) > len(best):
            best = payload

if best is None:
    print("Could not isolate the worker.js payload.", file=sys.stderr)
    sys.exit(1)

# Strip trailing CRLF and any final boundary marker
best = best.rstrip(b"-").rstrip(b"\r\n").rstrip(b"\r\n--")

with open(sys.argv[2], "wb") as f:
    f.write(best)

print(f"Wrote {sys.argv[2]} ({len(best)} bytes)")
