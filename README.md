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

In Temper, and the same API in each supported language (a starting
point, to refine before 1.0):

```temper
let url = parseUrl("https://user@EXAMPLE.com:443/a/../b?q=1#top") orelse panic();
url.href;     // "https://user@example.com/b?q=1#top"
url.hostname; // "example.com" (lowercased; the default port is dropped)
url.pathname; // "/b"

// Relative to a base.
(parseUrl("../c", "https://example.com/a/b") orelse panic()).href; // "https://example.com/c"

// The same, as JavaScript's URL.parse.
Url.parse("../c", "https://example.com/a/b") orelse panic();

// Inputs that aren't URLs bubble.
parseUrl("https://exa mple.com") orelse null; // null

// International domain names, as browsers read them.
(parseUrl("https://Bücher.example") orelse panic()).hostname; // "xn--bcher-kva.example"
domainToUnicode("xn--bcher-kva.example"); // "bücher.example"
```

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
  that Temper strings can't hold (unpaired surrogates), and 7 that need
  Unicode 18.0, which the tests are for, where the IDNA tables are still
  17.0; the test counts those apart.
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

## Development

Written with Claude Code and Opus 5.5.

Run tests with [Temper](https://temperlang.dev/), on one backend while
working:

    temper test -b py

Or on all of them:

    temper test -b cpp -b csharp -b java -b js -b lua -b py -b rust

Regenerate the tests from web-platform-tests' data, and the IDNA tables
from Unicode's (which `scripts/unicode_data.py` downloads and checks):

    uv run scripts/wpt_tests.py
    uv run scripts/wpt_idna_tests.py
    uv run scripts/idna_tables.py
