# Hrefine

Parses and serializes URLs exactly as the [WHATWG URL
Standard](https://url.spec.whatwg.org/) says, as browsers do, with the
same results in every language.

Most languages' own URL parsers follow older rules, or their own, so
the same URL can name a different host in Python, Java, C#, and the
browser. Those gaps have caused real security holes: server-side
request forgery and allowlist bypasses, where a check reads a URL one
way and the request goes another. This library reads every URL as a
browser does, in every language it supports, checked against the
browsers' own test cases.

Parsing and serializing work on every backend, international domain
names included. Setters and search parameters come in step 3 of the
[plan](docs/plan.md).

## Examples

In Temper, and the same API in each supported language (to refine
before 1.0). The names are JavaScript's, so `parseUrl` throws (bubbles)
as `new URL()` does, and `Url.parse` gives null:

```temper
let url = parseUrl("https://user@EXAMPLE.com:443/a/../b?q=1#top") orelse panic();
url.href;     // "https://user@example.com/b?q=1#top"
url.hostname; // "example.com" (lowercased; the default port is dropped)
url.pathname; // "/b"

// Relative to a base, given as a string, or parsed once and reused.
(parseUrl("../c", "https://example.com/a/b") orelse panic()).href; // "https://example.com/c"
let base = parseUrl("https://example.com/a/b") orelse panic();
(base.resolve("../c") orelse panic()).href; // "https://example.com/c"

// Inputs that aren't URLs bubble, or give null, or say why.
Url.parse("https://exa mple.com");     // null
Url.canParse("https://exa mple.com");  // false
(checkUrl("https://exa mple.com") orelse panic()).errors; // [domain-invalid-code-point at 8]

// Typed parts, beside the standard's strings.
url.scheme;     // "https"
url.portNumber; // null (443 is the default)
url.hostKind;   // HostKind.domain
(parseUrl("http://0x7f.1/") orelse panic()).hostKind; // HostKind.ipv4, 127.0.0.1
url.sameOrigin(base); // true

// International domain names, as browsers read them.
(parseUrl("https://Bücher.example") orelse panic()).hostname; // "xn--bcher-kva.example"
domainToUnicode("xn--bcher-kva.example"); // "bücher.example"
```

The [tour](demos/README.md) shows the same in each language, with
identical output.

## API

- `parseUrl(input, base?)`: the standard's URL parser, as `new URL()`
  in JavaScript: a `Url`, or it bubbles (throws) where the standard
  fails. `Url.parse(input, base?)` gives null instead, and
  `Url.canParse(input, base?)` only says whether it would parse.
- `checkUrl(input, base?)`: a `UrlCheck`, with the `url` (or null) and
  the standard's validation errors, each with its `name` (such as
  `invalid-URL-unit` or `host-invalid-code-point`) and `position`, in
  code points. Where parsing fails, the last error says why. Most
  errors don't stop a URL from parsing, as browsers accept it. Parsing
  notes errors only when asked, so `parseUrl` is no slower for them.
- `Url`: the standard's getters, each a string, as in JavaScript:
  `href`, `origin`, `protocol`, `username`, `password`, `host`,
  `hostname`, `port`, `pathname`, `search`, and `hash`. Typed parts
  beside them: `scheme` (without the colon), `portNumber` (null where
  `port` is empty), and `hostKind` (`HostKind.domain`, `ipv4`, `ipv6`,
  `opaque`, or `empty`, or null without a host). And:
  - `url.resolve(ref)`: `ref` resolved against `url`, without parsing
    `url` again; it bubbles where that fails, and `url.tryResolve(ref)`
    gives null instead.
  - `url.sameOrigin(other)`: whether the two have the same origin;
    opaque origins (as for `data:` URLs) never do.
  - `toString()` gives `href`, and `==` in Temper compares `href`s
    (`eq` in other languages).
- `parseHost(input)`: checks a host, as in `https://input/`, giving a
  `Host` with its `kind` and `serialized` form, or bubbles.
- `domainToAscii(domain)` and `domainToUnicode(domain)`: the standard's
  domain to ASCII and to Unicode (IDNA), as in Node's `url` module, for
  converting and showing names. They aren't checks: domain to ASCII
  passes `exa mple.com`, `0x7f.1`, and `[::1]` as they are, as the
  standard says. Use `parseHost` to check a host.

Every language gets these names in its own style (`parse_url` and
`url.host_kind` in Python and Rust, `ParseUrl` and `url.HostKind` in C#,
`getHref()` in Java). Some don't yet carry everything over from Temper:
`toString` and `==` reach only some languages' own string conversion
and equality, and only Java and Rust keep `Url`'s constructor private;
see the tour for each.

## Using it safely

Hrefine doesn't change how other code reads URLs: `fetch`, `requests`,
`HttpClient`, and the rest keep their own parsers. So decide with
Hrefine, then hand on its `href`, never the original string:

