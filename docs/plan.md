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
   *Done* (2026-10-30): the basic URL parser takes the standard's URL
   and state override, so each setter is the standard's own steps, and
   `Url` gets `withHref` through `withHash`, giving a new URL (see
   "Setters on an immutable URL" below). `UrlSearchParams` has
   JavaScript's methods, `url.searchParams` and `url.withSearchParams`
   keep it and the query in step, and its sort compares UTF-16 code
   units, as JavaScript's does. All 278 of `setters_tests.json`, the 35
   parsing and 8 sorting cases of `urlencoded-parser.any.js` and
   `urlsearchparams-sort.any.js`, and hand ports of the other
   `urlsearchparams-*.any.js` and `url-searchparams.any.js` tests pass on
   all seven backends. The tours show both. Then (2026-10-30):
   `withPortNumber`, beside `portNumber` (the only setter with an
   obvious typed twin: `withProtocol` already takes a bare scheme), and
   `UrlSearchParams.fromEntries`, from a list of `Pair`s, as `entries()`
   gives them; and `percent-encoding.json`'s UTF-8 answers, ported by hand
   (7 inputs). Its other answers are for legacy-encoded pages, whose
   queries the `URL` API never encodes, so they're out of scope.
4. **Tours in every language,** checked in CI, as in Ordable. Each also
   shows, in comments, the recommended pattern with that language's
   usual web clients and servers (such as `fetch`, `requests`,
   `HttpClient`, and `reqwest`): check with Hrefine, then hand on `href`,
   never the original string (README, "Using it safely").
   *Done* (2026-10-29), ahead of step 3, to review the API through
   them: `demos/tour/`, run in CI. What they showed is below, under
   "API review from the tours".
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
   *Strict form done* (2026-10-30): `url.strictHref`, a getter, as
   `href` and `origin` are, since it's another serialization of the
   same URL, with no options. See "The strict RFC 3986 form" below.
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
   *Started* (2026-10-30): `site/`, led by the security angle (the user,
   2026-10-29): one URL and each parser's host, then the live tester,
   13 gallery cards, the fix from the tours, the proof, and the tours.
   `site/record/record.py` records Python, Java (`URI` and `URL`), C#,
   Go, libcurl, and Node, and Hrefine's JS and Python builds, which must
   agree. A table of 47 more disagreements (2026-10-30; 48 since), by kind
   (backslashes and controls, user info, IPv4, IPv6, escaped and
   international names, schemes and ports, and paths), from WPT's cases
   and published parser-differential research, brings the recorded
   inputs from 14 to 61 (62 since); path tricks compare paths, not hosts, and IPv6
   hosts compare as addresses. Each row's full answers load only when
   tried. Given Hrefine's `href`, every recorded parser reads every
   gallery URL's host as browsers do (Java's `URL` and curl refuse
   `javascript:`). A WPT scoreboard (2026-10-30) runs `urltestdata.json`
   live through the browser's `URL` and Hrefine, with the misses listed,
   and the build runs the same module in Node, failing unless Hrefine
   passes all. The proof (2026-10-30) gives each parser the input,
   then Hrefine's `href`, then its `strictHref`, for the 51 of 62 URLs
   Hrefine accepts. Given `strictHref`, all agree but Java's `URL` and
   curl, which refuse `javascript:` (2 each), a scheme they don't
   fetch. Given `href`, Java's `URI` (49 of 51) refuses `/%zz` and `|`
   in a path, Go (49) refuses `/%zz` and escapes `|`, and C# (48)
   decodes `%2E%2E%2F` and escapes `%zz` and `|`. The build fails unless
   Node reads each strict form as it reads its `href` (the same host,
   and a path with the same bytes once decoded).
   Headless Chromium 153 passed 808 of 896, missing mostly
   `file:` and opaque-path cases, and Node 24.22.1 (Ada 4.0.0) all 896.
   An open gallery card spans its row, and narrow tables (each parser's
   answers and the more disagreements) stack each row, by container
   query, as checked in headless Chromium at phone and desktop widths.
   Dev mode (2026-10-30), as on Chromarite's and Ordable's sites: a
   switch shows badges on the opening, the tester (base, parts, and
   errors), a gallery card, the proof table, and the scoreboard, each
   with a snippet in all seven languages, marked in the tours (which
   gained a few WPT cases for the scoreboard's). The page shows no search
   parameters, so they have no badge. The build also runs the JS tour in
   Node the way the page's "Run in your browser" does.
   `site.yml` deploys from `main`, untested until it runs on GitHub. Not
   yet: PHP (no binary here), a minified bundle (Ordable uses esbuild,
   which needs approval here).
7. **Refine the API,** before 1.0. The name, Hrefine, was picked
   2026-10-29, after checking package registries and a web search for
   companies and trademarks; check USPTO and EUIPO before 1.0.

**Order** (2026-10-29): after the API review below, the next milestone
is the site (step 6), ahead of setters and search parameters (step 3),
even if the site needs refining later.

## API

Close to the URL Standard's `URL` interface, which the tests check and
people know, with JavaScript's names, revised after the tours
(2026-10-29, below); to refine before 1.0:

- `parseUrl(input: String, base: String? = null): Url throws Bubble`:
  the basic URL parser, failing (bubbling) where the standard fails, as
  `new URL()` throws. `Url.parse` gives `Url?` instead, as `URL.parse`
  does, and `Url.canParse` a `Boolean`.
- `checkUrl(input: String, base: String? = null): UrlCheck throws Bubble`:
  the URL or null, and the standard's validation errors, each a
  `ValidationError` with its `name` and `position` (in code points of
  the input as given: where the parser was, or where the host or port
  at fault starts). It bubbles only for a base that doesn't parse. The
  parser notes errors at the standard's points into a log that's null
  for `parseUrl`, so normal parsing pays only null checks in rare
  branches and one per run of code points.
- `Url`, immutable at first, with the standard's getters, each a
  `String`: `href`, `origin`, `protocol`, `username`, `password`,
  `host`, `hostname`, `port`, `pathname`, `search`, and `hash`; typed
  parts beside them: `scheme`, `portNumber: Int?`, and
  `hostKind: HostKind?`; `resolve(ref): Url throws Bubble` and
  `tryResolve(ref): Url?`, against the parsed URL without reparsing it;
  `sameOrigin(other)`, false for opaque origins; `toString()` giving
  `href`; and `==` comparing `href`s. Its constructor is private, so a
  `Url` comes only from the parser, but C#, JS, Python, Lua, and C++
  still make it public (only Java and Rust hide it).
- `HostKind`: `domain`, `ipv4`, `ipv6`, `opaque`, and `empty`, as a
  class with a private constructor and one static instance of each, so
  identity comparison works in every language.
- `parseHost(input: String): Host throws Bubble`: the host parser, as
  for a special URL, giving the `kind` and `serialized` host.
- `domainToAscii(domain: String): String throws Bubble` and
  `domainToUnicode(domain: String): String`: the standard's domain to
  ASCII and domain to Unicode (IDNA), as in Node's `url` module, for
  converting and showing a domain. Not checks; `parseHost` is.

- `strictHref`, the strict RFC 3986 form (below).
- Setters as `with` methods giving a new `Url` (step 3, below), with
  `withPortNumber(port: Int?)` beside `withPort`, and
  `UrlSearchParams`, as JavaScript's `URLSearchParams`, not tied to a
  URL: `url.searchParams` gives a new one each time, and
  `url.withSearchParams(params)` a URL with them;
  `UrlSearchParams.fromEntries(pairs)` builds one from `Pair`s, as a
  static factory, since a constructor can't be overloaded.

Later, perhaps: the source view, display formatting, and comparison
options (step 5). The canonical
`Url` stays what security decisions use; the source view is a separate,
opt-in type.

## API review from the tours

What writing the tours (`demos/tour/`, 2026-10-29) showed, and what was
done (2026-10-29, the same day). Several are Temper backend issues, not
Hrefine's own, which stay open in Temper.

- **Failures say nothing,** in every language: a bare `RuntimeError`
  (Python), `Error` (JS), `RuntimeException` (Java), `System.Exception`
  (C#), `TemperBubble` (C++), the string "Bubble" (Lua), and
  `Error(None)` (Rust, whose `Display` overflows the stack). Catching
  them catches unrelated errors too. Six tours wrote their own
  `tryParse` (Rust has `.ok()`).
  *Done:* `Url.parse` is nullable and `Url.canParse` a boolean, so the
  tours' `tryParse` helpers are gone, and `checkUrl` gives the
  standard's validation errors, with positions. The bubbles themselves
  are still bare (Temper's).
- **One parse function:** `parseUrl` and `Url.parse` did the same, but
  JavaScript's `URL.parse` returns null where Hrefine's threw.
  *Done:* JavaScript's names, exactly: `parseUrl` throws, `Url.parse`
  gives null, and `Url.canParse` is added.
- **Parsing a base once:** the base is a string, parsed again on each
  call, and a `Url` couldn't be one without going through `href`.
  *Done:* `url.resolve(ref)` and `url.tryResolve(ref)` (as Java's
  `URI.resolve` and Rust's `Url::join`), which reuse the parsed URL.
- **Typed parts:** `port` is `""` or digits; `origin` is the string
  `"null"` for opaque origins, so two `data:` URLs compare as the same
  origin; and telling an IP host from a domain meant parsing `hostname`
  again, which SSRF checks need.
  *Done:* `scheme`, `portNumber`, `hostKind`, and `sameOrigin`, beside
  the standard's strings; the tours' safety checks use them.
- **`domainToAscii` isn't a host check:** it passes `exa mple.com`,
  `0x7f.1`, and `[::1]` unchanged, as the standard's algorithm does,
  though the README offered it "for checking a domain".
  *Done:* `parseHost` checks a host and gives its kind, and the docs no
  longer offer `domainToAscii` as a check.
- **Strings and equality:** `href` works everywhere, but `str()`
  (Python), `tostring` (Lua), `$"{url}"` (C#), `Display` (Rust), and `<<`
  (C++) don't give it, and no backend compares two `Url`s by value.
  *Done in Temper:* `toString()` gives `href`, and `@operator("==")`
  compares `href`s. *Open in Temper:* backends still emit them as plain
  `toString`/`eq` methods, so only Java's string concatenation and JS
  templates use `toString`, and no language's own `==` or `equals`
  compares by value (Python, C#, Rust, C++, and Lua get no `__eq__`,
  `Equals`, `PartialEq`, `operator==`, or `__eq`).
- **Per language:** Rust needs `None::<&str>` for no base, `.as_str()`
  to compare parts, and `init` first (else a bare `unwrap` panic); Python
  takes no keywords (`base=` fails); C++ needs `global_init_init()` and
  Temper's `NullableParam` for an optional base (and now for
  `portNumber`), and its header shows every internal, with `Url`'s
  fields public and mutable; C#, JS, Python, Lua, and C++ make private
  constructors public, so a `Url` needn't come from the parser; Java and
  C# reach the functions through a `HrefineGlobal` class; and Lua gives
  `temper.null`, not `nil`, for a null result (`Url.parse`,
  `portNumber`), so the tour uses `temper.null_to_nil`. All Temper's,
  in `notes/temper-fixes.md`'s terms; still open.

## Setters on an immutable URL

Decided 2026-10-30, for step 3. JavaScript's `URL` is mutable, with a
live `searchParams`. Hrefine's `Url` stays immutable, and each setter is
a method giving a new `Url` (`withHost`, as Java's `java.time` and many
immutable types name them), because:

- **Security:** the README's pattern is to check a parsed URL and hand
  on its `href`. A URL that can change after the check, by any code
  holding it, undoes that. A new value can't.
- **Values:** `==` compares `href`s, which is safe only if they can't
  change, and immutable values are safe to share between threads in
  C++, C#, Java, and Rust without locks.
- **Every language:** methods that return a value translate plainly to
  all seven backends; property setters and a live child object tied to
  its parent don't (Lua and C++ have no property setters, and Rust's
  shared mutation needs locks).
- **Faithful still:** each `with` method runs the standard's setter
  steps, on a copy of the URL record, with partial changes kept where
  the standard keeps them, so `setters_tests.json` passes unchanged.

A builder was the other choice, but it would be a second type with the
same parts, and chaining `with` methods already builds. Search
parameters are mutable, as a list being edited, and not tied to a URL:
reading `searchParams` and handing them back with `withSearchParams` is
the standard's update steps, made explicit.

`UrlSearchParams` keeps JavaScript's method names but one: `delete` is
`remove(name, value?)` (2026-10-30), since `delete` is a C++ keyword,
and Temper renamed it `delete_` in C++ and JavaScript, while `remove`
is the usual name in Java, C#, Python, and Rust.

## The strict RFC 3986 form

Decided 2026-10-30, for step 5. `href` is ASCII, but WHATWG's encode
sets leave some characters that [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986)'s
grammar doesn't allow. RFC 3986 allows *unreserved* (letters, digits,
`-`, `.`, `_`, and `~`), *sub-delims* (`!$&'()*+,;=`), and `%` with two
hex digits everywhere, and more per part. What `href` can hold beyond
that, which `strictHref` escapes:

| Part | RFC 3986 also allows | `href` may still hold |
|---|---|---|
| User info | `:` | `%` without two hex digits |
| Domain or IPv4 host | nothing | `"`, `` ` ``, `{`, and `}` (domains) |
| Opaque host | nothing | `"`, `` ` ``, `{`, `}`, and lone `%` |
| IPv6 host | `[…]` | nothing |
| Path | `:`, `@`, and `/` | `[`, `\`, `]`, `\|`, and lone `%` |
| Opaque path | `:`, `@`, and `/` | space, `"`, `<`, `>`, `[`, `\`, `]`, `^`, `` ` ``, `{`, `\|`, `}`, and lone `%` |
| Query | `:`, `@`, `/`, and `?` | `[`, `\`, `]`, `^`, `` ` ``, `{`, `\|`, `}`, and lone `%` |
| Fragment | `:`, `@`, `/`, and `?` | `#`, `[`, `\`, `]`, `^`, `{`, `\|`, `}`, and lone `%` |

A lone `%` is one without two hex digits after it. `\` reaches a path
only in URLs that aren't special, which read it as `/`. Non-ASCII never
needs it: every encode set escapes it, and hosts are in Punycode.

So `strictHref` escapes, in each part, every ASCII character RFC 3986
doesn't allow there, and a lone `%` as `%25`. It also normalizes
escapes, as RFC 3986 section 6.2.2 says: hex digits uppercase, and
escaped unreserved characters decoded (`%7e` is `~`, and `%2E%2E%2F` is
`..%2F`, as C#'s `Uri` reads it). That can't make a dot segment, since
WHATWG already resolved escaped dots in paths; opaque paths, which
nothing resolves, keep `%2E`.

It means the same URL: parsed back with Hrefine, every part decodes to
the same bytes as the original's, and its `strictHref` is the same
again. Each case in `urltestdata.json` and `setters_tests.json` checks
this, and that the strict form is RFC 3986 by its grammar. Its `href`
may differ from the original's (`%7C` where it had `|`), as WHATWG keeps
escapes as they are. The site checks the other half: Node reads each
recorded strict form as it reads its `href`, and the recorded parsers,
Java's `URI` among them, read it as browsers do.

A getter, not a method with options, since it's one more serialization
of the same URL, as `href` and `origin` are; other forms (for display,
or without the fragment) are for step 5's formatter.

## Design notes

- **Code points, not code units:** Temper strings hold Unicode scalar
  values, walked with `StringIndex`, so every backend sees the same
  characters, whatever its own string encoding. The standard's inputs
  are code points too.
- **Files:** the parser's state machine and the setters; hosts
  (domains, IPv4 with its odd number forms, IPv6, and opaque hosts);
  percent-encoding and its encode sets; the strict RFC 3986 form; search
  parameters; and IDNA (mapping, checks, and NFC), Punycode, and IDNA's
  generated tables.
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
- **JS size matters for everyday use** (2026-10-29): at about 40 KB
  gzipped, the pure library may be too big for everyday JS, where `URL`
  is built in, though fine in other languages. So reconsider the native
  JS build below as JS's everyday choice, with pure Temper as the exact
  option, while the site still shows why one common implementation
  matters.
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
