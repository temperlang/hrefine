# /// script
# requires-python = ">=3.11"
# ///
"""Writes src/wpt-idna-tests.temper.md from web-platform-tests' IDNA cases
(tests/wpt/toascii.json and IdnaTestV2.json, vendored at the commit NOTICE
names).

    uv run scripts/wpt_idna_tests.py

Each case is a domain and the host it must give, or none if it must
fail. As web-platform-tests' own toascii.window.js and
IdnaTestV2.window.js do, the Temper test parses `https://<domain>/x`
and checks the host, hostname, pathname, and href, or that parsing
fails. (Their setter tests wait for step 3 of docs/plan.md.)

IdnaTestV2.json is Unicode's IdnaTestV2.txt, cut down by
web-platform-tests' IdnaTestV2-parser.py for the URL Standard: it leaves
out domains that end in a number (which the URL parser reads as IPv4),
ones that UseSTD3ASCIIRules would change, and ones that fail only the
Bidi rule, whose place in the URL Standard is still open. It leaves out
nothing more, so every case left must pass. Its empty domain is left out
here too, as web-platform-tests does, since `https:///x` has a host.

The vendored tests can be for a newer Unicode than the IDNA tables
(scripts/unicode_data.py's VERSION). A case that must pass but holds a
code point the tables' IDNA mapping disallows (unassigned in that
version) is counted apart, and the test checks how many there are, so
moving the tables up shows at once.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unicode_data  # noqa: E402
from wpt_tests import literal, scalar_only  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "wpt-idna-tests.temper.md"
CHUNK = 200  # Cases per function of test data.


def disallowed_code_points() -> set[int]:
    """The code points the pinned IDNA mapping table disallows."""
    out = set()
    path = unicode_data.ensure() / "IdnaMappingTable.txt"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(";")]
        if parts[1] == "disallowed":
            first, _, last = parts[0].partition("..")
            out.update(range(int(first, 16), int(last or first, 16) + 1))
    return out


def unicode_form(domain: str) -> str:
    """The domain with its `xn--` labels decoded, as far as Python can."""
    labels = []
    for label in domain.split("."):
        if label.startswith("xn--"):
            try:
                label = label[4:].encode("ascii").decode("punycode")
            except UnicodeError:
                pass
        labels.append(label)
    return ".".join(labels)


def encode_host_ending(domain: str) -> str:
    """As IdnaTestV2.window.js does, so the whole domain is the host."""
    return "".join("%{:02X}".format(ord(c)) if c in ":/?#\\" else c for c in domain)


def main() -> None:
    disallowed = disallowed_code_points()
    files = []
    skipped = 0
    for name, encode in [("toascii.json", False), ("IdnaTestV2.json", True)]:
        cases = [c for c in json.loads((ROOT / "tests" / "wpt" / name).read_text(encoding="utf-8"))
                 if isinstance(c, dict) and c["input"] != ""]
        rows, newer = [], 0
        for case in cases:
            if not scalar_only(case["input"]):
                skipped += 1
                continue
            domain = encode_host_ending(case["input"]) if encode else case["input"]
            output = case["output"]
            later = output is not None and any(ord(c) in disallowed for c in case["input"])
            newer += later
            # Cases without errors, which IdnaTestV2.json marks by having
            # no comment, must also round-trip through domain to Unicode,
            # if the tables know all their code points.
            clean = (encode and output is not None and "comment" not in case
                     and not any(ord(c) in disallowed for c in unicode_form(output)))
            flag = "y" if later else "r" if clean else "n"
            rows.append(f"      cases.addAll([{literal(domain)}, "
                        f"{literal('n' if output is None else 'y')}, {literal(output or '')}, "
                        f"{literal(flag)}]);")
        files.append((name, rows, newer))

    def data_functions(prefix: str, rows: list[str]) -> tuple[str, str]:
        chunks = [rows[i:i + CHUNK] for i in range(0, len(rows), CHUNK)]
        calls = "\n".join(f"      {prefix}{k}(cases);" for k in range(len(chunks)))
        bodies = "".join(f"""
    let {prefix}{k}(cases: ListBuilder<String>): Void {{
{chr(10).join(chunk)}
    }}
