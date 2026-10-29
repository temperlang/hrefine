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
7. **Refine the API and pick a name,** before 1.0.

## Starting API

Close to the URL Standard's `URL` interface, which the tests check and
people know; to refine before 1.0:

- `parseUrl(input: String, base: String? = null): Url throws Bubble`:
  the basic URL parser, failing (bubbling) where the standard fails.
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
