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

   The tables are this library's own, not Ordable's (which is on 15.0,
   and keeps its Unicode code internal). If Temper later builds in
   Unicode data, both libraries could use that instead. Python's
   `unicodedata` is older (16.0 as of Python 3.14), so all the data comes
   from Unicode's own files, which `scripts/unicode_data.py` downloads
   into `data/unicode-18.0.0/` (not in git) and checks against pinned
   hashes: `IdnaMappingTable.txt`, `UnicodeData.txt`,
   `DerivedNormalizationProps.txt`, `DerivedBidiClass.txt`, and
   `DerivedJoiningType.txt`.
   *Done* (2026-10-29): all three test files pass on all seven
   backends, with Unicode 18.0, which the vendored IDNA tests are for
   (web-platform-tests moved them on 2026-10-04).
   `scripts/idna_tables.py` writes the tables
   (`src/idna-tables.temper.md`, 53 KB, by block of code points, read
   in place: see "Speed and size" below); `src/idna.temper.md` has
   domain to ASCII, domain to Unicode, and NFC, and
   `src/punycode.temper.md` Punycode. For a new Unicode version, raise
   `unicode_data.py`'s VERSION, `--repin` (unicode.org isn't reachable
   from the dev container), regenerate, and update NOTICE.
3. **Setters and search parameters:** changing a URL's parts as the
   standard's setters do (`setters_tests.json`), and
   `application/x-www-form-urlencoded` parsing and serializing
   (`URLSearchParams`).
4. **Tours in every language,** checked in CI, as in Ordable. Each also
   shows, in comments, the recommended pattern with that language's
   usual web clients and servers (such as `fetch`, `requests`,
   `HttpClient`, and `reqwest`): check with Hrefine, then hand on `href`,
   never the original string (README, "Using it safely").
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
   spans must map back through that. Also a **strict RFC 3986 form:**
   `href` with the few characters WHATWG leaves unencoded but strict
   parsers reject or read differently (`|`, `^`, `{`, `}`, and the like)
   percent-encoded, for clients such as Java's `URI`, so prenormalized
   URLs are read alike there too.
6. **The site:** a disagreement explorer. Type a URL and see the parts
   this library reads, beside each language's built-in parser (Python's
   `urllib`, Java's `URI`, C#'s `Uri`, Go's `net/url`, and the
   browser's own `URL`), from results a script records ahead of time,
   with differences lit up; plus a gallery of the famous tricks
   (`http://127.1`, `http://0x7f.1`, backslashes, look-alike hosts) and
   the security holes they've caused. And the fix, shown: tricky inputs
   fed to each language's parser disagree, while Hrefine's `href` (or its
   strict form) fed to the same parsers agrees. Visit counts by
   cookieless GoatCounter, site code `hrefine`, as on Chromarite's and
   Ordable's sites.
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
- `domainToAscii(domain: String): String throws Bubble` and
  `domainToUnicode(domain: String): String`: the standard's domain to
  ASCII and domain to Unicode (IDNA), as in Node's `url` module, for
  checking a domain and for showing one.

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
  encode sets; IDNA (mapping, checks, and NFC), Punycode, and IDNA's
  generated tables; and, later, search parameters.
- **Speed and size:** as small and fast as we can make them, in every
  language, without giving up exactness, measured with `bench/` (see the
  README). As of 2026-10-29, against the version before, timed in turns:
  - The IDNA tables are read in place, by block of code points, so
    nothing is decoded or cached: the first domain beyond ASCII went
    from 46 to 0.13 ms in Python, 28 to 0.1 ms in Lua, 18 to 0.45 ms in
    Java, and 9 to 0.9 ms in JavaScript. With no module-level `var`,
    there's no state for threads to race on (it was a data race in
    C++). Steady-state domain to ASCII got 10–30% faster in most
    languages. The cost: the library is 15–45 KB bigger (3–4 KB
    gzipped), and loading builds the tables' lists, 0.15 ms in C++ and
    about 4 ms in C# (JIT of its static constructor).
  - Parsing takes runs of code points at once, and uses few builders:
    44% faster in Python, 43% in Lua, about 30% in JavaScript, C++,
    and Rust, 25% in C#. Java is too noisy here to call.
  - Hot helpers avoid early returns, which Temper's Python backend
    turns into raised exceptions.
  - Tried and dropped: sub-blocks of 32 code points (faster in Python
    and Lua, but 9 KB bigger and slower to load in C#), storing runs'
    ends rather than lengths (slower), a module for the tables (Java
    and C# would load it lazily, but every backend makes its exports
    public), and `indexOf` for finding tabs (culture-sensitive in C#).
- **Native JS, maybe later:** once Temper's connected functions can fall
  back to Temper bodies, an opt-in JS build could use the runtime's own
  `URL` (in browsers, Node, Deno, and Bun) for parsing and IDNA, dropping
  the tables. Pure Temper stays the default, since engines differ on WPT's
  edge cases, which would break "the same in every language"; the native
  build would run WPT in CI and say exactly where it differs. It keeps
  the pure extras (typed parts, spans, reasons, and display).
- **Test files are data:** `scripts/wpt_tests.py` writes the Temper test
  from the vendored JSON; regenerate it after updating the vendored files
  (and NOTICE's commit).