""" for k, chunk in enumerate(chunks))
        return calls, bodies

    (_, ascii_rows, ascii_newer), (_, idna_rows, idna_newer) = files

    def test_body(data: str, newer: int) -> str:
        """The test's body, the same for each file. It's written out in
        each test, not shared as a function, since Temper (as of
        2026-10-29) can fold a call with constant arguments at compile
        time, and gets `orelse` wrong there when the code it runs has a
        loop with `break`, `continue`, or `return` in it."""
        return f"""      let data = {data};
      var cases = 0;
      var wrong = 0;
      var waiting = 0;
      let examples = new ListBuilder<String>();
      for (var i = 0; i < data.length; i += 4) {{
        cases += 1;
        let domain = data[i];
        let expected = data[i + 2];
        let url: Url? = parseUrl("https://${{domain}}/x") orelse null;
        var problem = "";
        if (url == null) {{
          problem = if (data[i + 1] == "y") {{ "failed to parse" }} else {{ "" }};
        }} else if (data[i + 1] == "n") {{
          problem = "parsed, but must fail, as ${{url.host}}";
        }} else if (
          url.host != expected || url.hostname != expected || url.pathname != "/x" ||
          url.href != "https://${{expected}}/x"
        ) {{
          problem = "host is ${{url.host}}, not ${{expected}}";
        }} else if (data[i + 3] == "r") {{
          let unicode = domainToUnicode(expected);
          let back = domainToAscii(unicode) orelse "(fails)";
          if (back != expected) {{
            problem = "domain to Unicode gives ${{unicode}}, which goes back to ${{back}}";
          }}
        }}
        if (data[i + 3] == "y") {{
          if (problem != "") {{
            waiting += 1;
            problem = "";
          }} else {{
            problem = "passes, though it needs a newer Unicode";
          }}
        }}
        if (problem != "") {{
          wrong += 1;
          if (examples.length < 10) {{
            examples.add("${{domain}}: ${{problem}}");
          }}
        }}
      }}
      assert(wrong == 0 && waiting == {newer}) {{
        "${{wrong.toString()}} of ${{cases.toString()}} cases differ (and ${{waiting.toString()}} of {newer} need a newer Unicode), such as: ${{examples.toList().join("; ") {{ e => e }}}}"
      }}"""
    assert ascii_newer == 0
    ascii_calls, ascii_bodies = data_functions("addToAscii", ascii_rows)
    idna_calls, idna_bodies = data_functions("addIdnaTestV2", idna_rows)
    OUT.write_text(f"""# Web Platform Tests: International Domain Names

Generated by `scripts/wpt_idna_tests.py` from web-platform-tests'
`url/resources/toascii.json` and `IdnaTestV2.json` (see NOTICE); don't
edit by hand.

Each case is a domain and the host it must give, or none if it must
fail, checked as web-platform-tests does: by parsing `https://`, the
domain, and `/x`, and checking the host, hostname, pathname, and href.
`IdnaTestV2.json` is Unicode's own IDNA tests, minus those the URL
Standard reads differently (domains ending in a number, which are IPv4)
and those still open (UseSTD3ASCIIRules, and domains that fail only the
Bidi rule); see the script for more. {skipped} cases of `IdnaTestV2.json` are left
out, since they hold unpaired surrogates, which Temper strings can't.

The IDNA tables are for Unicode {unicode_data.VERSION}. {idna_newer} cases of `IdnaTestV2.json`
must pass but hold code points that version hasn't assigned, so they're
for a newer one: the test counts them apart, and checks how many fail.

Each case is four strings: the domain; `y` if it must parse, or `n`;
the host it must give; and `y` if it needs a newer Unicode, `r` if it
has no errors at all, so domain to Unicode and back must give the host
again, or `n`.

    test("IDNA: web-platform-tests' toascii.json") {{
{test_body("toAsciiData()", 0)}
    }}

    test("IDNA: web-platform-tests' IdnaTestV2.json") {{
{test_body("idnaTestV2Data()", idna_newer)}
    }}

The data, built in chunks, since one function holding it all is too
big for the JVM, whose methods can't pass 64 KB of bytecode.

    let toAsciiData(): List<String> {{
      let cases = new ListBuilder<String>();
{ascii_calls}
      cases.toList()
    }}

    let idnaTestV2Data(): List<String> {{
      let cases = new ListBuilder<String>();
{idna_calls}
      cases.toList()
    }}
{ascii_bodies}{idna_bodies}""", encoding="utf-8")
    print(f"Wrote {len(ascii_rows)} toascii.json cases and {len(idna_rows)} IdnaTestV2.json cases"
          f" ({idna_newer} needing a newer Unicode) to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
