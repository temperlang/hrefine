# /// script
# requires-python = ">=3.11"
# ///
"""Records how other URL parsers read the site's trick gallery.

    temper build -b js -b py
    uv run site/record/record.py

Reads the inputs in `site/gallery.json` and asks each parser installed on
this machine what URL, scheme, and host it makes of each one, writing
`site/recorded.json`, which the site shows beside Hrefine's live answers.
Parsers missing here are left out, and said to be. Each parser's version
and the date are recorded too, since answers change between versions.

- Python's `urllib.parse` (`urlsplit`, and `urljoin` for a base), in the
  Python running this script;
- libcurl's URL API (`curl_url`), through ctypes, if libcurl is installed;
- Java's `java.net.URI` and `java.net.URL` (`Probe.java`), if `java` is;
- .NET's `System.Uri` (`csharp/`), if `dotnet` is;
- Go's `net/url` (`probe.go`), if `go` is;
- Node's `URL`, standing in for browsers, which follow the same standard
  (`probe.mjs`), and Hrefine's JavaScript build beside it;
- Hrefine's Python build (`probe_hrefine.py`), to check two of Hrefine's
  languages agree here too (all seven pass the same tests in CI).

Then it gives every parser Hrefine's `href` for each input, in place of the
input, and then its `strictHref` (the strict RFC 3986 form), to show the
fix: the parsers then read the host as browsers do.

Each probe reads lines of base64 input and base (or `-`) on stdin, so tabs
and newlines in inputs survive, and prints a JSON line for each.
"""

import base64
import ctypes
import ctypes.util
import datetime
import json
import platform
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = ROOT / "site" / "record"
GALLERY = ROOT / "site" / "gallery.json"
OUT = ROOT / "site" / "recorded.json"

# Each parser the page can show, in order: id, name, and what's called.
PARSERS = [
    ("browser", "Browsers (Node's URL)", "new URL(input, base)"),
    ("python", "Python urllib", "urllib.parse.urlsplit"),
    ("java-uri", "Java URI", "java.net.URI"),
    ("java-url", "Java URL", "java.net.URL"),
    ("csharp", "C# Uri", "System.Uri"),
    ("go", "Go net/url", "url.Parse"),
    ("curl", "curl", "libcurl curl_url"),
]


def b64(text):
    return "-" if text is None else base64.b64encode(text.encode("utf-8")).decode("ascii")


def run_probe(args, inputs, cwd=HERE):
    """Runs a probe on every input, returning one dict per input."""
    lines = "".join(f"{b64(i['input'])} {b64(i.get('base'))}\n" for i in inputs)
    result = subprocess.run(args, cwd=cwd, input=lines, capture_output=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))} failed:\n{result.stderr}")
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    if len(rows) != len(inputs):
        raise RuntimeError(f"{args[0]} gave {len(rows)} results for {len(inputs)} inputs:\n{result.stdout}")
    return rows


def version(args, cwd=HERE):
    return subprocess.run(args, cwd=cwd, capture_output=True, encoding="utf-8", check=True).stdout.strip()


def python_urllib(text, base):
    try:
        parts = urllib.parse.urlsplit(urllib.parse.urljoin(base, text) if base else text)
        # Python gives None for no host, and "" for an empty one.
        host = parts.hostname
        if host is None and parts.netloc != "":
            host = ""
        return {"ok": True, "scheme": parts.scheme, "host": host, "path": parts.path, "href": parts.geturl()}
    except ValueError as error:
        return {"ok": False, "error": f"ValueError: {error}"}


class Curl:
    """libcurl's URL API, as curl's own tools parse URLs."""

    URL, SCHEME, HOST, PATH = 0, 1, 5, 7
    # Parse schemes curl doesn't support, such as javascript:, too.
    NON_SUPPORT_SCHEME = 1 << 3

    def __init__(self, path):
        lib = ctypes.CDLL(path)
        lib.curl_version.restype = ctypes.c_char_p
        lib.curl_url.restype = ctypes.c_void_p
        lib.curl_url_cleanup.argtypes = [ctypes.c_void_p]
        lib.curl_url_set.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        lib.curl_url_get.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p), ctypes.c_uint]
        lib.curl_url_strerror.restype = ctypes.c_char_p
        lib.curl_free.argtypes = [ctypes.c_void_p]
        self.lib = lib
        self.version = lib.curl_version().decode().split()[0].replace("/", " ")

    def get(self, handle, part):
        out = ctypes.c_char_p()
        code = self.lib.curl_url_get(handle, part, ctypes.byref(out), 0)
        if code != 0:
            return None
        value = out.value.decode("utf-8", "replace")
        self.lib.curl_free(ctypes.cast(out, ctypes.c_void_p))
        return value

    def parse(self, text, base):
        handle = self.lib.curl_url()
        try:
            for value in [base, text] if base else [text]:
                # On a handle that holds a URL, curl resolves a relative one
                # against it, as for a redirect.
                code = self.lib.curl_url_set(handle, self.URL, value.encode("utf-8"), self.NON_SUPPORT_SCHEME)
                if code != 0:
                    return {"ok": False, "error": self.lib.curl_url_strerror(code).decode()}
            return {
                "ok": True,
                "scheme": self.get(handle, self.SCHEME),
                "host": self.get(handle, self.HOST),
                "path": self.get(handle, self.PATH),
                "href": self.get(handle, self.URL),
            }
        finally:
            self.lib.curl_url_cleanup(handle)


