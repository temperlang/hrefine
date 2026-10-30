"""Reads URLs with Hrefine's Python build, for site/record/record.py.

Each input line is base64 of the input, a space, and base64 of the base (or
"-" for none). Prints one JSON line per input line. Run in the tour's
environment, after temper build -b py:

    uv run -q --project demos/tour/py python site/record/probe_hrefine.py
"""

import base64
import json
import sys

from hrefine import check_url


def decode(text):
    return base64.b64decode(text).decode("utf-8")


def hrefine(text, base):
    check = check_url(text, base)
    errors = [error.to_string() for error in check.errors]
    url = check.url
    if url is None:
        return {"ok": False, "error": errors[-1] if errors else "failure", "errors": errors}
    kind = url.host_kind
    return {
        "ok": True,
        "scheme": url.scheme,
        "host": None if kind is None else url.hostname,
        "path": url.pathname,
        # The exact URL, credentials and all, as probe.mjs gives.
        "href": url.href_with_credentials,
        "strictHref": url.strict_href_with_credentials,
        "hostKind": None if kind is None else kind.to_string(),
        "errors": errors,
    }


for line in sys.stdin:
    text, base = line.split()
    result = hrefine(decode(text), None if base == "-" else decode(base))
    print(json.dumps({"hrefine-py": result}, ensure_ascii=False))
