"""Shared HTTP helper for all scrapers."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HealthTechJobsFetcher/1.0"


def fetch_json(url, timeout=15, data=None, method=None):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    else:
        body = None
    req = Request(url, headers=headers, data=body, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        return None
    except (URLError, TimeoutError):
        return None
    except Exception:
        return None
import re as _re
import html as _html_mod


def _strip_html(s):
    """Strip HTML tags + decode entities. Used by every scraper for description."""
    s = s or ""
    s = _html_mod.unescape(_html_mod.unescape(s))
    s = _re.sub(r"<[^>]+>", " ", s)
    s = _re.sub(r"\s+", " ", s).strip()
    return s[:4000]
