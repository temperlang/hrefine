# Plan

A URL library for every language Temper supports, following the WHATWG
URL Standard exactly, built like Chromarite and Ordable: one Temper
source, tests from an outside authority, a tour in each language, and a
site that makes the point.

## Steps

1. **Parse and serialize,** passing web-platform-tests'
   `urltestdata.json` on every backend, apart from international domain
   names (hosts beyond ASCII), which wait for step 2. The URL Standard's
   basic URL parser is a state machine, written as the standard writes
   it, so each part can be checked against the text.
   *Done* (2026-10-29): all of `urltestdata.json` passes on all seven
   backends but the 40 cases whose hosts need IDNA, which the test
   counts apart (21 must parse and don't yet; 19 must fail and do, by
   chance). Hosts beyond ASCII, and `xn--` labels, fail to parse for
   now.
2. **International domain names:** UTS #46 mapping and Punycode, with
   generated Unicode tables (generated the way Ordable generates its own),
   passing `toascii.json` and `IdnaTestV2.json`, and the rest of
   `urltestdata.json`. The URL Standard sets UTS #46's options, which
   call for four kinds of data:
   - **The IDNA mapping table:** each code point's status (valid,
     mapped, deviation, or disallowed) and its mapping.
   - **NFC normalization:** decompositions, combining classes, and
     composition.
   - **Bidi classes,** for the Bidi rule (RFC 5893).
   - **Joining types and viramas,** for the ContextJ rules on zero-width
     joiners (RFC 5892).

   The tables are this library's own, not Ordable's. They must match the
   Unicode version of the vendored IDNA tests, which is 17.0 (they treat
   CJK Extension J, new in 17.0, as valid), not Ordable's 15.0, and
   Ordable's Unicode code stays internal to it. If Temper later builds in
   Unicode data, both libraries could use that instead. Python's
   `unicodedata` is older (16.0 as of Python 3.14), so all the data comes
   from Unicode 17.0's own files, vendored in `data/unicode-17.0.0/`:
   `IdnaMappingTable.txt`, `UnicodeData.txt`,
   `DerivedNormalizationProps.txt`, `DerivedBidiClass.txt`, and
   `DerivedJoiningType.txt`.
3. **Setters and search parameters:** changing a URL's parts as the
   standard's setters do (`setters_tests.json`), and
   `application/x-www-form-urlencoded` parsing and serializing
   (`URLSearchParams`).
4. **Tours in every language,** checked in CI, as in Ordable.
5. **Formatting and lossless edits** (designed now, built after the
   above): a formatter in any case, and maybe both a normalizing and a
   preserving form; a source view that keeps the original input with each
   component's span, so a tool can change one part (a query, a host, a
   path segment) and leave the rest byte for byte as written, for config
   files, docs, and lint fixes (the same idea as a lossless Markdown
   library, and maybe shared with one); display formatting (a Unicode
   host by IDNA's ToUnicode, with browsers' anti-spoofing rules for mixed
   scripts and look-alikes, and options such as dropping the fragment);
   and comparison ("the same URL?", with options such as ignoring the
   fragment). Security decisions stay on the standard's canonical form,
   never on the source view. The standard strips leading and trailing
   control characters and removes tabs and newlines before parsing, so
   spans must map back through that.
6. **The site:** a disagreement explorer. Type a URL and see the parts
   this library reads, beside each language's built-in parser (Python's
   `urllib`, Java's `URI`, C#'s `Uri`, Go's `net/url`, and the
   browser's own `URL`), from results a script records ahead of time,
   with differences lit up; plus a gallery of the famous tricks
   (`http://127.1`, `http://0x7f.1`, backslashes, look-alike hosts) and
   the security holes they've caused.
7. **Refine the API,** before 1.0. The name, Hrefine, was picked
   2026-10-29, after checking package registries and a web search for
   companies and trademarks; check USPTO and EUIPO before 1.0.

## Starting API

Close to the URL Standard's `URL` interface, which the tests check and
people know; to refine before 1.0:

- `parseUrl(input: String, base: String? = null): Url throws Bubble`:
  the basic URL parser, failing (bubbling) where the standard fails.
  `Url.parse` is the same, as in JavaScript; it's there because only
  the class can call its private constructor.
- `Url`, immutable at first, with the standard's getters, each a
  `String`: `href`, `origin`, `protocol`, `username`, `password`,
  `host`, `hostname`, `port`, `pathname`, `search`, and `hash`.

Later, perhaps: a builder or setters (step 3), the source view,
display formatting, and comparison (step 5), `canParse`, and parsing a
base once to reuse. The canonical `Url` stays what security decisions
use; the source view is a separate, opt-in type.

## Design notes

- **Code points, not code units:** Temper strings hold Unicode scalar
  values, walked with `StringIndex`, so every backend sees the same
  characters, whatever its own string encoding. The standard's inputs
  are code points too.
- **Files:** the parser's state machine; hosts (domains, IPv4 with its
  odd number forms, IPv6, and opaque hosts); percent-encoding and its
  encode sets; and, later, IDNA and its tables, and search parameters.
- **Speed:** check that parsing is fast enough in every language (a
  benchmark like Ordable's), but correctness first.
- **Test files are data:** `scripts/wpt_tests.py` writes the Temper test
  from the vendored JSON; regenerate it after updating the vendored files
  (and NOTICE's commit).
