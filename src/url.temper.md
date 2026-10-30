# URLs

Parsing and serializing URLs, following the WHATWG [URL
Standard](https://url.spec.whatwg.org/)'s [URL
parsing](https://url.spec.whatwg.org/#url-parsing) and [URL
serializing](https://url.spec.whatwg.org/#url-serializing) sections,
step by step, with their names, so each part can be checked against the
text. Hosts are in [host](host.temper.md), and percent-encoding in
[percent](percent.temper.md).

## The API

JavaScript's [`URL`](https://url.spec.whatwg.org/#url-class), with its
names: `parseUrl` bubbles where parsing fails, as `new URL()` throws,
`Url.parse` gives null instead, and `Url.canParse` only says whether
input parses. `checkUrl` says what was wrong, and a `Url` has typed
parts, resolving, and an origin check beside the standard's strings.

Parses `input`, against `base` if given, as the standard's [`URL`
constructor](https://url.spec.whatwg.org/#dom-url-url) does: it bubbles
where the standard says parsing fails, including when `base` doesn't
parse.

    export let parseUrl(input: String, base: String? = null): Url throws Bubble {
      urlOf(parseAgainst(input, base))
    }

    let parseAgainst(input: String, base: String?): UrlRecord throws Bubble {
      let baseRecord = if (base == null) { noBase } else { parseRecord(base, noBase, false, null) };
      parseRecord(input, baseRecord, base != null, null)
    }

Parses `input` as `parseUrl` does, but gives the URL, or null where
parsing fails, with the standard's [validation
errors](https://url.spec.whatwg.org/#validation-error) on the way. Most
don't stop a URL from parsing, as browsers accept it, but each says
what was off; when parsing fails, the last says why. Parsing notes them
only when asked, so `parseUrl` doesn't slow down for them. A `base`
that doesn't parse still bubbles, since it's the caller's own.

    export let checkUrl(input: String, base: String? = null): UrlCheck throws Bubble {
      let baseRecord = if (base == null) { noBase } else { parseRecord(base, noBase, false, null) };
      let log = new ErrorLog();
      let record: UrlRecord? = parseRecord(input, baseRecord, base != null, log) orelse null;
      let url: Url? = if (record == null) { null } else { urlOf(record) };
      new UrlCheck(url, log.errors.toList(), log.strict.toList())
    }

What `checkUrl` found: the URL, or null, and the validation errors, in
the order the parser noted them.

`strictErrors` are the ones strict mode counts, in the same order: every
validation error but `invalid-URL-unit` for a code point that a path,
query, fragment, or opaque host keeps or escapes, as `a b`, `a|b`, or
`?a[]=1`, which `href` holds unambiguously; and two of Hrefine's own,
for hosts the standard reads without a validation error:
`IPv4-non-canonical`, for an IPv4 address written any way but as its
four decimal numbers (`127.1`, `0x7f.1`, `2130706433`, `%31%32%37.1`,
or full-width digits), and `domain-percent-encoded`, for escapes in a
domain (`%65vil.example`). `strictUrl` is the URL if there are none, or
else null, for input as cautious parsers would take it. See the
[plan](../docs/plan.md), "Strict mode", for why.

    export class UrlCheck {
      public url: Url?;
      public errors: List<ValidationError>;
      public strictErrors: List<ValidationError>;

      private constructor(url: Url?, errors: List<ValidationError>, strictErrors: List<ValidationError>) {
        this.url = url;
        this.errors = errors;
        this.strictErrors = strictErrors;
      }

      public get strictUrl(): Url? { if (strictErrors.isEmpty) { url } else { null } }
    }

A [validation error](https://url.spec.whatwg.org/#validation-error):
its name in the standard, such as `invalid-URL-unit` or
`host-invalid-code-point`, and where it is, in code points from 0 in
the input as given, tabs, newlines, and spaces and controls at the ends
included: `position`, where the standard's parser was when it noted the
error, and `length`, how many code points it's about (`1` for one, the
whole host or port for an error in a host or port, and `0` at the end of
the input). Leading and trailing spaces and controls are each one error
for the run, and tabs and newlines one at the first.

    export class ValidationError {
      public name: String;
      public position: Int;
      public length: Int;

      private constructor(name: String, position: Int, length: Int) {
        this.name = name;
        this.position = position;
        this.length = length;
      }

      public toString(): String { "${name} at ${position.toString()}" }
    }

A parsed URL, with the standard's [`URL`
getters](https://url.spec.whatwg.org/#urlutils-members), each a string,
as in JavaScript, and typed parts beside them. It's immutable: the
standard's setters are methods here that give a new URL, such as
`url.withHost("example.com")` for JavaScript's `url.host =
"example.com"`, so a URL that passed a check stays as it was checked.

    export class Url {
      private schemeValue: String;
      private usernameValue: String;
      private passwordValue: String;
      private hostValue: String?;
      private portValue: Int;
      private pathValue: String;
      private query: String?;
      private fragment: String?;
      private opaquePath: Boolean;

The constructor is private, so every `Url` is a parsed one. Its parts
are as the [URL record](https://url.spec.whatwg.org/#concept-url) has
them, with the host and path already serialized, -1 for no port, and
whether the path is opaque. They're plain strings and numbers, since
Temper's C# backend makes private constructors public, and C# then
rejects internal types in their signatures.

      private constructor(
        scheme: String, username: String, password: String, host: String?,
        port: Int, path: String, query: String?, fragment: String?, opaquePath: Boolean,
      ) {
        this.schemeValue = scheme;
        this.usernameValue = username;
        this.passwordValue = password;
        this.hostValue = host;
        this.portValue = port;
        this.pathValue = path;
        this.query = query;
        this.fragment = fragment;
        this.opaquePath = opaquePath;
      }

As JavaScript's [`URL.parse`](https://url.spec.whatwg.org/#dom-url-parse):
the same as `parseUrl`, but null where that bubbles.

      public static parse(input: String, base: String? = null): Url? {
        parseUrl(input, base) orelse null
      }

As JavaScript's [`URL.canParse`](https://url.spec.whatwg.org/#dom-url-canparse):
whether `parseUrl` would give a URL, without making one.

      public static canParse(input: String, base: String? = null): Boolean {
        let record: UrlRecord? = parseAgainst(input, base) orelse null;
        record != null
      }

The [href](https://url.spec.whatwg.org/#dom-url-href): the whole URL,
serialized. It's also what `toString` gives, and what `==` compares.

      public get href(): String {
        serializeUrl(
          schemeValue, usernameValue, passwordValue, hostValue, portValue, pathValue, query,
          fragment,
        )
      }

The [strict RFC 3986 form](strict.temper.md): `href`, with what RFC
3986 doesn't allow there (such as `|`, `^`, `{`, and `}`) escaped, for
strict parsers such as Java's `URI`. It means the same URL.

      public get strictHref(): String {
        let h = hostValue;
        let q = query;
        let f = fragment;
        serializeUrl(
          schemeValue, strictPart(usernameValue, strictUserinfo),
          strictPart(passwordValue, strictUserinfo),
          if (h == null) {
            null
          } else if (h.hasIndex(String.begin) && h[String.begin] == char'[') {
            h
          } else {
            strictPart(h, strictHost)
          },
          portValue, strictPart(pathValue, if (opaquePath) { strictOpaquePath } else { strictPath }),
          if (q == null) { null } else { strictPart(q, strictQuery) },
          if (f == null) { null } else { strictPart(f, strictQuery) },
        )
      }

      public toString(): String { href }

      @operator("==")
      public eq(other: Url): Boolean { href == other.href }

The [origin](https://url.spec.whatwg.org/#dom-url-origin), serialized:
`scheme://host` with any port, for `http`, `https`, `ws`, `wss`, and
`ftp` URLs, or `null` for the rest, whose origins are opaque. A `blob:`
URL has the origin of the URL in its path, if that's `http` or `https`.

      public get origin(): String { originOf(schemeValue, hostValue, portValue, pathValue) }

Whether this URL and `other` have the [same
origin](https://url.spec.whatwg.org/#same-origin), as a browser checks
before letting one page read another's. Opaque origins never match
here, though both serialize as `null`: each is a new origin.

      public sameOrigin(other: Url): Boolean {
        let mine = origin;
        mine != "null" && mine == other.origin
      }

Whether this URL and `other` are the same but for their fragments, as
the standard's [URL equals](https://url.spec.whatwg.org/#concept-url-equals)
with *exclude fragments*, which browsers use to tell a jump within a
page from loading another. Use `==` (`eq`) for the same URL, fragment
and all. Both compare canonical forms, so case in the scheme and host,
a default port written out, dot segments, and IPv4 written in hex all
compare equal already.

      public sameDocument(other: Url): Boolean {
        beforeFragment(href) == beforeFragment(other.href)
      }

The [protocol](https://url.spec.whatwg.org/#dom-url-protocol): the
scheme and a colon, as `https:`, and the scheme alone, as `https`,
always lowercase.

      public get protocol(): String { "${schemeValue}:" }

      public get scheme(): String { schemeValue }

The [username](https://url.spec.whatwg.org/#dom-url-username) and
[password](https://url.spec.whatwg.org/#dom-url-password), percent-encoded.

      public get username(): String { usernameValue }

      public get password(): String { passwordValue }

The [host](https://url.spec.whatwg.org/#dom-url-host), with the port if
there is one, and the
[hostname](https://url.spec.whatwg.org/#dom-url-hostname), without it.
Both are empty without a host.

      public get host(): String {
        let h = hostValue;
        if (h == null) {
          ""
        } else if (portValue < 0) {
          h
        } else {
          "${h}:${portValue.toString()}"
        }
      }

      public get hostname(): String {
        let h = hostValue;
        if (h == null) { "" } else { h }
      }

What kind of [host](https://url.spec.whatwg.org/#concept-host) it is:
a domain, an IPv4 or IPv6 address, an opaque host (in URLs that aren't
special, as `foo://host`), or an empty host (as in `file:///etc`), or
null for none at all (as in `mailto:someone@example.com`). Checks that
must keep to the public internet need it, since `hostname` alone
doesn't say that `127.0.0.1` is an address.

      public get hostKind(): HostKind? {
        let h = hostValue;
        if (h == null) { null } else { kindOfHost(h, isSpecialScheme(schemeValue)) }
      }

The [port](https://url.spec.whatwg.org/#dom-url-port), empty if it's the
scheme's default, such as 443 for `https`, or missing; and the same as
a number, null for those.

      public get port(): String { if (portValue < 0) { "" } else { portValue.toString() } }

      public get portNumber(): Int? { if (portValue < 0) { null } else { portValue } }

The [pathname](https://url.spec.whatwg.org/#dom-url-pathname), as `/a/b`.

      public get pathname(): String { pathValue }

The [search](https://url.spec.whatwg.org/#dom-url-search) and
[hash](https://url.spec.whatwg.org/#dom-url-hash): the query and
fragment, after `?` and `#`, or empty if they're empty or missing.

      public get search(): String {
        let q = query;
        if (q == null) { "" } else if (q == "") { "" } else { "?${q}" }
      }

      public get hash(): String {
        let f = fragment;
        if (f == null) { "" } else if (f == "") { "" } else { "#${f}" }
      }

Resolves `ref` against this URL, as `parseUrl(ref, href)` would, but
without parsing this one again: `ref` is parsed with this URL as its
base. It bubbles where that fails; `tryResolve` gives null instead.

      public resolve(ref: String): Url throws Bubble {
        urlOf(parseRecord(ref, toRecord(), true, null))
      }

      public tryResolve(ref: String): Url? { resolve(ref) orelse null }

## Setters

The standard's [setters](https://url.spec.whatwg.org/#urlutils-members),
as methods that give a new URL, each named for the getter it sets:
`url.withPathname("/b")` is JavaScript's `url.pathname = "/b"`. As in
JavaScript, they don't fail: a value that can't be set leaves the URL
as it was, or as far as the standard got, as `withHost("example.com:x")`
changes the host but not the port. Only `withHref` bubbles, as setting
`href` throws, since it parses a whole new URL.

      public withHref(href: String): Url throws Bubble { parseUrl(href) }

The scheme, as `https` or `https:`; anything after the colon is
ignored.

      public withProtocol(protocol: String): Url {
        withOverride("${protocol}:", schemeStartState)
      }

The username and password, percent-encoded with the userinfo set, but
only in a URL that can have them: one with a host that isn't empty, and
not a `file` URL.

      public withUsername(username: String): Url {
        if (cannotHaveCredentialsOrPort) {
          this
        } else {
          let record = toRecord();
          record.username = percentEncodeString(username, userinfoSet);
          urlOf(record)
        }
      }

      public withPassword(password: String): Url {
        if (cannotHaveCredentialsOrPort) {
          this
        } else {
          let record = toRecord();
          record.password = percentEncodeString(password, userinfoSet);
          urlOf(record)
        }
      }

The host, with a port if it has one, and the hostname, without, parsed
as in a URL. Not for a URL with an opaque path, such as `mailto:`.

      public withHost(host: String): Url {
        if (opaquePath) { this } else { withOverride(host, hostState) }
      }

      public withHostname(hostname: String): Url {
        if (opaquePath) { this } else { withOverride(hostname, hostnameState) }
      }

The port, from the digits at the start of `port`, or none if it's
empty; not in a URL that can't have one.

      public withPort(port: String): Url {
        if (cannotHaveCredentialsOrPort) {
          this
        } else if (port == "") {
          let record = toRecord();
          record.port = -1;
          urlOf(record)
        } else {
          withOverride(port, portState)
        }
      }

The same with a number, beside `portNumber`: null for none, and a
number outside 0 to 65535 is ignored, as `withPort` ignores one.

      public withPortNumber(port: Int?): Url {
        if (port == null) {
          withPort("")
        } else if (port < 0 || port > 65535) {
          this
        } else {
          withPort(port.toString())
        }
      }

The path, parsed as a path, with dot segments resolved, and `?` and `#`
percent-encoded; not for a URL with an opaque path.

      public withPathname(pathname: String): Url {
        if (opaquePath) {
          this
        } else {
          let record = toRecord();
          record.path.clear();
          applyOverride(record, pathname, pathStartState)
        }
      }

The query and fragment, from `search` without a leading `?` and `hash`
without a leading `#`, percent-encoded. An empty string removes them.

      public withSearch(search: String): Url {
        if (search == "") {
          new Url(
            schemeValue, usernameValue, passwordValue, hostValue, portValue, pathValue, null,
            fragment, opaquePath,
          )
        } else {
          let record = toRecord();
          record.query = "";
          applyOverride(record, withoutLeading(search, char'?'), queryState)
        }
      }

      public withHash(hash: String): Url {
        if (hash == "") {
          new Url(
            schemeValue, usernameValue, passwordValue, hostValue, portValue, pathValue, query,
            null, opaquePath,
          )
        } else {
          let record = toRecord();
          record.fragment = "";
          applyOverride(record, withoutLeading(hash, char'#'), fragmentState)
        }
      }

The query as [search parameters](search-params.temper.md), a new list
each time, which changing doesn't change this URL; `withSearchParams`
gives a URL with them as its query, which, as the standard updates a
URL's query from its `searchParams`, is removed if they're empty.

      public get searchParams(): UrlSearchParams {
        // The constructor drops one leading `?`, so the query keeps any of
        // its own.
        let q = query;
        new UrlSearchParams(if (q == null) { "" } else { "?${q}" })
      }

      public withSearchParams(params: UrlSearchParams): Url {
        let serialized = params.toString();
        new Url(
          schemeValue, usernameValue, passwordValue, hostValue, portValue, pathValue,
          if (serialized == "") { null } else { serialized }, fragment, opaquePath,
        )
      }

A URL [can't have a username, password, or
port](https://url.spec.whatwg.org/#cannot-have-a-username-password-port)
without a host, or with an empty one, or as a `file` URL.

      private get cannotHaveCredentialsOrPort(): Boolean {
        let h = hostValue;
        h == null || h.isEmpty || schemeValue == "file"
      }

Runs the basic URL parser on `input`, from state `override`, to change
a copy of this URL.

      private withOverride(input: String, override: Int): Url {
        applyOverride(toRecord(), input, override)
      }

This URL as a record again, to be a base. Path segments can't hold `/`,
which the path set escapes, so splitting the serialized path gives them
back.

      private toRecord(): UrlRecord {
        let record = new UrlRecord();
        record.scheme = schemeValue;
        record.username = usernameValue;
        record.password = passwordValue;
        record.host = hostValue;
        record.port = portValue;
        if (opaquePath) {
          record.hasOpaquePath = true;
          record.opaquePath = pathValue;
        } else if (!pathValue.isEmpty) {
          let segments = pathValue.split("/");
          for (var k = 1; k < segments.length; k += 1) {
            record.path.add(segments[k]);
          }
        }
        record.query = query;
        record.fragment = fragment;
        record
      }
    }

Changes `record` by parsing `input` from state `override`, keeping
whatever the parser changed, even where it then fails, as the standard's
setters do, and gives the URL.

    let applyOverride(record: UrlRecord, input: String, override: Int): Url {
      let ignored: UrlRecord? = basicUrlParse(input, noBase, false, null, record, override) orelse null;
      urlOf(record)
    }

`href` up to its fragment, if any. Only the fragment can hold a `#`,
which the path and query sets escape, and which ends an opaque path.

    let beforeFragment(href: String): String {
      var i = String.begin;
      while (href.hasIndex(i) && href[i] != char'#') {
        i = href.next(i);
      }
      href.slice(String.begin, i)
    }

`s` without one leading `c`, if it starts with one.

    let withoutLeading(s: String, c: Int): String {
      if (s.hasIndex(String.begin) && s[String.begin] == c) { s.slice(s.next(String.begin), s.end) } else { s }
    }

A `Url` from a parsed record.

    let urlOf(record: UrlRecord): Url {
      new Url(
        record.scheme, record.username, record.password, record.host, record.port,
        serializePath(record), record.query, record.fragment, record.hasOpaquePath,
      )
    }

## Noting Validation Errors

When `checkUrl` asks, the parser notes each validation error in a log,
at the point where the standard notes it; otherwise the log is null, and
noting costs only that check, in branches that rarely run. Positions are
counted in the input after its tabs and newlines and leading controls
are removed, then moved back past those, so they point into the input
as given.

Strict mode's errors go in `strict` too: all the standard's, but for
code points a path, query, fragment, or opaque host keeps or escapes
(`noteLenient`), and Hrefine's own few (`noteStrict`), which only it
counts.

The log also keeps where each part of the URL was written, for
`parseUrlSource` (in [source](source.temper.md)): each a count of code
points in the cleaned input, or -1 if the parser didn't get there. And
while the parser reads a host or port, `spanEnd` is where it ends, so
its errors cover all of it.

    class ErrorLog {
      public errors: ListBuilder<ValidationError> = new ListBuilder<ValidationError>();
      public strict: ListBuilder<ValidationError> = new ListBuilder<ValidationError>();
      public removed: ListBuilder<Int> = new ListBuilder<Int>();
      public var length: Int = 0;
      public var spanEnd: Int = -1;
      public var schemeEnd: Int = -1;
      public var userinfoStart: Int = -1;
      public var colonAt: Int = -1;
      public var lastAt: Int = -1;
      public var hostStart: Int = -1;
      public var hostEnd: Int = -1;
      public var portStart: Int = -1;
      public var portEnd: Int = -1;
      public var pathStart: Int = -1;
      public var queryStart: Int = -1;
      public var fragmentStart: Int = -1;
    }

    let noteAt(log: ErrorLog?, name: String, at: Int): Void {
      if (log != null) {
        let error = errorAt(log, name, at);
        log.errors.add(error);
        log.strict.add(error);
      }
    }

    let noteLenient(log: ErrorLog, name: String, at: Int): Void {
      log.errors.add(errorAt(log, name, at));
    }

    let noteStrict(log: ErrorLog?, name: String, at: Int): Void {
      if (log != null) {
        log.strict.add(errorAt(log, name, at));
      }
    }

An error at `at` in the cleaned input, to the end of the host or port
being read, or else one code point, or none at the end.

    let errorAt(log: ErrorLog, name: String, at: Int): ValidationError {
      let end = if (log.spanEnd > at) { log.spanEnd } else if (at < log.length) { at + 1 } else { at };
      let position = positionIn(log, at);
      new ValidationError(name, position, endIn(log, at, end) - position)
    }

Where `at` in the cleaned input was in the input as given, and where a
span from `start` to `end` ends there, after its last code point.

    let positionIn(log: ErrorLog, at: Int): Int {
      var position = at;
      let removed = log.removed;
      for (var k = 0; k < removed.length && removed[k] <= position; k += 1) {
        position += 1;
      }
      position
    }

    let endIn(log: ErrorLog, start: Int, end: Int): Int {
      if (end > start) { positionIn(log, end - 1) + 1 } else { positionIn(log, start) }
    }

    let note(log: ErrorLog?, name: String, input: String, at: StringIndex): Void {
      if (log != null) {
        noteAt(log, name, input.countBetween(String.begin, at));
      }
    }

Where a run of `count` code points ending at `at` starts, as a count of
code points, for a host or port's errors; 0 when there's no log.

    let startOf(log: ErrorLog?, input: String, at: StringIndex, count: Int): Int {
      if (log == null) { 0 } else { input.countBetween(String.begin, at) - count }
    }

Where `at` is, as a count of code points, for the log's spans, or -1
without a log.

    let countAt(log: ErrorLog?, input: String, at: StringIndex): Int {
      if (log == null) { -1 } else { input.countBetween(String.begin, at) }
    }

The removals before parsing: one error for any leading or trailing C0
controls and spaces, covering the run, and one for any tabs and
newlines, at the first, and where each removed code point was, but for
trailing ones, which nothing follows. It also counts the cleaned input.

    let noteCleaning(log: ErrorLog, input: String): Void {
      var start = String.begin;
      var count = 0;
      while (input.hasIndex(start) && input[start] <= 0x20) {
        log.removed.add(count);
        start = input.next(start);
        count += 1;
      }
      var end = input.end;
      while (end > start && input[input.prev(end)] <= 0x20) {
        end = input.prev(end);
      }
      if (count > 0) {
        noteCleaned(log, 0, count);
      } else if (end < input.end) {
        let at = input.countBetween(String.begin, end);
        noteCleaned(log, at, input.countBetween(end, input.end));
      }
      var tabAt = -1;
      var kept = 0;
      for (var i = start; i < end; i = input.next(i)) {
        let c = input[i];
        if (c == 0x9 || c == 0xA || c == 0xD) {
          if (tabAt < 0) {
            tabAt = count;
          }
          log.removed.add(count);
        } else {
          kept += 1;
        }
        count += 1;
      }
      if (tabAt >= 0) {
        noteCleaned(log, tabAt, 1);
      }
      log.length = kept;
    }

    let noteCleaned(log: ErrorLog, at: Int, length: Int): Void {
      let error = new ValidationError("invalid-URL-unit", at, length);
      log.errors.add(error);
      log.strict.add(error);
    }

Code points that may be in a URL as they are, the standard's [URL code
points](https://url.spec.whatwg.org/#url-code-points): ASCII letters and
digits, some punctuation, and everything from U+00A0 on but surrogates
and noncharacters.

    let isUrlCode(c: Int): Boolean {
      if (c < 0x80) {
        isAsciiAlpha(c) || isDigit(c) || c == char'!' || c == char'$' ||
          (c >= char'&' && c <= char'/') || c == char':' || c == char';' || c == char'=' ||
          c == char'?' || c == char'@' || c == char'_' || c == char'~'
      } else {
        c >= 0xA0 && c <= 0x10FFFD && (c < 0xD800 || c > 0xDFFF) &&
          (c < 0xFDD0 || c > 0xFDEF) && (c & 0xFFFE) != 0xFFFE
      }
    }

Notes `invalid-URL-unit` for each code point from `start` to `end` that
isn't a URL code point or `%`, and each `%` without two hex digits after
it, as the path, query, fragment, and opaque path states do for each
code point they read. Only for a log.

    let noteUnits(log: ErrorLog, input: String, start: StringIndex, end: StringIndex): Void {
      var at = input.countBetween(String.begin, start);
      for (var i = start; i < end; i = input.next(i)) {
        noteUnit(log, input, i, at);
        at += 1;
      }
    }

    let noteUnit(log: ErrorLog, input: String, i: StringIndex, at: Int): Void {
      let c = input[i];
      if (c == char'%') {
        let first = input.next(i);
        let second = if (input.hasIndex(first)) { input.next(first) } else { first };
        if (
          !input.hasIndex(second) || hexValue(input[first]) < 0 || hexValue(input[second]) < 0
        ) {
          noteLenient(log, "invalid-URL-unit", at);
        }
      } else if (!isUrlCode(c)) {
        noteLenient(log, "invalid-URL-unit", at);
      }
    }

## URL Records

A [URL record](https://url.spec.whatwg.org/#concept-url) as the parser
builds it. The path is a list of segments, or an opaque path, a single
string, for URLs like `mailto:someone@example.com`, which has no host
and no slash after the scheme. A port of -1 means none.

    class UrlRecord {
      public var scheme: String = "";
      public var username: String = "";
      public var password: String = "";
      public var host: String? = null;
      public var port: Int = -1;
      public var path: ListBuilder<String> = new ListBuilder<String>();
      public var hasOpaquePath: Boolean = false;
      public var opaquePath: String = "";
      public var query: String? = null;
      public var fragment: String? = null;
    }

Stands in for the base where there isn't one.

    let noBase = new UrlRecord();

## Special Schemes

[Special schemes](https://url.spec.whatwg.org/#special-scheme) are those
web browsers treat specially, with hierarchical paths and hosts that
must be domains or IP addresses. Each but `file` has a default port.

    let isSpecialScheme(scheme: String): Boolean {
      scheme == "http" || scheme == "https" || scheme == "ws" || scheme == "wss" ||
        scheme == "ftp" || scheme == "file"
    }

    let defaultPort(scheme: String): Int {
      if (scheme == "http" || scheme == "ws") {
        80
      } else if (scheme == "https" || scheme == "wss") {
        443
      } else if (scheme == "ftp") {
        21
      } else {
        -1
      }
    }

## Windows Drive Letters

A [Windows drive letter](https://url.spec.whatwg.org/#windows-drive-letter)
is an ASCII letter and `:` or `|`, as `C:`; a normalized one has `:`.
`file` URLs keep them at the start of the path, even through `..`.

    let isWindowsDriveLetter(s: String, normalized: Boolean): Boolean {
      let first = String.begin;
      if (!s.hasIndex(first)) {
        return false;
      }
      let second = s.next(first);
      if (!s.hasIndex(second) || s.hasIndex(s.next(second))) {
        return false;
      }
      isAsciiAlpha(s[first]) &&
        (s[second] == char':' || (!normalized && s[second] == char'|'))
    }

Whether `s` from `i` [starts with a Windows drive
letter](https://url.spec.whatwg.org/#start-with-a-windows-drive-letter):
a drive letter, followed by the end or `/`, `\`, `?`, or `#`.

    let startsWithWindowsDriveLetter(s: String, i: StringIndex): Boolean {
      if (!s.hasIndex(i) || !isAsciiAlpha(s[i])) {
        return false;
      }
      let second = s.next(i);
      if (!s.hasIndex(second) || (s[second] != char':' && s[second] != char'|')) {
        return false;
      }
      let third = s.next(second);
      if (!s.hasIndex(third)) {
        return true;
      }
      let c = s[third];
      c == char'/' || c == 0x5C || c == char'?' || c == char'#'
    }

    let isAsciiAlpha(c: Int): Boolean {
      (c >= char'a' && c <= char'z') || (c >= char'A' && c <= char'Z')
    }

## Paths

To [shorten a path](https://url.spec.whatwg.org/#shorten-a-urls-path),
as `..` does, remove its last segment, except a `file` URL's lone drive
letter.

    let shortenPath(url: UrlRecord): Void {
      let path = url.path;
      if (
        path.length > 0 &&
          !(url.scheme == "file" && path.length == 1 && isWindowsDriveLetter(path[0], true))
      ) {
        path.removeLast();
      }
    }

[Single-dot](https://url.spec.whatwg.org/#single-dot-path-segment) and
[double-dot](https://url.spec.whatwg.org/#double-dot-path-segment)
segments, with dots possibly written as `%2e`, in either case.

    let isSingleDot(s: String): Boolean {
      s == "." || s == "%2e" || s == "%2E"
    }

    let isDoubleDot(s: String): Boolean {
      when (s) {
        "..", ".%2e", ".%2E", "%2e.", "%2E.", "%2e%2e", "%2E%2E", "%2e%2E", "%2E%2e" -> true;
        else -> false;
      }
    }

## The Basic URL Parser

The [basic URL parser](https://url.spec.whatwg.org/#concept-basic-url-parser)
first trims C0 controls and spaces from both ends, and drops every tab
and newline, wherever it is. Given a URL to change, as the
setters (`withHost` and the rest) do, it only drops tabs and newlines.

    let cleanInput(input: String): String {
      if (isClean(input)) { input } else { cleanAll(input) }
    }

    let cleanAll(input: String): String {
      var start = String.begin;
      while (input.hasIndex(start) && input[start] <= 0x20) {
        start = input.next(start);
      }
      var end = input.end;
      while (end > start && input[input.prev(end)] <= 0x20) {
        end = input.prev(end);
      }
      let out = new StringBuilder();
      for (var i = start; i < end; i = input.next(i)) {
        let c = input[i];
        if (c != 0x9 && c != 0xA && c != 0xD) {
          appendCode(out, c);
        }
      }
      out.toString()
    }

    let removeTabs(input: String): String {
      if (hasNoTabs(input)) {
        input
      } else {
        let out = new StringBuilder();
        for (var i = String.begin; input.hasIndex(i); i = input.next(i)) {
          let c = input[i];
          if (c != 0x9 && c != 0xA && c != 0xD) {
            appendCode(out, c);
          }
        }
        out.toString()
      }
    }

Most input has nothing to remove, which is quick to see. Splitting
checks for tabs and newlines in each language's own code, much faster
than a loop here in some, while `indexOf` isn't safe for this in C#,
where Temper's translation compares by culture, which can skip some
control characters (as of 2026-10-29).

    let isClean(input: String): Boolean {
      if (!input.hasIndex(String.begin)) {
        true
      } else {
        input[String.begin] > 0x20 && input[input.prev(input.end)] > 0x20 && hasNoTabs(input)
      }
    }

    let hasNoTabs(input: String): Boolean {
      input.split("\t").length == 1 && input.split("\n").length == 1 &&
        input.split("\r").length == 1
    }

Then it runs a state machine over the input's code points, one at a
time, with the end of input as one more, the standard's EOF code point
(-1 here). Each state below is a number, named as in the standard.

    let schemeStartState = 0;
    let schemeState = 1;
    let noSchemeState = 2;
    let specialRelativeOrAuthorityState = 3;
    let pathOrAuthorityState = 4;
    let relativeState = 5;
    let relativeSlashState = 6;
    let specialAuthoritySlashesState = 7;
    let specialAuthorityIgnoreSlashesState = 8;
    let authorityState = 9;
    let hostState = 10;
    let portState = 11;
    let fileState = 12;
    let fileSlashState = 13;
    let fileHostState = 14;
    let pathStartState = 15;
    let pathState = 16;
    let opaquePathState = 17;
    let queryState = 18;
    let fragmentState = 19;

The hostname state is the host state but for one step, so the parser
runs the host state for both, and checks the override for that step.
No override is -1.

    let hostnameState = 20;
    let noOverride = -1;

    let eof = -1;
    let backslash = 0x5C;

Parses `input` against `base`, if `hasBase`, noting validation errors
in `log`, if given.

    let parseRecord(
      rawInput: String, base: UrlRecord, hasBase: Boolean, log: ErrorLog?,
    ): UrlRecord throws Bubble {
      basicUrlParse(rawInput, base, hasBase, log, null, noOverride)
    }

The standard's parser takes a URL to change, `target`, and a state
`override` to start in, for the setters. Then it changes `target` in
place, and where the standard says to return early, it returns it, or
bubbles where it says to return failure. Either way, what it changed
before stays changed, as the standard has it. Without an override,
`target` is null, and the parser makes a new URL.

    let basicUrlParse(
      rawInput: String, base: UrlRecord, hasBase: Boolean, log: ErrorLog?, target: UrlRecord?,
      override: Int,
    ): UrlRecord throws Bubble {
      if (log != null) {
        noteCleaning(log, rawInput);
      }
      let input = if (target == null) { cleanInput(rawInput) } else { removeTabs(rawInput) };
      let url = if (target == null) { new UrlRecord() } else { target };
      let overridden = override != noOverride;
      var special = isSpecialScheme(url.scheme);
      var state = if (override == hostnameState) {
        hostState
      } else if (overridden) {
        override
      } else {
        schemeStartState
      };

The standard's buffer, with a count of its code points, so checking
whether it's empty doesn't need a string.

      let buffer = new StringBuilder();
      var bufferCount = 0;
      var atSignSeen = false;
      var insideBrackets = false;
      var passwordTokenSeen = false;

The authority state reads its buffer from the input, from
`authorityStart` to the pointer, since when it reaches the host it goes
back to reread it. `authorityStarted` is false until its first code
point.

      var authorityStart = String.begin;
      var authorityStarted = false;
      var portValue = 0;

The opaque path, query, and fragment are kept here, then stored at the
end. (Strings, not builders, since the query and fragment are each read
at once, and builders cost much in some languages.)

      var queryText = "";
      var inQuery = override == queryState;
      var fragmentText = "";
      var inFragment = override == fragmentState;
      var opaqueText = url.opaquePath;

The pointer, and whether the state just run asked to see the same code
point again. The standard says "decrease pointer by 1" and then always
increases it, which here is `again`.

      var pointer = String.begin;
      while (true) {
        let c = if (input.hasIndex(pointer)) { input[pointer] } else { eof };
        var again = false;
        if (log != null) {
          noteSpanStarts(log, state, input, pointer);
        }

### Scheme Start State

        if (state == schemeStartState) {
          if (isAsciiAlpha(c)) {
            appendCode(buffer, c | 0x20);
            state = schemeState;
          } else if (!overridden) {
            state = noSchemeState;
            again = true;
          } else {
            bubble();
          }

### Scheme State

A scheme is a letter followed by letters, digits, `+`, `-`, and `.`,
lowercased, up to a `:`. Without the `:`, there's no scheme after all,
so it starts over in the no scheme state. (Here and in other states, a
run of code points that the state treats alike is taken at once, and
the pointer left on the last, which runs much faster than one at a
time, since most URLs are made of such runs.)

        } else if (state == schemeState) {
          if (isSchemeCode(c)) {
            var end = input.next(pointer);
            while (input.hasIndex(end) && isSchemeCode(input[end])) {
              end = input.next(end);
            }
            buffer.append(asciiLowercase(input.slice(pointer, end)));
            pointer = input.prev(end);
          } else if (c == char':') {
            let scheme = buffer.toString();

With an override, as for the `protocol` setter, the scheme changes only
between special schemes, or between schemes that aren't, and not to
`file` with credentials or a port, nor from `file` with an empty host.
A port that's the new scheme's default goes.

            if (overridden) {
              let host = url.host;
              if (
                isSpecialScheme(url.scheme) == isSpecialScheme(scheme) &&
                  !(scheme == "file" && (hasCredentials(url) || url.port >= 0)) &&
                  !(url.scheme == "file" && host != null && host.isEmpty)
              ) {
                url.scheme = scheme;
                if (url.port == defaultPort(scheme)) {
                  url.port = -1;
                }
              }
              return url;
            }
            url.scheme = scheme;
            special = isSpecialScheme(url.scheme);
            buffer.clear();
            if (log != null) {
              log.schemeEnd = countAt(log, input, pointer);
            }
            if (url.scheme == "file") {
              if (log != null && (peek(input, pointer) != char'/' || peek(input, input.next(pointer)) != char'/')) {
                note(log, "special-scheme-missing-following-solidus", input, pointer);
              }
              state = fileState;
            } else if (special && hasBase && base.scheme == url.scheme) {
              state = specialRelativeOrAuthorityState;
            } else if (special) {
              state = specialAuthoritySlashesState;
            } else if (peek(input, pointer) == char'/') {
              state = pathOrAuthorityState;
              pointer = input.next(pointer);
            } else {
              url.hasOpaquePath = true;
              state = opaquePathState;
            }
          } else if (!overridden) {
            buffer.clear();
            state = noSchemeState;
            pointer = String.begin;
            again = true;
          } else {
            bubble();
          }

### No Scheme State

Without a scheme, the input is relative to the base, which must have
one, and not an opaque path, unless the input is only a fragment.

        } else if (state == noSchemeState) {
          if (!hasBase || (base.hasOpaquePath && c != char'#')) {
            note(log, "missing-scheme-non-relative-URL", input, pointer);
            bubble();
          } else if (base.hasOpaquePath && c == char'#') {
            url.scheme = base.scheme;
            special = isSpecialScheme(url.scheme);
            url.hasOpaquePath = true;
            opaqueText = base.opaquePath;
            url.query = base.query;
            inFragment = true;
            state = fragmentState;
          } else if (base.scheme != "file") {
            state = relativeState;
            again = true;
          } else {
            state = fileState;
            again = true;
          }

### Special Relative or Authority State

        } else if (state == specialRelativeOrAuthorityState) {
          if (c == char'/' && peek(input, pointer) == char'/') {
            state = specialAuthorityIgnoreSlashesState;
            pointer = input.next(pointer);
          } else {
            note(log, "special-scheme-missing-following-solidus", input, pointer);
            state = relativeState;
            again = true;
          }

### Path or Authority State

        } else if (state == pathOrAuthorityState) {
          if (c == char'/') {
            state = authorityState;
          } else {
            notePathStart(log, input, pointer, 1);
            state = pathState;
            again = true;
          }

### Relative State

A relative URL takes the base's scheme, and the rest of the base up to
where the input starts: `?q` keeps the base's path, and `x` replaces its
last segment.

        } else if (state == relativeState) {
          url.scheme = base.scheme;
          special = isSpecialScheme(url.scheme);
          if (c == char'/' || (special && c == backslash)) {
            if (c == backslash) {
              note(log, "invalid-reverse-solidus", input, pointer);
            }
            state = relativeSlashState;
          } else {
            url.username = base.username;
            url.password = base.password;
            url.host = base.host;
            url.port = base.port;
            url.path.addAll(base.path);

The standard copies the base's query and then sets it to null if a path
follows. Here it's copied only where it's kept, since Temper's Rust
backend can't yet compile assigning `null` to this property.

            if (c == char'?') {
              inQuery = true;
              state = queryState;
            } else if (c == char'#') {
              url.query = base.query;
              inFragment = true;
              state = fragmentState;
            } else if (c != eof) {
              shortenPath(url);
              state = pathState;
              again = true;
            } else {
              url.query = base.query;
            }
          }

### Relative Slash State

        } else if (state == relativeSlashState) {
          if (special && (c == char'/' || c == backslash)) {
            if (c == backslash) {
              note(log, "invalid-reverse-solidus", input, pointer);
            }
            state = specialAuthorityIgnoreSlashesState;
          } else if (c == char'/') {
            state = authorityState;
          } else {
            url.username = base.username;
            url.password = base.password;
            url.host = base.host;
            url.port = base.port;
            notePathStart(log, input, pointer, 1);
            state = pathState;
            again = true;
          }

### Special Authority Slashes State

        } else if (state == specialAuthoritySlashesState) {
          if (c == char'/' && peek(input, pointer) == char'/') {
            state = specialAuthorityIgnoreSlashesState;
            pointer = input.next(pointer);
          } else {
            note(log, "special-scheme-missing-following-solidus", input, pointer);
            state = specialAuthorityIgnoreSlashesState;
            again = true;
          }

### Special Authority Ignore Slashes State

Special URLs skip any number of slashes and backslashes before the
authority, so `http:\\\example.com` works.

        } else if (state == specialAuthorityIgnoreSlashesState) {
          if (c != char'/' && c != backslash) {
            state = authorityState;
            again = true;
          } else {
            note(log, "special-scheme-missing-following-solidus", input, pointer);
          }

### Authority State

The authority is everything up to the path, query, or fragment. Its
last `@` ends the user and password, which are percent-encoded with the
userinfo set, split at the first `:`; any earlier `@` is part of them,
as `%40`. Then the parser goes back to read the host and port.

        } else if (state == authorityState) {
          if (!authorityStarted) {
            authorityStart = pointer;
            authorityStarted = true;
          }
          if (c == char'@') {
            note(log, "invalid-credentials", input, pointer);
            let credentials = new StringBuilder();
            if (atSignSeen) {
              credentials.append("%40");
            }
            atSignSeen = true;
            if (log != null) {
              if (log.userinfoStart < 0) {
                log.userinfoStart = countAt(log, input, authorityStart);
              }
              log.lastAt = countAt(log, input, pointer);
            }
            for (var i = authorityStart; i < pointer; i = input.next(i)) {
              let code = input[i];
              if (code == char':' && !passwordTokenSeen) {
                if (log != null) {
                  log.colonAt = countAt(log, input, i);
                }
                url.username = "${url.username}${credentials.toString()}";
                credentials.clear();
                passwordTokenSeen = true;
              } else {
                percentEncodeOnto(credentials, code, userinfoSet);
              }
            }
            if (passwordTokenSeen) {
              url.password = "${url.password}${credentials.toString()}";
            } else {
              url.username = "${url.username}${credentials.toString()}";
            }
            authorityStart = input.next(pointer);
          } else if (c == eof || isAuthorityEnd(c, special)) {
            if (atSignSeen && authorityStart == pointer) {
              note(log, "host-missing", input, pointer);
              bubble();
            }
            pointer = authorityStart;
            state = hostState;
            again = true;
          } else {
            pointer = input.prev(runEnd(input, pointer, special, char'@'));
          }

### Host State and Hostname State

The host ends at a `:` outside brackets, which starts the port, or at
the path, query, or fragment. Special URLs need a host. With an
override, a `file` URL's host goes to the file host state, the hostname
state stops at a port, and the parser stops after the host (or the
port). A URL with credentials or a port can't lose its host.

        } else if (state == hostState) {
          if (overridden && url.scheme == "file") {
            state = fileHostState;
            again = true;
          } else if (c == char':' && !insideBrackets) {
            if (bufferCount == 0) {
              note(log, "host-missing", input, pointer);
              bubble();
            }
            if (override == hostnameState) {
              bubble();
            }
            noteHostSpan(log, input, pointer, bufferCount);
            url.host = runHostParser(
              buffer.toString(), !special, log, startOf(log, input, pointer, bufferCount),
            );
            if (log != null) {
              log.spanEnd = -1;
              log.portStart = log.hostEnd + 1;
            }
            buffer.clear();
            bufferCount = 0;
            state = portState;
          } else if (c == eof || isAuthorityEnd(c, special)) {
            if (special && bufferCount == 0) {
              note(log, "host-missing", input, pointer);
              bubble();
            }
            if (overridden && bufferCount == 0 && (hasCredentials(url) || url.port >= 0)) {
              bubble();
            }
            noteHostSpan(log, input, pointer, bufferCount);
            url.host = runHostParser(
              buffer.toString(), !special, log, startOf(log, input, pointer, bufferCount),
            );
            if (log != null) {
              log.spanEnd = -1;
            }
            if (overridden) {
              return url;
            }
            buffer.clear();
            bufferCount = 0;
            state = pathStartState;
            again = true;
          } else {
            var end = pointer;
            var more = true;
            while (more) {
              let d = input[end];
              if (d == char'[') {
                insideBrackets = true;
              } else if (d == char']') {
                insideBrackets = false;
              }
              bufferCount += 1;
              end = input.next(end);
              if (input.hasIndex(end)) {
                let e = input[end];
                more = (e != char':' || insideBrackets) && !isAuthorityEnd(e, special);
              } else {
                more = false;
              }
            }
            buffer.append(input.slice(pointer, end));
            pointer = input.prev(end);
          }

### Port State

A port is decimal digits, at most 65535, and none at all if it's the
scheme's default. With an override, as for the `port` setter, the port
ends at anything else, and must have a digit.

        } else if (state == portState) {
          if (isDigit(c)) {
            portValue = portValue * 10 + c - char'0';
            if (portValue > 65535) {
              if (log == null) {
                bubble();
              }
              portValue = 65536;
            }
            bufferCount += 1;
          } else if (c == eof || isAuthorityEnd(c, special) || overridden) {
            if (log != null) {
              log.portEnd = countAt(log, input, pointer);
              log.spanEnd = log.portEnd;
            }
            if (bufferCount != 0) {
              if (portValue > 65535) {
                noteAt(log, "port-out-of-range", startOf(log, input, pointer, bufferCount));
                bubble();
              }
              url.port = if (portValue == defaultPort(url.scheme)) { -1 } else { portValue };
              if (overridden) {
                return url;
              }
              portValue = 0;
              bufferCount = 0;
            }
            if (overridden) {
              bubble();
            }
            if (log != null) {
              log.spanEnd = -1;
            }
            state = pathStartState;
            again = true;
          } else {
            note(log, "port-invalid", input, pointer);
            bubble();
          }

### File State

`file` URLs have their own states, mostly for Windows drive letters, and
since their host may be empty, as in `file:///etc`.

        } else if (state == fileState) {
          url.scheme = "file";
          special = true;
          url.host = "";
          if (c == char'/' || c == backslash) {
            if (c == backslash) {
              note(log, "invalid-reverse-solidus", input, pointer);
            }
            state = fileSlashState;
          } else if (hasBase && base.scheme == "file") {
            url.host = base.host;
            url.path.addAll(base.path);
            if (c == char'?') {
              inQuery = true;
              state = queryState;
            } else if (c == char'#') {
              url.query = base.query;
              inFragment = true;
              state = fragmentState;
            } else if (c == eof) {
              url.query = base.query;
            } else {
              if (!startsWithWindowsDriveLetter(input, pointer)) {
                shortenPath(url);
              } else {
                note(log, "file-invalid-Windows-drive-letter", input, pointer);
                url.path.clear();
              }
              state = pathState;
              again = true;
            }
          } else {
            state = pathState;
            again = true;
          }

### File Slash State

        } else if (state == fileSlashState) {
          if (c == char'/' || c == backslash) {
            if (c == backslash) {
              note(log, "invalid-reverse-solidus", input, pointer);
            }
            state = fileHostState;
          } else {
            if (hasBase && base.scheme == "file") {
              url.host = base.host;
              if (
                !startsWithWindowsDriveLetter(input, pointer) && base.path.length > 0 &&
                isWindowsDriveLetter(base.path[0], true)
              ) {
                url.path.add(base.path[0]);
              }
            }
            notePathStart(log, input, pointer, 1);
            state = pathState;
            again = true;
          }

### File Host State

A drive letter where the host would be, as in `file://C:/x`, is the
start of the path instead (but for an override), and `localhost` is the
same as no host.

        } else if (state == fileHostState) {
          if (c == eof || c == char'/' || c == backslash || c == char'?' || c == char'#') {
            again = true;
            let text = buffer.toString();
            if (!overridden && isWindowsDriveLetter(text, false)) {
              noteHostSpan(log, input, pointer, bufferCount);
              noteAt(log, "file-invalid-Windows-drive-letter-host", startOf(log, input, pointer, bufferCount));
              if (log != null) {
                log.spanEnd = -1;
                log.hostStart = -1;
                log.pathStart = log.hostEnd - bufferCount;
              }
              state = pathState;
            } else if (bufferCount == 0) {
              noteHostSpan(log, input, pointer, 0);
              if (log != null) {
                log.spanEnd = -1;
              }
              url.host = "";
              if (overridden) {
                return url;
              }
              state = pathStartState;
            } else {
              noteHostSpan(log, input, pointer, bufferCount);
              let host = runHostParser(
                text, !special, log, startOf(log, input, pointer, bufferCount),
              );
              if (log != null) {
                log.spanEnd = -1;
              }
              url.host = if (host == "localhost") { "" } else { host };
              if (overridden) {
                return url;
              }
              buffer.clear();
              bufferCount = 0;
              state = pathStartState;
            }
          } else {
            appendCode(buffer, c);
            bufferCount += 1;
          }

### Path Start State

With an override, as for the `pathname` setter, `?` and `#` are part of
the path, and a URL without a host gets an empty path segment, so that
its path is `/`.

        } else if (state == pathStartState) {
          if (special) {
            if (c == backslash) {
              note(log, "invalid-reverse-solidus", input, pointer);
            }
            state = pathState;
            if (c != char'/' && c != backslash) {
              again = true;
            }
          } else if (c == char'?' && !overridden) {
            inQuery = true;
            state = queryState;
          } else if (c == char'#' && !overridden) {
            inFragment = true;
            state = fragmentState;
          } else if (c != eof) {
            state = pathState;
            if (c != char'/') {
              again = true;
            }
          } else if (overridden && url.host == null) {
            url.path.add("");
          }

### Path State

Each segment is percent-encoded with the path set. At its end, `..`
removes the segment before, `.` is dropped, and a `file` URL's first
segment, if a drive letter, is normalized to use `:`. With an override,
`?` and `#` don't end the path, and are percent-encoded.

        } else if (state == pathState) {
          let slash = c == char'/' || (special && c == backslash);
          if (slash || c == eof || (!overridden && (c == char'?' || c == char'#'))) {
            if (special && c == backslash) {
              note(log, "invalid-reverse-solidus", input, pointer);
            }
            let segment = buffer.toString();
            let doubleDot = isDoubleDot(segment);
            if (doubleDot) {
              shortenPath(url);
            }

A `.` or `..` at the end of the path leaves it ending in `/`, as an
empty segment. (The checks are flat, not nested as in the standard,
since Temper's C# backend drops the braces around a lone nested `if`,
so a following `else` attaches to it.)

            if (!doubleDot && !isSingleDot(segment)) {
              if (
                url.scheme == "file" && url.path.length == 0 &&
                isWindowsDriveLetter(segment, false)
              ) {
                url.path.add("${segment.slice(String.begin, segment.next(String.begin))}:");
              } else {
                url.path.add(segment);
              }
            } else if (!slash) {
              url.path.add("");
            }
            buffer.clear();
            bufferCount = 0;
            if (c == char'?') {
              inQuery = true;
              state = queryState;
            } else if (c == char'#') {
              inFragment = true;
              state = fragmentState;
            }
          } else {
            var clean = !inEncodeSet(c, pathSet);
            var end = input.next(pointer);
            var more = true;
            while (more && input.hasIndex(end)) {
              let d = input[end];
              more = !isAuthorityEnd(d, special) || (overridden && (d == char'?' || d == char'#'));
              if (more) {
                clean = clean && !inEncodeSet(d, pathSet);
                end = input.next(end);
              }
            }
            if (log != null) {
              noteUnits(log, input, pointer, end);
            }
            buffer.append(encodedSlice(input, pointer, end, pathSet, clean));
            pointer = input.prev(end);
          }

### Opaque Path State

An opaque path is percent-encoded only with the C0 control set. A space
right before the query or fragment becomes `%20`, so that removing them
later can't leave a trailing space.

        } else if (state == opaquePathState) {
          if (c == char'?') {
            inQuery = true;
            state = queryState;
          } else if (c == char'#') {
            inFragment = true;
            state = fragmentState;
          } else if (c == char' ') {
            let next = peek(input, pointer);
            opaqueText = if (next == char'?' || next == char'#') {
              "${opaqueText}%20"
            } else {
              "${opaqueText} "
            };
          } else if (c != eof) {
            let end = opaqueRunEnd(input, pointer);
            if (log != null) {
              noteUnits(log, input, pointer, end);
            }
            opaqueText = "${opaqueText}${percentEncodeSlice(input, pointer, end, c0ControlSet)}";
            pointer = input.prev(end);
          }

### Query State

A query is percent-encoded with the query set, or the special-query set
for special URLs, which also escapes `'`. (Only UTF-8 is supported, as
the standard's `URL` API uses.) With an override, as for the `search`
setter, `#` is part of the query, and percent-encoded.

        } else if (state == queryState) {
          if (c == char'#' && !overridden) {
            inFragment = true;
            state = fragmentState;
          } else if (c != eof) {
            let set = if (special) { specialQuerySet } else { querySet };
            var clean = !inEncodeSet(c, set);
            var end = input.next(pointer);
            var more = true;
            while (more && input.hasIndex(end)) {
              let d = input[end];
              more = d != char'#' || overridden;
              if (more) {
                clean = clean && !inEncodeSet(d, set);
                end = input.next(end);
              }
            }
            if (log != null) {
              noteUnits(log, input, pointer, end);
            }
            queryText = encodedSlice(input, pointer, end, set, clean);
            pointer = input.prev(end);
          }

### Fragment State

The fragment is the rest of the input.

        } else {
          if (c != eof) {
            var clean = true;
            for (var i = pointer; clean && input.hasIndex(i); i = input.next(i)) {
              clean = !inEncodeSet(input[i], fragmentSet);
            }
            if (log != null) {
              noteUnits(log, input, pointer, input.end);
            }
            fragmentText = encodedSlice(input, pointer, input.end, fragmentSet, clean);
            pointer = input.prev(input.end);
          }
        }

After each run, the pointer moves to the next code point, unless the
state asked to see this one again, and the parser stops after the end.

        if (!again) {
          if (!input.hasIndex(pointer)) {
            break;
          }
          pointer = input.next(pointer);
        }
      }
      if (url.hasOpaquePath) {
        url.opaquePath = opaqueText;
      }
      if (inQuery) {
        url.query = queryText;
      }
      if (inFragment) {
        url.fragment = fragmentText;
      }
      url
    }

The code point after `i`, or EOF, for the standard's "remaining starts
with" checks.

    let peek(input: String, i: StringIndex): Int {
      let next = input.next(i);
      if (input.hasIndex(i) && input.hasIndex(next)) { input[next] } else { eof }
    }

Where parts start, for the log's spans: the path where a path state
first runs, and the query and fragment after their `?` and `#`, where
their states first run. A path that starts after a lone slash, as in
`/x` against a base, starts at the slash (`back` 1). A host or port's
span ends at `at`, and its errors cover it.

    let noteSpanStarts(log: ErrorLog, state: Int, input: String, at: StringIndex): Void {
      if (
        log.pathStart < 0 &&
          (state == pathStartState || state == pathState || state == opaquePathState)
      ) {
        log.pathStart = countAt(log, input, at);
      } else if (log.queryStart < 0 && state == queryState) {
        log.queryStart = countAt(log, input, at);
      } else if (log.fragmentStart < 0 && state == fragmentState) {
        log.fragmentStart = countAt(log, input, at);
      }
    }

    let notePathStart(log: ErrorLog?, input: String, at: StringIndex, back: Int): Void {
      if (log != null) {
        if (log.pathStart < 0) {
          log.pathStart = countAt(log, input, at) - back;
        }
      }
    }

    let noteHostSpan(log: ErrorLog?, input: String, at: StringIndex, count: Int): Void {
      if (log != null) {
        log.hostEnd = countAt(log, input, at);
        log.hostStart = log.hostEnd - count;
        log.spanEnd = log.hostEnd;
      }
    }

Whether a URL [includes
credentials](https://url.spec.whatwg.org/#include-credentials).

    let hasCredentials(url: UrlRecord): Boolean {
      !url.username.isEmpty || !url.password.isEmpty
    }

Code points a scheme can hold, and those that end an authority, a host,
a port, or a path segment.

    let isSchemeCode(c: Int): Boolean {
      isAsciiAlpha(c) || isDigit(c) || c == char'+' || c == char'-' || c == char'.'
    }

    let isAuthorityEnd(c: Int, special: Boolean): Boolean {
      c == char'/' || c == char'?' || c == char'#' || (special && c == backslash)
    }

Where a run from `i` ends: at the end of the input, an authority's end,
or `stop` (EOF for none).

    let runEnd(input: String, i: StringIndex, special: Boolean, stop: Int): StringIndex {
      var end = input.next(i);
      var more = input.hasIndex(end);
      while (more) {
        let c = input[end];
        more = c != stop && !isAuthorityEnd(c, special);
        if (more) {
          end = input.next(end);
          more = input.hasIndex(end);
        }
      }
      end
    }

Where an opaque path's run from `i` ends: at the end, `?`, `#`, or a
space, which needs a look ahead.

    let opaqueRunEnd(input: String, i: StringIndex): StringIndex {
      var end = input.next(i);
      var more = input.hasIndex(end);
      while (more) {
        let c = input[end];
        more = c != char'?' && c != char'#' && c != char' ';
        if (more) {
          end = input.next(end);
          more = input.hasIndex(end);
        }
      }
      end
    }

A run of `input` from `start` to `end`, percent-encoded with `set`, or
just the run if it's `clean`, needing no escapes, as most are.

    let encodedSlice(
      input: String, start: StringIndex, end: StringIndex, set: Int, clean: Boolean,
    ): String {
      if (clean) { input.slice(start, end) } else { percentEncodeSlice(input, start, end, set) }
    }

## Serializing

The [URL path serializer](https://url.spec.whatwg.org/#url-path-serializer):
an opaque path as it is, or else `/` before each segment.

    let serializePath(url: UrlRecord): String {
      if (url.hasOpaquePath) {
        url.opaquePath
      } else if (url.path.isEmpty) {
        ""
      } else {
        "/${url.path.join("/") { segment => segment }}"
      }
    }

The [URL serializer](https://url.spec.whatwg.org/#concept-url-serializer).
Credentials, if any, go before the host, and a port after it. Without a
host, a path starting with an empty segment gets `/.` in front, as in
`web+demo:/.//not-a-host/`, so that it can't read back as a host.

    let serializeUrl(
      scheme: String, username: String, password: String, host: String?, port: Int,
      path: String, query: String?, fragment: String?,
    ): String {
      let authority = if (host != null) {
        let credentials = if (password != "") {
          "${username}:${password}@"
        } else if (username != "") {
          "${username}@"
        } else {
          ""
        };
        let portText = if (port >= 0) { ":${port.toString()}" } else { "" };
        "//${credentials}${host}${portText}"
      } else if (path.hasAtLeast(String.begin, path.end, 2) && startsWithTwoSlashes(path)) {
        "/."
      } else {
        ""
      };
      let search = if (query != null) { "?${query}" } else { "" };
      let hash = if (fragment != null) { "#${fragment}" } else { "" };
      "${scheme}:${authority}${path}${search}${hash}"
    }

A path serialized as `//…` has an empty first segment and more after
it. (An opaque path never starts with `/`.)

    let startsWithTwoSlashes(path: String): Boolean {
      let first = String.begin;
      path.hasIndex(first) && path[first] == char'/' &&
        path.hasIndex(path.next(first)) && path[path.next(first)] == char'/'
    }

The [origin](https://url.spec.whatwg.org/#concept-url-origin) of a URL,
[serialized](https://url.spec.whatwg.org/#ascii-serialization-of-an-origin).
`file` URLs' origins are left to implementations, and opaque here, as
in most browsers.

    let originOf(scheme: String, host: String?, port: Int, path: String): String {
      if (scheme == "blob") {
        let inner: UrlRecord? = parseRecord(path, noBase, false, null) orelse null;
        if (inner == null) {
          return "null";
        } else if (inner.scheme == "http" || inner.scheme == "https") {
          return originOf(inner.scheme, inner.host, inner.port, serializePath(inner));
        }
        return "null";
      }
      if (
        scheme != "http" && scheme != "https" && scheme != "ws" && scheme != "wss" &&
        scheme != "ftp"
      ) {
        return "null";
      }
      if (host == null) {
        "null"
      } else if (port >= 0) {
        "${scheme}://${host}:${port.toString()}"
      } else {
        "${scheme}://${host}"
      }
    }

## Tests

The README's examples.

    test("README examples") {
      let url = parseUrl("https://user@EXAMPLE.com:443/a/../b?q=1#top") orelse panic();
      assert(url.href == "https://user@example.com/b?q=1#top");
      assert(url.hostname == "example.com");
      assert(url.pathname == "/b");
      let relative = parseUrl("../c", "https://example.com/a/b") orelse panic();
      assert(relative.href == "https://example.com/c");
      assert(Url.parse("https://exa mple.com") == null);
      assert(!Url.canParse("https://exa mple.com"));
      let bad: Url? = parseUrl("https://exa mple.com") orelse null;
      assert(bad == null);
      let check = checkUrl("https://exa mple.com") orelse panic();
      assert(check.url == null);
      assert(check.errors.join(", ") { e => e.toString() } == "domain-invalid-code-point at 8");
      let base = parseUrl("https://example.com/a/b") orelse panic();
      assert((base.resolve("../c") orelse panic()).href == "https://example.com/c");
      assert(url.scheme == "https");
      assert(url.portNumber == null);
      assert(url.hostKind == HostKind.domain);
      assert((parseUrl("http://0x7f.1/") orelse panic()).hostKind == HostKind.ipv4);
      assert(url.sameOrigin(base));
      let host = parseHost("0x7f.1") orelse panic();
      assert(host.kind == HostKind.ipv4 && host.serialized == "127.0.0.1");
      let international = parseUrl("https://Bücher.example") orelse panic();
      assert(international.hostname == "xn--bcher-kva.example");
      assert(domainToUnicode("xn--bcher-kva.example") == "bücher.example");
      let moved = url.withHost("example.org:8443").withPathname("/c d").withHash("");
      assert(moved.href == "https://user@example.org:8443/c%20d?q=1");
      assert(url.href == "https://user@example.com/b?q=1#top");
      let params = moved.searchParams;
      params.append("lang", "en US");
      params.set("q", "2");
      assert(moved.withSearchParams(params).search == "?q=2&lang=en+US");
      assert(url.withPort("x").port == "" && url.withProtocol("mailto").scheme == "https");
    }

Parsing, nullable parsing, and checking agree; a base that doesn't
parse fails each, and bubbles from `checkUrl`.

    test("parse names") {
      assert(Url.canParse("https://example.com/"));
      assert(Url.canParse("a", "https://example.com/"));
      assert(!Url.canParse("a"));
      assert(!Url.canParse("a", "not a base"));
      assert(Url.parse("a", "not a base") == null);
      let parsed = Url.parse("a", "https://example.com/b/c");
      assert(parsed != null && parsed.href == "https://example.com/b/a");
      let rejected: UrlCheck? = checkUrl("a", "not a base") orelse null;
      assert(rejected == null) { "checkUrl bubbles for a base that doesn't parse" };
    }

Resolving against a parsed URL gives what parsing against its `href`
does, for every kind of path and base.

    test("resolve") {
      let cases = [
        "https://example.com/docs/guide/intro.html", "setup.html",
        "https://example.com/docs/guide/intro.html", "../api/?x#y",
        "https://example.com/docs/guide/intro.html", "?page=2",
        "https://example.com/docs/guide/intro.html", "#top",
        "https://example.com/docs/guide/intro.html", "//cdn.example/lib.js",
        "https://example.com/docs/guide/intro.html", "/\\evil.example",
        "https://example.com", "a",
        "https://example.com/?q#f", "",
        "mailto:someone@example.com", "#x",
        "web+demo:/.//not-a-host/", "x",
        "web+demo:/", "..//x",
        "file:///C:/a/b", "/c",
        "file:///C:/a/b", "..\\..\\..\\d",
        "file://host/share/a", "b",
        "foo://h/a/b?q", "c",
        "foo:", "x",
      ];
      for (var k = 0; k < cases.length; k += 2) {
        let base = parseUrl(cases[k]) orelse panic();
        let expected: Url? = parseUrl(cases[k + 1], cases[k]) orelse null;
        let actual = base.tryResolve(cases[k + 1]);
        if (expected == null) {
          assert(actual == null) { "${cases[k + 1]} against ${cases[k]} must fail" };
        } else {
          assert(actual != null && actual == expected) {
            "${cases[k + 1]} against ${cases[k]} must give ${expected.href}"
          };
        }
      }
      let mailto = parseUrl("mailto:someone@example.com") orelse panic();
      assert(mailto.tryResolve("x") == null);
    }

The typed parts, origins, equality, and strings.

    test("typed parts") {
      let kinds = [
        "https://example.com/", "domain", "https://127.1/", "ipv4", "https://[::1]/", "ipv6",
        "foo://host/", "opaque", "file:///etc", "empty", "foo:///x", "empty",
        "mailto:a@b", "none", "foo://[::1]/", "ipv6", "https://a1/", "domain",
        "https://1.2.3.4./", "ipv4", "https://xn--bcher-kva.example/", "domain",
      ];
      for (var k = 0; k < kinds.length; k += 2) {
        let url = parseUrl(kinds[k]) orelse panic();
        let kind = url.hostKind;
        let name = if (kind == null) { "none" } else { kind.toString() };
        assert(name == kinds[k + 1]) { "${kinds[k]}: ${name}" };
      }
      let url = parseUrl("HTTPS://example.com:8080/") orelse panic();
      assert(url.scheme == "https" && url.protocol == "https:");
      assert(url.portNumber == 8080 && url.port == "8080");
      assert((parseUrl("https://example.com:443/") orelse panic()).portNumber == null);
      assert((parseUrl("foo://h:0/") orelse panic()).portNumber == 0);
      assert(url.withPortNumber(9000).port == "9000" && url.withPortNumber(443).port == "");
      assert(url.withPortNumber(null).href == "https://example.com/");
      assert(url.withPortNumber(65536).port == "8080" && url.withPortNumber(-1).port == "8080");
      assert((parseUrl("file:///a") orelse panic()).withPortNumber(80).port == "");
      let same(a: String, b: String): Boolean {
        (parseUrl(a) orelse panic()).sameOrigin(parseUrl(b) orelse panic())
      }
      assert(same("https://example.com/a", "https://EXAMPLE.com:443/b?c"));
      assert(!same("https://example.com/", "http://example.com/"));
      assert(!same("https://example.com/", "https://example.com:8443/"));
      assert(!same("https://example.com/", "https://www.example.com/"));
      assert(same("blob:https://example.com/uuid", "https://example.com/"));
      assert(!same("data:text/plain,a", "data:text/plain,a"));
      assert(!same("file:///a", "file:///a"));
      let data = parseUrl("data:,a") orelse panic();
      assert(!data.sameOrigin(data));
      let a = parseUrl("HTTP://Example.com/./a") orelse panic();
      let b = parseUrl("http://example.com/a") orelse panic();
      assert(a == b);
      assert(a != (parseUrl("http://example.com/a#") orelse panic()));
      assert(a.toString() == "http://example.com/a");
    }

Checking hosts, unlike domain to ASCII, which passes all of these.

    test("parseHost") {
      let good = [
        "Example.COM", "domain", "example.com",
        "bücher.example", "domain", "xn--bcher-kva.example",
        "%62%C3%BCcher.example", "domain", "xn--bcher-kva.example",
        "0x7f.1", "ipv4", "127.0.0.1",
        "2130706433", "ipv4", "127.0.0.1",
        "[0:0::1]", "ipv6", "[::1]",
        "example.com.", "domain", "example.com.",
      ];
      for (var k = 0; k < good.length; k += 3) {
        let host = parseHost(good[k]) orelse panic();
        assert(host.kind.toString() == good[k + 1] && host.serialized == good[k + 2]) {
          "${good[k]}: ${host.kind.toString()} ${host.toString()}"
        };
      }
      for (let input of ["", "exa mple.com", "example.com:80", "1.2.3.256", "[::1", "::1",
        "a/b", "xn--tešla", "user@example.com", "%zz"]) {
        let host: Host? = parseHost(input) orelse null;
        assert(host == null) { "${input} must fail" };
      }
    }

Validation errors, each checked by hand against the standard: the
input, the base or empty for none, the href or empty where parsing
fails, and the errors.

    test("validation errors") {
      let cases = [
        "https://example.com/", "", "https://example.com/", "",
        " https://example.com/ ", "", "https://example.com/", "invalid-URL-unit at 0",
        "https://exa\tmple.com/", "", "https://example.com/", "invalid-URL-unit at 11",
        " https://exa\tmple.com/a b", "", "https://example.com/a%20b",
        "invalid-URL-unit at 0, invalid-URL-unit at 12, invalid-URL-unit at 23",
        "https:example.com", "", "https://example.com/",
        "special-scheme-missing-following-solidus at 6",
        "https:///x", "", "https://x/", "special-scheme-missing-following-solidus at 8",
        "https:\\\\example.com\\path", "", "https://example.com/path",
        "special-scheme-missing-following-solidus at 6, special-scheme-missing-following-solidus at 6, special-scheme-missing-following-solidus at 7, invalid-reverse-solidus at 19",
        "https://example.com\\a", "", "https://example.com/a", "invalid-reverse-solidus at 19",
        "\\x", "https://example.com/a", "https://example.com/x", "invalid-reverse-solidus at 0",
        "http://user:pa@ss@host/", "", "http://user:pa%40ss@host/",
        "invalid-credentials at 14, invalid-credentials at 17",
        "http://a:b@c:1/", "", "http://a:b@c:1/", "invalid-credentials at 10",
        "https://user@/x", "", "", "invalid-credentials at 12, host-missing at 13",
        "https://", "", "", "host-missing at 8",
        "a", "", "", "missing-scheme-non-relative-URL at 0",
        "x", "mailto:a@b", "", "missing-scheme-non-relative-URL at 0",
        "http://example.com:99999/", "", "", "port-out-of-range at 19",
        "http://example.com:8a/", "", "", "port-invalid at 20",
        "http://exa mple.com/", "", "", "domain-invalid-code-point at 7",
        "https://xn--tešla/", "", "", "domain-to-ASCII at 8",
        "http://1.2.3.256/", "", "", "IPv4-out-of-range-part at 7",
        "http://0x7f.1/", "", "http://127.0.0.1/", "IPv4-non-decimal-part at 7",
        "http://1.2.3.4./", "", "http://1.2.3.4/", "IPv4-empty-part at 7",
        "http://1.2.3.4.5/", "", "", "IPv4-too-many-parts at 7",
        "http://1.0x.3.4/", "", "http://1.0.3.4/", "IPv4-non-decimal-part at 7",
        "http://1.x.3/", "", "", "IPv4-non-numeric-part at 7",
        "http://[::1/", "", "", "IPv6-unclosed at 7",
        "http://[1:2:3:4:5:6:7:8:9]/", "", "", "IPv6-too-many-pieces at 7",
        "http://[1::2::3]/", "", "", "IPv6-multiple-compression at 7",
        "http://[:1]/", "", "", "IPv6-invalid-compression at 7",
        "http://[1:2]/", "", "", "IPv6-too-few-pieces at 7",
        "http://[::g]/", "", "", "IPv6-invalid-code-point at 7",
        "http://[::1.2.3]/", "", "", "IPv4-in-IPv6-too-few-parts at 7",
        "http://[::1.2.3.256]/", "", "", "IPv4-in-IPv6-out-of-range-part at 7",
        "http://[::01.2.3.4]/", "", "", "IPv4-in-IPv6-invalid-code-point at 7",
        "http://[1:2:3:4:5:6:7:1.2.3.4]/", "", "", "IPv4-in-IPv6-too-many-pieces at 7",
        "foo://exa mple/", "", "", "host-invalid-code-point at 6",
        "foo://ex%zzample/", "", "foo://ex%zzample/", "invalid-URL-unit at 8",
        "foo://ex{ample/", "", "foo://ex{ample/", "invalid-URL-unit at 8",
        "https://example.com/a b", "", "https://example.com/a%20b", "invalid-URL-unit at 21",
        "https://example.com/%zz", "", "https://example.com/%zz", "invalid-URL-unit at 20",
        "https://example.com/%4", "", "https://example.com/%4", "invalid-URL-unit at 20",
        "https://example.com/%4a", "", "https://example.com/%4a", "",
        "https://example.com/?q=a|b#x^y", "", "https://example.com/?q=a|b#x^y",
        "invalid-URL-unit at 24, invalid-URL-unit at 28",
        "https://example.com#a#b", "", "https://example.com/#a#b", "invalid-URL-unit at 21",
        "mailto:a<b", "", "mailto:a<b", "invalid-URL-unit at 8",
        "file:c:/x", "", "file:///c:/x", "special-scheme-missing-following-solidus at 4",
        "file://C:/x", "", "file:///C:/x", "file-invalid-Windows-drive-letter-host at 7",
        "c|/x", "file:///a/b", "file:///c:/x",
        "file-invalid-Windows-drive-letter at 0, invalid-URL-unit at 1",
      ];
      for (var k = 0; k < cases.length; k += 4) {
        let input = cases[k];
        let base: String? = if (cases[k + 1] == "") { null } else { cases[k + 1] };
        let check = checkUrl(input, base) orelse panic();
        let url = check.url;
        let href = if (url == null) { "" } else { url.href };
        let errors = check.errors.join(", ") { e => e.toString() };
        assert(href == cases[k + 2] && errors == cases[k + 3]) {
          "${input}: ${href}, with ${errors}"
        };
      }
    }
