# /// script
# requires-python = ">=3.11"
# ///
"""Writes src/wpt-url-tests.temper.md from web-platform-tests' URL parsing
cases (tests/wpt/urltestdata.json, vendored at the commit NOTICE names).

    uv run scripts/wpt_tests.py

Each case parses an input, against a base if it has one, and either must
fail or must give the expected value for each of the URL's getters. The
Temper test runs them all and reports every case that differs, not just
the first, so progress shows as a count.

Cases whose strings hold unpaired surrogates (a few test how JavaScript's
UTF-16 strings are cleaned up) can't be written as Temper strings, which
hold only Unicode scalar values, so they're left out, and counted.

Until international domain names work (step 2 of docs/plan.md), cases
whose host needs them are marked, and the test counts them apart: every
other case must pass. Set IDNA_DONE once they work, so all must pass.
"""

import json
import re
from pathlib import Path
from urllib.parse import unquote_to_bytes

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tests" / "wpt" / "urltestdata.json"
OUT = ROOT / "src" / "wpt-url-tests.temper.md"
# The standard's href is Hrefine's hrefWithCredentials; Hrefine's href
# leaves the credentials out, and is checked against it.
GETTER_OF = {"href": "hrefWithCredentials"}
GETTERS = ["href", "origin", "protocol", "username", "password", "host", "hostname", "port",
           "pathname", "search", "hash"]
IDNA_DONE = True
CHUNK = 100  # Cases per function of test data.
SPECIAL = {"http", "https", "ws", "wss", "ftp", "file"}


def needs_idna(case: dict) -> bool:
    """Whether the case's host is a domain that needs IDNA, beyond ASCII
    lowercasing: one with code points past ASCII, after percent-decoding,
    or with a label starting with `xn--`. Only special URLs have domains.
    Close enough to the parser's rules to sort the cases, not exact."""
    text = re.sub(r"[\t\n\r]", "", case["input"]).strip("".join(map(chr, range(0x21))))
    match = re.match(r"([A-Za-z][A-Za-z0-9+.-]*):(.*)", text, re.S)
    if match:
        scheme, rest = match.group(1).lower(), match.group(2)
    elif case.get("base"):
        scheme, rest = case["base"].split(":", 1)[0].lower(), text
    else:
        return False
    base_scheme = (case.get("base") or "").split(":", 1)[0].lower()
    if (not match or scheme == base_scheme) and not re.match(r"[/\\]{2}", rest):
        return False  # A path relative to the base, without a host.
    authority = re.match(r"[/\\]*([^/\\?#]*)", rest)
    if scheme not in SPECIAL or not authority:
        return False
    host = authority.group(1).rsplit("@", 1)[-1]
    if host.startswith("["):
        return False
    domain = unquote_to_bytes(re.sub(r":[0-9]*$", "", host))
    return (any(b >= 0x80 for b in domain)
            or re.search(rb"(^|\.)xn--", domain, re.I) is not None)


def literal(s: str) -> str:
    """A Temper string literal for `s`, escaping anything but plain ASCII."""
    out = []
    for ch in s:
        if " " <= ch <= "~" and ch not in '"\\$':
            out.append(ch)
        else:
            out.append(f"\\u{{{ord(ch):X}}}")
    return '"' + "".join(out) + '"'


def scalar_only(*strings: str) -> bool:
    return not any(0xD800 <= ord(ch) <= 0xDFFF for s in strings for ch in s)


