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
2. **International domain names:** UTS #46 mapping and Punycode, with a
   generated Unicode table (as Ordable generates its own), passing
   `toascii.json` and `IdnaTestV2.json`, and the rest of
   `urltestdata.json`.
3. **Setters and search parameters:** changing a URL's parts as the
   standard's setters do (`setters_tests.json`), and
   `application/x-www-form-urlencoded` parsing and serializing
   (`URLSearchParams`).
4. **Tours in every language,** checked in CI, as in Ordable.
5. **The site:** a disagreement explorer. Type a URL and see the parts
   this library reads, beside each language's built-in parser (Python's
   `urllib`, Java's `URI`, C#'s `Uri`, Go's `net/url`, and the
   browser's own `URL`), from results a script records ahead of time,
   with differences lit up; plus a gallery of the famous tricks
   (`http://127.1`, `http://0x7f.1`, backslashes, look-alike hosts) and
   the security holes they've caused.
6. **Refine the API and pick a name,** before 1.0.

## Starting API

Close to the URL Standard's `URL` interface, which the tests check and
people know; to refine before 1.0:

- `parseUrl(input: String, base: String? = null): Url throws Bubble`:
  the basic URL parser, failing (bubbling) where the standard fails.
- `Url`, immutable at first, with the standard's getters, each a
  `String`: `href`, `origin`, `protocol`, `username`, `password`,
  `host`, `hostname`, `port`, `pathname`, `search`, and `hash`.

Later, perhaps: a builder or setters (step 3), a way to compare URLs,
`canParse`, and parsing a base once to reuse.

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
