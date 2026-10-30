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
   *Display, comparison, and spans done* (2026-10-30): `UrlDisplay`
   and `domainToDisplay`, `url.sameDocument`, and `parseUrlSource`
   with `UrlSource` and `SourceSpan`, and validation errors now carry a
   `length` beside their `position`. Display shows only Latin labels in
   Unicode for now, until Unicode's Script and identifier data are
   pinned. Lossless editing is designed, not built: it waits on htmlmd.
   See "Display formatting", "Comparison", "Source spans", and
   "Lossless editing" below.
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

8. **Strict mode and policies,** for the security pitch: check with
   Hrefine, then hand on `href`. *Done* (2026-10-30): strict mode on
   `UrlCheck`, and `UrlPolicy` for the usual checks, in one call. See
   "Strict mode" and "Policies" below. The tours gained a section, and
   the site's fix a step with a dev-mode badge.

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
- `UrlCheck.strictErrors` and `strictUrl`, for strict mode, and
  `UrlPolicy`, `PolicyCheck`, and `PolicyRule` (below).
- Setters as `with` methods giving a new `Url` (step 3, below), with
  `withPortNumber(port: Int?)` beside `withPort`, and
  `UrlSearchParams`, as JavaScript's `URLSearchParams`, not tied to a
  URL: `url.searchParams` gives a new one each time, and
  `url.withSearchParams(params)` a URL with them;
  `UrlSearchParams.fromEntries(pairs)` builds one from `Pair`s, as a
  static factory, since a constructor can't be overloaded.

- `UrlDisplay`, `domainToDisplay`, `url.sameDocument`,
  `parseUrlSource`, `UrlSource`, and `SourceSpan` (step 5, below), and
  `ValidationError.length`. The canonical `Url` stays what security
  decisions use; the source view is a separate, opt-in type.

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

## Strict mode