def main() -> None:
    cases = [c for c in json.loads(SOURCE.read_text(encoding="utf-8")) if isinstance(c, dict)]
    rows, skipped, idna, idna_fail = [], 0, 0, 0
    for case in cases:
        strings = [case["input"], case.get("base") or ""] + [case.get(g, "") for g in GETTERS]
        if not scalar_only(*strings):
            skipped += 1
            continue
        fails = case.get("failure", False)
        later = not IDNA_DONE and needs_idna(case)
        idna += later
        idna_fail += later and fails
        values = [case["input"],
                  "y" if case.get("base") is not None else "n", case.get("base") or "",
                  "y" if fails else "n",
                  "y" if "origin" in case else "n",
                  "y" if later else "n"]
        values += [case.get(g, "") for g in GETTERS]
        rows.append("      cases.addAll([" + ", ".join(literal(v) for v in values) + "]);")
    stride = 6 + len(GETTERS)
    chunks = [
        f"""
    let addCases{k}(cases: ListBuilder<String>): Void {{
{chr(10).join(rows[start:start + CHUNK])}
    }}
""" for k, start in enumerate(range(0, len(rows), CHUNK))]
    getters = "\n".join(
        f'          check("{g}", url.{GETTER_OF.get(g, g)}, data[i + {6 + k}]);'
        for k, g in enumerate(GETTERS) if g != "origin")
    idna_note = (f"""
{idna} cases need international domain names (IDNA), which wait for
step 2 of the [plan](../docs/plan.md), so the test counts them apart and
needn't pass them yet: hosts that need IDNA fail to parse for now, so
the {idna - idna_fail} of them that must parse don't, and the {idna_fail} that must fail do,
but only by chance. Every other case must pass.
""" if idna else "")
    OUT.write_text(f"""# Web Platform Tests: URL Parsing

Generated by `scripts/wpt_tests.py` from web-platform-tests'
`url/resources/urltestdata.json` (see NOTICE); don't edit by hand.

{len(rows)} cases, each parsing an input, against a base if it has one,
that must either fail or give the expected value for each getter.
{skipped} cases are left out, since their strings hold unpaired
surrogates, which Temper strings can't. The test reports every case that
differs, with the first few in full, so progress shows as a count.
{idna_note}
Each case is {stride} strings: the input; `y` and the base, or `n` and
nothing; `y` if parsing must fail; `y` if the origin is given; `y` if
the case waits for IDNA; and the expected {", ".join(GETTERS[:-1])}, and {GETTERS[-1]}.

`Url.canParse` and `checkUrl` must agree with `parseUrl`, and
`checkUrl` must say why where parsing fails: a base that doesn't parse
bubbles, and otherwise the URL fails with at least one error. And each
URL's [strict form](strict.temper.md) must be RFC 3986, and mean the
same URL. The standard's href is `hrefWithCredentials`, and `href` and
`strictHref` must be the same without the credentials
(`credentialsProblem`).

    let otherWays(input: String, base: String?, url: Url?): String {{
      let baseFails = base != null && !Url.canParse(base);
      let checked: UrlCheck? = checkUrl(input, base) orelse null;
      var problem = "";
      if (Url.canParse(input, base) != (url != null)) {{
        problem = "canParse disagrees";
      }} else if (checked == null) {{
        if (!baseFails) {{
          problem = "checkUrl bubbles";
        }}
      }} else {{
        let checkedUrl = checked.url;
        if (baseFails) {{
          problem = "checkUrl doesn't bubble for a bad base";
        }} else if (checkedUrl == null) {{
          if (url != null) {{
            problem = "checkUrl fails";
          }} else if (checked.errors.isEmpty) {{
            problem = "checkUrl fails without errors";
          }}
        }} else if (url == null || checkedUrl.hrefWithCredentials != url.hrefWithCredentials) {{
          problem = "checkUrl gives ${{checkedUrl.hrefWithCredentials}}";
        }}
      }}
      if (url != null) {{
        if (problem == "") {{
          problem = strictProblem(url);
        }}
        if (problem == "") {{
          problem = credentialsProblem(url);
        }}
      }}
      problem
    }}

    test("WHATWG URL parsing: web-platform-tests' urltestdata.json") {{
      let data = urlTestData();
      let stride = {stride};
      var cases = 0;
      var wrong = 0;
      var waiting = 0;
      let examples = new ListBuilder<String>();
      var i = 0;
      while (i < data.length) {{
        cases += 1;
        let input = data[i];
        let base: String? = if (data[i + 1] == "y") {{ data[i + 2] }} else {{ null }};
        let mustFail = data[i + 3] == "y";
        let url: Url? = parseUrl(input, base) orelse null;
        var problem = "";
        if (url == null) {{
          problem = if (mustFail) {{ "" }} else {{ "failed to parse" }};
        }} else if (mustFail) {{
          problem = "parsed, but must fail, as ${{url.hrefWithCredentials}}";
        }} else {{
          let check(name: String, actual: String, expected: String): Void {{
            if (problem == "" && actual != expected) {{
              problem = "${{name}} is ${{actual}}, not ${{expected}}";
            }}
          }}
{getters}
          if (data[i + 4] == "y") {{
            check("origin", url.origin, data[i + 7]);
          }}
        }}
        if (problem == "") {{
          problem = otherWays(input, base, url);
        }}
        if (problem != "") {{
          if (data[i + 5] == "y") {{
            waiting += 1;
          }} else {{
            wrong += 1;
            if (examples.length < 10) {{
              let against = if (base == null) {{ "no base" }} else {{ "base ${{base}}" }};
              examples.add("${{input}} (${{against}}): ${{problem}}");
            }}
          }}
        }}
        i += stride;
      }}
      assert(wrong == 0) {{
        "${{wrong.toString()}} of ${{cases.toString()}} cases differ (and ${{waiting.toString()}} waiting for IDNA), such as: ${{examples.toList().join("; ") {{ e => e }}}}"
      }}
    }}

The data, built in chunks, since one function holding it all is too
big for the JVM, whose methods can't pass 64 KB of bytecode.

    let urlTestData(): List<String> {{
      let cases = new ListBuilder<String>();
{chr(10).join(f"      addCases{k}(cases);" for k in range(len(chunks)))}
      cases.toList()
    }}
{"".join(chunks)}""", encoding="utf-8")
    print(f"Wrote {len(rows)} cases ({skipped} left out, {idna} waiting for IDNA,"
          f" {idna_fail} of them failures) to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