```temper
let url = Url.parse(input);
if (
  url != null && url.scheme == "https" && url.hostKind == HostKind.domain &&
    isAllowed(url.hostname) // your check
) {
  fetchUrl(url.href); // your HTTP client, given href, not input
}
```

`hostKind` says whether the host is a name or an address, however the
address is written (`0x7f.1` is `127.0.0.1`), so an allowlist of names
can't be met by an address. To redirect to a user's `next` parameter,
resolve it against your own site, and check `sameOrigin`:

```temper
let next = site.tryResolve(param);
if (next != null && next.sameOrigin(site)) { redirectTo(next.href) }
```

`href` is the standard's canonical form: backslashes become slashes,
tabs and newlines are gone, hosts are lowercased and in ASCII (`127.1`
becomes `127.0.0.1`, international names become Punycode), and dot
segments are resolved. Most of what makes parsers disagree is gone, so
other parsers, browsers' and servers' alike, read it as Hrefine did.

## Tests

The tests are [web-platform-tests](https://github.com/web-platform-tests/wpt)'
own URL cases, the ones browsers are checked against, vendored in
[tests/wpt](tests/wpt) at a pinned commit (see [NOTICE](NOTICE)):

- `urltestdata.json`: 896 inputs, with bases, that must parse to given
  values for each part, or must fail. `scripts/wpt_tests.py` turns them
  into [a Temper test](src/wpt-url-tests.temper.md). All pass on every
  backend.
- `toascii.json` and `IdnaTestV2.json`: 87 and 2,675 international domain
  names, each with the host it must give, or none if it must fail.
  `scripts/wpt_idna_tests.py` turns them into [a Temper
  test](src/wpt-idna-tests.temper.md), which parses each as a URL's
  host, as web-platform-tests does. All pass on every backend, but for 2
  that Temper strings can't hold (unpaired surrogates), which are left
  out. The tests and the IDNA tables are both for Unicode 18.0.
- `setters_tests.json` and `percent-encoding.json`, for later steps.

## Languages

Made in Temper, it will support these languages, and its tests run on
each:

- C++
- C\#
- Java
- JavaScript
- Lua
- Python
- Rust

## Speed and size

`bench/` times Hrefine on the same inputs in every language: 50 URLs
(`bench/urls.txt`: mostly ASCII, some against a base, IPv4 and IPv6
hosts, percent-encoding, nine international hosts, and three that must
fail) and 12 domains to convert to ASCII (`bench/domains.txt`). Each
program in `bench/<language>/` first checks its results against
`bench/expected.txt` (which match Node's `URL`), then reports the
library's load time, the first domain beyond ASCII, and steady-state
nanoseconds per URL and per domain; the script also measures the
generated library without tests, raw and gzipped. One command builds
and runs it all, five runs per language:

    uv run bench/run.py [LANGUAGE ...]

Medians on a busy laptop (2026-10-29), so rough:

| Language | Load | First IDNA | Parse | IDNA | Size (gzipped) |
|---|---|---|---|---|---|
| C++ | 0.15 ms | 0.006 ms | 6.6 µs | 2.7 µs | 225 KB (43 KB) |
| C# | 4.4 ms | 11 ms (JIT) | 4.7 µs | 4.6 µs | 238 KB (41 KB) |
| Java | 4.1 ms | 0.45 ms | 7–15 µs | 1.6 µs | 201 KB (40 KB) |
| JavaScript | 4.4 ms | 0.9 ms | 5.9 µs | 5.9 µs | 157 KB (40 KB) |
| Lua | 3.9 ms | 0.11 ms | 113 µs | 132 µs | 160 KB (40 KB) |
| Python | 1.6 ms | 0.13 ms | 106 µs | 154 µs | 163 KB (39 KB) |
| Rust | 0.08 ms | 0.009 ms | 7.2 µs | 4.9 µs | 248 KB (45 KB) |

Load is after Temper's own runtime, which takes another 30–40 ms to
import in Python. The API revision after the tours (`checkUrl`, typed
parts, and `parseHost`) left parsing as fast, timed in turns, and added
about 21–23 KB (4 KB gzipped) in Python and JavaScript. The [plan](docs/plan.md) has what changed these.

## Development

Written with Claude Code and Opus 5.5.

Run tests with [Temper](https://temperlang.dev/), on one backend while
working:

    temper test -b py

Or on all of them:

    temper test -b cpp -b csharp -b java -b js -b lua -b py -b rust

Run the tour in every language against `temper.out/`, checking each
prints the same text (see [demos](demos/README.md)):

    uv run demos/run.py

CI runs the tests and the tour on every backend for pull requests and
pushes to `main`, using Temper's nightly `dev` build.

Regenerate the tests from web-platform-tests' data, and the IDNA tables
from Unicode's (which `scripts/unicode_data.py` downloads and checks):

    uv run scripts/wpt_tests.py
    uv run scripts/wpt_idna_tests.py
    uv run scripts/idna_tables.py
