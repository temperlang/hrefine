"""Hrefine's benchmark in Python; see ../run.py, which runs it."""

import json
import sys
import time

# Temper's runtime first, so the library's own load is timed alone.
t0 = time.perf_counter()
import temper_core  # noqa: E402, F401

t1 = time.perf_counter()
import hrefine  # noqa: E402

load = time.perf_counter() - t1
runtime = t1 - t0
mode, folder = sys.argv[1], sys.argv[2]
seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0


def read_lines(name):
    with open(f"{folder}/{name}", encoding="utf-8") as file:
        return [line for line in file.read().split("\n") if line]


urls = [(line.split("\t") + [None])[:2] for line in read_lines("urls.txt")]
domains = read_lines("domains.txt")


def parse(pair):
    try:
        return hrefine.parse_url(pair[0], pair[1]).href_with_credentials
    except Exception:
        return "fail"


def to_ascii(domain):
    try:
        return hrefine.domain_to_ascii(domain)
    except Exception:
        return "fail"


def rate(run, items):
    """Nanoseconds per item, after warming up for `seconds`, running over
    `items` for `seconds` more."""
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        for item in items:
            run(item)
    passes, start = 0, time.perf_counter()
    while True:
        for item in items:
            run(item)
        passes += 1
        elapsed = time.perf_counter() - start
        if elapsed >= seconds:
            return elapsed * 1e9 / (passes * len(items))


if mode == "check":
    for pair in urls:
        print(parse(pair))
    for domain in domains:
        print(to_ascii(domain))
else:
    t0 = time.perf_counter()
    parse(["https://example.com/", None])
    t1 = time.perf_counter()
    to_ascii("bücher.example")
    t2 = time.perf_counter()
    print(json.dumps({
        "runtime_ms": runtime * 1e3, "load_ms": load * 1e3, "first_ascii_ms": (t1 - t0) * 1e3,
        "first_idna_ms": (t2 - t1) * 1e3, "parse_ns": rate(parse, urls),
        "idna_ns": rate(to_ascii, domains),
    }))
