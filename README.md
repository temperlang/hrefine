# Urlparser

Parses and serializes URLs exactly as the [WHATWG URL
Standard](https://url.spec.whatwg.org/) says, as browsers do, with the
same results in every language. (The name is a placeholder; see the
[candidates](docs/names.md).)

Most languages' own URL parsers follow older rules, or their own, so
the same URL can name a different host in Python, Java, C#, and the
browser. Those gaps have caused real security holes: server-side
request forgery and allowlist bypasses, where a check reads a URL one
way and the request goes another. This library reads every URL as a
browser does, in every language it supports, checked against the
browsers' own test cases.

Not yet working: it's being built (see the [plan](docs/plan.md)).

## Examples

In Temper, and the same API in each supported language (a starting
point, to refine before 1.0):

```temper
let url = parseUrl("https://user@EXAMPLE.com:443/a/../b?q=1#top") orelse panic();
url.href;     // "https://user@example.com/b?q=1#top"
url.hostname; // "example.com" (lowercased; the default port is dropped)
url.pathname; // "/b"

// Relative to a base.
parseUrl("../c", "https://example.com/a/b") orelse panic(); // https://example.com/c

// Inputs that aren't URLs bubble.
parseUrl("https://exa mple.com") orelse null; // null
```

## Tests

The tests are [web-platform-tests](https://github.com/web-platform-tests/wpt)'
own URL cases, the ones browsers are checked against, vendored in
[tests/wpt](tests/wpt) at a pinned commit (see [NOTICE](NOTICE)):

- `urltestdata.json`: 896 inputs, with bases, that must parse to given
  values for each part, or must fail. `scripts/wpt_tests.py` turns them
  into [a Temper test](src/wpt-url-tests.temper.md).
- `setters_tests.json`, `toascii.json` and `IdnaTestV2.json` (hosts and
  international domain names), and `percent-encoding.json`, for later
  steps.

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

Regenerate the tests from web-platform-tests' data:

    uv run scripts/wpt_tests.py