Decided 2026-10-30. The standard accepts much that it calls a
[validation error](https://url.spec.whatwg.org/#validation-error), and
cautious parsers refuse, so strict mode refuses it too, while the
standard parse stays the default. It's on `UrlCheck`, which already
has the errors: `strictErrors` are those strict mode counts, and
`strictUrl` is the URL only if there are none; a policy's
`withStrict(true)` does the same in one call. Not a separate parse
function, which would double `parseUrl`, `Url.parse`, and
`Url.canParse`.

Every error counts but one kind, which is too benign:
`invalid-URL-unit` for a code point that a path, query, fragment, or
opaque host keeps or percent-encodes, such as a space, `"`, `<`, `|`,
`[`, `{`, or a `%` without hex digits. They're common in real links
(`?a[]=1`, `?q=a b`), `href` holds them unambiguously, and `strictHref`
escapes the rest, so they can't change where a URL leads.
`invalid-URL-unit` for what the standard strips (leading and trailing C0
controls and spaces, tabs, and newlines) does count. So these count:

- `invalid-URL-unit`, for stripped code points only
- `special-scheme-missing-following-solidus` (`https:example.com`,
  `https:\\host`)
- `invalid-reverse-solidus` (backslashes in special URLs)
- `invalid-credentials` (any `@` before the host)
- `missing-scheme-non-relative-URL`, `host-missing`, `port-invalid`,
  `port-out-of-range`, and the other failures, though a failed parse
  fails anyway
- `IPv4-empty-part` (`1.2.3.4.`), `IPv4-non-decimal-part` (hex and
  octal), and `IPv4-out-of-range-part` (`2130706433`)
- `file-invalid-Windows-drive-letter` and
  `file-invalid-Windows-drive-letter-host`
- `domain-to-ASCII`, `domain-invalid-code-point`,
  `host-invalid-code-point`, and the IPv6 errors, which all fail

The standard notes nothing for some forms that cautious parsers refuse
or read otherwise, and that filters miss, so Hrefine adds two of its
own, only to `strictErrors`, never to `errors`:

- `IPv4-non-canonical`: an IPv4 address written any way but as its four
  decimal numbers, as `127.1`, `127.0.1`, `0x7f.1`, `2130706433`,
  `%31%32%37.1`, or full-width digits. The standard notes no error at all
  for `127.1`.
- `domain-percent-encoded`: escapes in a domain, as `%65vil.example`
  or `evil%2Eexample`.

Not counted, as the standard doesn't: case in schemes and hosts, a
default port written out, dot segments, and hosts that IDNA maps
(`ｅｖｉｌ.example`, `bücher.example`), which have one reading, in
`href`, everywhere.

## Policies

Decided 2026-10-30. The checks people get wrong by hand, on the parsed
URL: schemes, credentials, IP hosts, special addresses (against SSRF),
host allowlists, the same origin, redirect targets (path only), a
maximum length, and strict mode. One immutable `UrlPolicy`, built once,
from `UrlPolicy.any` (no rules), by `with` methods, each giving a new
policy with one more rule, and `policy.check(input)` giving a
`PolicyCheck`: the URL, or the first `PolicyRule` failed and a reason.

- **One object, not separate functions:** a check usually needs
  several rules at once, built from configuration once and applied to
  every request. Separate functions would each parse again, or take a
  `Url` and leave strict mode and length (which need the input) out.
  One `check` says which rule failed first, in one documented order.
- **`with` methods, not an object literal or a builder:** Temper has no
  named arguments outside constructors, and an object literal of eleven
  optional properties would be positional arguments in JavaScript, Lua,
  and C++. `with` methods translate plainly to all seven languages, as
  `Url`'s setters do, read well chained, and keep the policy immutable,
  so it can be shared between threads, and a check can't change after
  it's built. Booleans say what's allowed (`withCredentials(false)`),
  but for `withStrict(true)` and `withPathOnly(true)`, which ask for
  more. `UrlPolicy.any` is the start, since the constructor stays
  private, as `Url`'s does.
- **Results say which rule failed:** `PolicyRule` is a class with one
  instance per rule, as `HostKind` is, so every language compares and
  prints them alike; `reason` is for logs.
- **Hosts as parsed:** opaque hosts, in URLs that aren't special, are
  read as a special URL's host would be (`gopher://0x7f.1/`), since
  other clients may. Allowlist entries are parsed with `parseHost`, so
  they're lowercased, in Punycode, and canonical, and compared ignoring
  a trailing dot. An entry that isn't a host matches nothing.
- **Special addresses** come from IANA's IPv4 and IPv6 special-purpose
  registries (blocks not globally reachable), multicast and everything
  outside IPv6 global unicast from the address-space registries, NAT64
  and 6to4 (which embed any IPv4 address), and the names `localhost`,
  `local`, `home.arpa`, and `internal`, in one table in
  `src/policy.temper.md`, with each block's RFC. IPv4-mapped addresses
  are refused whole. A policy can't see DNS, so SSRF defenses still
  need to check the address connected to.
- **Path only** resolves the input against the base, and against the
  base with another host: a path, query, or fragment keeps both hosts,
  while `//evil.example`, `/\evil.example`, `\\evil.example`, and any
  absolute URL don't, all decided on the parsed result.

## Display formatting

Decided 2026-10-30, for step 5. `UrlDisplay.full.format(url)` formats a
URL for people, built with `with` methods as policies are:
`withUnicodeHosts`, `withDecoding`, `withCredentials`, `withFragment`,
and `withRootSlash`, each `false` to turn it off. `domainToDisplay` does
hosts alone. The display form is never for security decisions, nor for
handing on, and the docs on both say so.

**Hosts.** Chromium ([IDN in Google
Chrome](https://chromium.googlesource.com/chromium/src/+/main/docs/idn.md))
and Firefox ([IDN display
algorithm](https://wiki.mozilla.org/IDN_Display_Algorithm)) decide each
label alone, showing Unicode only if it passes rules built on [UTS
#39](https://www.unicode.org/reports/tr39/)'s restriction levels (Firefox's
default is Moderately Restrictive; Chromium's is close, but never mixes
Latin with Cyrillic or Greek), plus Chromium's own checks. What Hrefine
does, rule by rule:

| Rule | Source | Hrefine |
|---|---|---|
| Decide each label alone | both | yes |
| Valid IDNA, in normal form: the label converts to Unicode and back to the same `xn--` | both (a label that doesn't round-trip stays Punycode) | yes |
| Characters allowed in identifiers (UTS #39's Identifier Status) | both | in part: only IDNA-valid Latin letters, so no symbols, marks, or other scripts |
| One script, or an allowed mix (Latin with Han and kana, Bopomofo, or Hangul, or with one other script but Cyrillic and Greek) | both, UTS #39 section 5.2 | in part: Latin only, so nothing mixes |
| No digits from mixed numbering systems | both | yes, since only ASCII digits pass |
| No invisible characters or combining marks out of place | both, and Chromium's dot-above checks | yes, by allowing no combining marks at all |
| Whole-script look-alikes (`аррӏе` in Cyrillic for `apple`) | Chromium, by script and top-level domain | yes, since Cyrillic labels keep `xn--` for now |
| Latin look-alikes of ASCII letters (`ı`, `ɑ`, `ɡ`, `ĸ`, small capitals) | Unicode's confusables, as Chromium uses them, and Chromium's own additions (`ĸ`, `ħ`, `ŧ`, `ƅ`, `ŋ`) | a hand-picked list of 38, in `src/display.temper.md` |
| Labels whose look-alike skeleton matches a top domain | Chromium, with its top-domains list | no: that needs the list, and the full confusables table |

So Latin labels show in Unicode (`bücher`, `münchen`, `café`, `faß`)
unless they hold a look-alike, and all other scripts keep `xn--` for now:
stricter than both browsers, never looser. Unicode's data for the rest
isn't pinned yet, and unicode.org isn't reachable from the dev
container, so the Latin letters come from `UnicodeData.txt` (letters
named `LATIN …`, a subset of the Latin script), through
`scripts/display_tables.py` and `unicode_data.py`'s pinned hashes. To
show other scripts as browsers do, pin and use `Scripts.txt` and
`ScriptExtensions.txt` (UCD), and `IdentifierStatus.txt`,
`IdentifierType.txt`, and `confusables.txt` (Unicode's security data),
then check the restriction level, mixed numbers, and whole-script
look-alikes as above. The full `confusables.txt` is about 6,300
mappings; only the look-alikes of ASCII letters, a few hundred, would
need to ship, as a subset documented the same way.

**Decoding.** A path, query, or fragment shows escapes of non-ASCII
text decoded, as both browsers' address bars do, but only where it's
safe: a whole, shortest-form UTF-8 sequence for a code point that IDNA
calls valid (no controls, spaces, format characters such as bidi
controls, private use, or unassigned code points), but for the joiners
U+200C and U+200D, a short list of look-alikes of `/`, `\`, `?`, `#`,
padlocks, and blanks (after Chromium's and Firefox's decoders), and a
combining mark that would follow anything but decoded text. Escaped
ASCII always stays escaped, so `%2F`, `%3F`, `%25`, and `%20` keep their
meaning, and the display form parses back to the same `href` (the tests
check this).

**Options:** credentials, as browsers leave them out; the fragment; and
a path that's only `/`, with nothing after it, which special URLs read
back the same. The scheme stays: dropping `https://` hides what the
connection is.

## Comparison

Decided 2026-10-30, for step 5. Plain methods, beside `sameOrigin`,
rather than a comparison builder: there are three useful questions, and
each is the standard's or HTML's own:

- `==` (`eq`): the same URL, the standard's URL equals, comparing
  `href`s.
- `url.sameDocument(other)`: the same but for the fragment, the
  standard's URL equals with *exclude fragments*, as HTML uses for a
  jump within a page.
- `url.sameOrigin(other)`: the same origin, never for opaque ones.

A default port needs no option: the parser drops it, so
`https://example.com:443/` is `https://example.com/`, as are case in the
scheme and host, dot segments, and other IPv4 forms. Ignoring the query,
or comparing escapes as RFC 3986 does (`%7E` as `~`), would make URLs
equal that browsers and servers treat as different; comparing
`strictHref`s does the latter, for anyone who wants it.

## Source spans

Decided 2026-10-30, for step 5. `parseUrlSource(input, base?)` gives a
`UrlSource`: the input `asWritten`, the parsed `url`, and a `SourceSpan`
per part (`schemeSpan`, `usernameSpan`, `passwordSpan`, `hostSpan`,
`portSpan`, `pathSpan`, `querySpan`, and `fragmentSpan`), each with its
`start` and `length` in code points of the input as given, and its text
`asWritten`. A part the input didn't write (from the base, or absent)
has none; a part written empty has an empty span.

- **A separate type,** never members on `Url`, so code checking a URL
  can't reach the text as written, and policies and strict mode take
  only input and `Url`s.
- **Names say "as written":** `asWritten` is neither normalized nor
  checked (`EXAMPLE.com`, `0x7f.1`, a tab inside a host), and every
  member's docs say never to use it for security decisions.
- **Through what the standard strips:** spans count code points in the
  input as given, so they skip stripped leading and trailing controls
  and spaces, and keep tabs and newlines inside a part.
- **One record:** the parser notes where each part starts and ends in
  the same log as validation errors, so spans cost nothing unless asked
  for, and `ValidationError` gained a `length`: one code point, a whole
  host or port, the stripped ends, or none at the end of the input. The
  site's tester marks each error's span in the input.

Positions count code points, as Temper strings do; JavaScript callers
showing them in UTF-16 text convert, as the site does with `[...input]`.

## Lossless editing

Designed 2026-10-30, not built. A tool editing URLs in config files,
docs, or code (a linter fixing `http:` to `https:`, a refactor moving a
host) should change one part and leave the rest byte for byte as
written. On top of source spans:

- **An edit gives text and a URL:** `source.withHost("example.org")`
  (and the like, one per part) gives a new `UrlSource`, whose
  `asWritten` is the input with that span replaced, and whose `url` is
  that text parsed again, canonical, as `parseUrl` gives it. Nothing
  about the new text is trusted until parsed: if it doesn't parse, or
  its `url` isn't what the matching `Url` setter gives, the edit
  bubbles.
- **Escaping:** the new part is escaped only as much as it must be to
  mean what the setter means (an `@` in a username as `%40`, `#` in a
  path as `%23`), not normalized, so the rest of the text keeps its
  style.
- **Names:** as for spans, nothing on `Url`; methods on `UrlSource`,
  named for the text (`withHostWritten`, or `editHost`), to settle when
  built, never anything a policy or strict mode would take.
- **Risks:** the text as written can mean something else to other
  parsers than its `url` does (a backslash, a tab, `127.1`), and an edit
  keeps that. So an edited source's `url` is what to check and hand on,
  as ever, and a tool should warn when `asWritten` and `url.href`
  disagree in host or scheme (strict mode's errors say so). Spans
  across stripped tabs and newlines must be replaced whole, never split
  inside a removed run, or the edit could join two parts. A part
  missing from the text (from a base) can't be edited in place, only
  added, which needs rules for where its delimiters go.
- **Shared with htmlmd:** a planned lossless Markdown and HTML library
  (working name htmlmd), whose design hasn't started, needs the same
  span and edit model: text as written, spans in code points, edits that
  replace a span and reparse. The model should be one design, used by
  both, so building waits for htmlmd's design.

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