def record(inputs):
    """Every installed parser's answers for each input, and their versions."""
    results = [{} for _ in inputs]
    versions = {}
    missing = []

    def merge(rows):
        for row, out in zip(rows, results):
            out.update(row)

    versions["python"] = f"Python {platform.python_version()}"
    merge([{"python": python_urllib(i["input"], i.get("base"))} for i in inputs])

    curl_path = ctypes.util.find_library("curl")
    if curl_path:
        curl = Curl(curl_path)
        versions["curl"] = curl.version
        merge([{"curl": curl.parse(i["input"], i.get("base"))} for i in inputs])
    else:
        missing.append("curl")

    # One toolchain at a time, each run to the end before the next.
    if shutil.which("java"):
        versions["java-uri"] = versions["java-url"] = version(["java", "Probe.java", "--version"])
        merge(run_probe(["java", "Probe.java"], inputs))
    else:
        missing += ["java-uri", "java-url"]

    if shutil.which("dotnet"):
        # No build servers, which would stay running after.
        quiet = ["-v", "q", "--nologo", "-nodeReuse:false", "-p:UseSharedCompilation=false"]
        subprocess.run(["dotnet", "build", *quiet], cwd=HERE / "csharp", check=True, capture_output=True)
        versions["csharp"] = version(["dotnet", "run", "--no-build", "--", "--version"], HERE / "csharp")
        merge(run_probe(["dotnet", "run", "--no-build"], inputs, HERE / "csharp"))
    else:
        missing.append("csharp")

    if shutil.which("go"):
        versions["go"] = version(["go", "run", "probe.go", "--version"])
        merge(run_probe(["go", "run", "probe.go"], inputs))
    else:
        missing.append("go")

    node = version(["node", "probe.mjs", "--version"])
    versions["browser"] = node
    versions["hrefine"] = f"Hrefine's JavaScript build, in {node}"
    merge([{"browser": r["node"], "hrefine": r["hrefine"]} for r in run_probe(["node", "probe.mjs"], inputs)])

    # Hrefine in Python too, which must agree with Hrefine in JavaScript.
    if (ROOT / "temper.out" / "py" / "hrefine").exists():
        project = ROOT / "demos" / "tour" / "py"
        args = ["uv", "run", "-q", "--project", project, "python", HERE / "probe_hrefine.py"]
        for row, out in zip(run_probe(args, inputs, ROOT), results):
            if row["hrefine-py"] != out["hrefine"]:
                raise SystemExit(f"Hrefine's Python and JS builds disagree:\n{row['hrefine-py']}\n{out['hrefine']}")
        versions["hrefine"] += ", and its Python build, which agrees"
    return results, versions, missing


def main():
    if not (ROOT / "temper.out" / "js" / "hrefine").exists():
        raise SystemExit("Build Hrefine's JS first: temper build -b js")
    gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
    corpus = [item for group in gallery["corpus"] for item in group["items"]]
    inputs = [{"input": i["input"], "base": i.get("base")} for i in gallery["hero"] + gallery["cards"] + corpus]
    results, versions, missing = record(inputs)

    # The fix, checked: each parser given Hrefine's href instead of the
    # input, and then its strict RFC 3986 form. Inputs Hrefine rejects have
    # neither, and are left out.
    hrefs = [{"input": r["hrefine"]["href"]} for r in results if r["hrefine"]["ok"]]
    href_results, _, _ = record(hrefs)
    stricts = [{"input": r["hrefine"]["strictHref"]} for r in results if r["hrefine"]["ok"]]
    strict_results, _, _ = record(stricts)

    recorded = {
        "date": datetime.date.today().isoformat(),
        "platform": f"{platform.system()} {platform.machine()}",
        "parsers": [
            {"id": id, "name": name, "calls": calls, "version": versions[id]}
            for id, name, calls in PARSERS
            if id in versions
        ],
        "missing": missing,
        "hrefine": versions["hrefine"],
        "results": [{**i, "answers": r} for i, r in zip(inputs, results)],
        "hrefs": [{**i, "answers": r} for i, r in zip(hrefs, href_results)],
        "stricts": [{**i, "answers": r} for i, r in zip(stricts, strict_results)],
    }
    OUT.write_text(json.dumps(recorded, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for id, name, _ in PARSERS:
        print(f"{name}: {versions.get(id, 'not installed')}")
    print(f"Wrote {OUT.relative_to(ROOT)}, {len(inputs)} inputs, and {len(hrefs)} hrefs and strict forms")


if __name__ == "__main__":
    sys.exit(main())
