# URLs

Parsing and serializing URLs, following the WHATWG [URL
Standard](https://url.spec.whatwg.org/)'s [URL
parsing](https://url.spec.whatwg.org/#url-parsing) and [URL
serializing](https://url.spec.whatwg.org/#url-serializing) sections,
step by step, with their names, so each part can be checked against the
text. Hosts are in [host](host.temper.md), and percent-encoding in
[percent](percent.temper.md).

## The API

Parses `input`, against `base` if given, as the standard's [`URL`
constructor](https://url.spec.whatwg.org/#dom-url-url) does: it bubbles
where the standard says parsing fails, including when `base` doesn't
parse.

    export let parseUrl(input: String, base: String? = null): Url throws Bubble {
      Url.parse(input, base)
    }

A parsed URL, with the standard's [`URL`
getters](https://url.spec.whatwg.org/#urlutils-members), each a string,
as in JavaScript. It's immutable for now.

    export class Url {
      private scheme: String;
      private usernameValue: String;
      private passwordValue: String;
      private hostValue: String?;
      private portValue: Int;
      private pathValue: String;
      private query: String?;
      private fragment: String?;

The constructor is private, so every `Url` is a parsed one. Its parts
are as the [URL record](https://url.spec.whatwg.org/#concept-url) has
them, with the host and path already serialized, and -1 for no port.
They're plain strings and numbers, since Temper's C# backend makes
private constructors public, and C# then rejects internal types in their
signatures.

      private constructor(
        scheme: String, username: String, password: String, host: String?,
        port: Int, path: String, query: String?, fragment: String?,
      ) {
        this.scheme = scheme;
        this.usernameValue = username;
        this.passwordValue = password;
        this.hostValue = host;
        this.portValue = port;
        this.pathValue = path;
        this.query = query;
        this.fragment = fragment;
      }

The same as `parseUrl`, here since only the class can call its
constructor, and as JavaScript's `URL.parse`.

      public static parse(input: String, base: String? = null): Url throws Bubble {
        let baseRecord = if (base == null) { noBase } else { parseRecord(base, noBase, false) };
        let record = parseRecord(input, baseRecord, base != null);
        new Url(
          record.scheme, record.username, record.password, record.host, record.port,
          serializePath(record), record.query, record.fragment,
        )
      }

The [href](https://url.spec.whatwg.org/#dom-url-href): the whole URL,
serialized.

      public get href(): String {
        serializeUrl(
          scheme, usernameValue, passwordValue, hostValue, portValue, pathValue, query,
          fragment,
        )
      }

The [origin](https://url.spec.whatwg.org/#dom-url-origin), serialized:
`scheme://host` with any port, for `http`, `https`, `ws`, `wss`, and
`ftp` URLs, or `null` for the rest, whose origins are opaque. A `blob:`
URL has the origin of the URL in its path, if that's `http` or `https`.

      public get origin(): String { originOf(scheme, hostValue, portValue, pathValue) }

The [protocol](https://url.spec.whatwg.org/#dom-url-protocol): the
scheme and a colon, as `https:`.

      public get protocol(): String { "${scheme}:" }

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

The [port](https://url.spec.whatwg.org/#dom-url-port), empty if it's the
scheme's default, such as 443 for `https`.

      public get port(): String { if (portValue < 0) { "" } else { portValue.toString() } }

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

      public toString(): String { href }
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
        url.scheme == "file" && path.length == 1 && isWindowsDriveLetter(path[0], true)
      ) {
        return;
      }
      if (path.length > 0) {
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
and newline, wherever it is. (State overrides, which the standard's
setters use, wait for step 3.)

    let cleanInput(input: String): String {
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

    let eof = -1;
    let backslash = 0x5C;

Parses `input` against `base`, if `hasBase`.

    let parseRecord(rawInput: String, base: UrlRecord, hasBase: Boolean): UrlRecord throws Bubble {
      let input = cleanInput(rawInput);
      let url = new UrlRecord();
      var special = false;
      var state = schemeStartState;

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

The opaque path, query, and fragment are built here, then stored at the
end.

      let queryBuffer = new StringBuilder();
      var inQuery = false;
      let fragmentBuffer = new StringBuilder();
      var inFragment = false;
      let opaqueBuffer = new StringBuilder();

The pointer, and whether the state just run asked to see the same code
point again. The standard says "decrease pointer by 1" and then always
increases it, which here is `again`.

      var pointer = String.begin;
      while (true) {
        let c = if (input.hasIndex(pointer)) { input[pointer] } else { eof };
        var again = false;

### Scheme Start State

        if (state == schemeStartState) {
          if (isAsciiAlpha(c)) {
            appendCode(buffer, c | 0x20);
            state = schemeState;
          } else {
            state = noSchemeState;
            again = true;
          }

### Scheme State

A scheme is a letter followed by letters, digits, `+`, `-`, and `.`,
lowercased, up to a `:`. Without the `:`, there's no scheme after all,
so it starts over in the no scheme state.

        } else if (state == schemeState) {
          if (
            isAsciiAlpha(c) || isDigit(c) || c == char'+' || c == char'-' || c == char'.'
          ) {
            appendCode(buffer, if (isAsciiAlpha(c)) { c | 0x20 } else { c });
          } else if (c == char':') {
            url.scheme = buffer.toString();
            special = isSpecialScheme(url.scheme);
            buffer.clear();
            if (url.scheme == "file") {
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
          } else {
            buffer.clear();
            state = noSchemeState;
            pointer = String.begin;
            again = true;
          }

### No Scheme State

Without a scheme, the input is relative to the base, which must have
one, and not an opaque path, unless the input is only a fragment.

        } else if (state == noSchemeState) {
          if (!hasBase || (base.hasOpaquePath && c != char'#')) {
            bubble();
          } else if (base.hasOpaquePath && c == char'#') {
            url.scheme = base.scheme;
            special = isSpecialScheme(url.scheme);
            url.hasOpaquePath = true;
            opaqueBuffer.append(base.opaquePath);
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
            state = relativeState;
            again = true;
          }

### Path or Authority State

        } else if (state == pathOrAuthorityState) {
          if (c == char'/') {
            state = authorityState;
          } else {
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
            state = specialAuthorityIgnoreSlashesState;
          } else if (c == char'/') {
            state = authorityState;
          } else {
            url.username = base.username;
            url.password = base.password;
            url.host = base.host;
            url.port = base.port;
            state = pathState;
            again = true;
          }

### Special Authority Slashes State

        } else if (state == specialAuthoritySlashesState) {
          if (c == char'/' && peek(input, pointer) == char'/') {
            state = specialAuthorityIgnoreSlashesState;
            pointer = input.next(pointer);
          } else {
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
            let credentials = new StringBuilder();
            if (atSignSeen) {
              credentials.append("%40");
            }
            atSignSeen = true;
            for (var i = authorityStart; i < pointer; i = input.next(i)) {
              let code = input[i];
              if (code == char':' && !passwordTokenSeen) {
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
          } else if (
            c == eof || c == char'/' || c == char'?' || c == char'#' ||
            (special && c == backslash)
          ) {
            if (atSignSeen && authorityStart == pointer) {
              bubble();
            }
            pointer = authorityStart;
            state = hostState;
            again = true;
          }

### Host State and Hostname State

The host ends at a `:` outside brackets, which starts the port, or at
the path, query, or fragment. Special URLs need a host. (The hostname
state differs only with a state override.)

        } else if (state == hostState) {
          if (c == char':' && !insideBrackets) {
            if (bufferCount == 0) {
              bubble();
            }
            url.host = parseHost(buffer.toString(), !special);
            buffer.clear();
            bufferCount = 0;
            state = portState;
          } else if (
            c == eof || c == char'/' || c == char'?' || c == char'#' ||
            (special && c == backslash)
          ) {
            if (special && bufferCount == 0) {
              bubble();
            }
            url.host = parseHost(buffer.toString(), !special);
            buffer.clear();
            bufferCount = 0;
            state = pathStartState;
            again = true;
          } else {
            if (c == char'[') {
              insideBrackets = true;
            } else if (c == char']') {
              insideBrackets = false;
            }
            appendCode(buffer, c);
            bufferCount += 1;
          }

### Port State

A port is decimal digits, at most 65535, and none at all if it's the
scheme's default.

        } else if (state == portState) {
          if (isDigit(c)) {
            portValue = portValue * 10 + c - char'0';
            if (portValue > 65535) {
              bubble();
            }
            bufferCount += 1;
          } else if (
            c == eof || c == char'/' || c == char'?' || c == char'#' ||
            (special && c == backslash)
          ) {
            if (bufferCount != 0) {
              url.port = if (portValue == defaultPort(url.scheme)) { -1 } else { portValue };
              portValue = 0;
              bufferCount = 0;
            }
            state = pathStartState;
            again = true;
          } else {
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
            state = pathState;
            again = true;
          }

### File Host State

A drive letter where the host would be, as in `file://C:/x`, is the
start of the path instead, and `localhost` is the same as no host.

        } else if (state == fileHostState) {
          if (c == eof || c == char'/' || c == backslash || c == char'?' || c == char'#') {
            again = true;
            let text = buffer.toString();
            if (isWindowsDriveLetter(text, false)) {
              state = pathState;
            } else if (bufferCount == 0) {
              url.host = "";
              state = pathStartState;
            } else {
              let host = parseHost(text, !special);
              url.host = if (host == "localhost") { "" } else { host };
              buffer.clear();
              bufferCount = 0;
              state = pathStartState;
            }
          } else {
            appendCode(buffer, c);
            bufferCount += 1;
          }

### Path Start State

        } else if (state == pathStartState) {
          if (special) {
            state = pathState;
            if (c != char'/' && c != backslash) {
              again = true;
            }
          } else if (c == char'?') {
            inQuery = true;
            state = queryState;
          } else if (c == char'#') {
            inFragment = true;
            state = fragmentState;
          } else if (c != eof) {
            state = pathState;
            if (c != char'/') {
              again = true;
            }
          }

### Path State

Each segment is percent-encoded with the path set. At its end, `..`
removes the segment before, `.` is dropped, and a `file` URL's first
segment, if a drive letter, is normalized to use `:`.

        } else if (state == pathState) {
          let slash = c == char'/' || (special && c == backslash);
          if (slash || c == eof || c == char'?' || c == char'#') {
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
            percentEncodeOnto(buffer, c, pathSet);
            bufferCount += 1;
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
            if (next == char'?' || next == char'#') {
              opaqueBuffer.append("%20");
            } else {
              opaqueBuffer.append(" ");
            }
          } else if (c != eof) {
            percentEncodeOnto(opaqueBuffer, c, c0ControlSet);
          }

### Query State

A query is percent-encoded with the query set, or the special-query set
for special URLs, which also escapes `'`. (Only UTF-8 is supported, as
the standard's `URL` API uses.)

        } else if (state == queryState) {
          if (c == char'#') {
            inFragment = true;
            state = fragmentState;
          } else if (c != eof) {
            percentEncodeOnto(queryBuffer, c, if (special) { specialQuerySet } else { querySet });
          }

### Fragment State

        } else {
          if (c != eof) {
            percentEncodeOnto(fragmentBuffer, c, fragmentSet);
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
        url.opaquePath = opaqueBuffer.toString();
      }
      if (inQuery) {
        url.query = queryBuffer.toString();
      }
      if (inFragment) {
        url.fragment = fragmentBuffer.toString();
      }
      url
    }

The code point after `i`, or EOF, for the standard's "remaining starts
with" checks.

    let peek(input: String, i: StringIndex): Int {
      if (!input.hasIndex(i)) {
        return eof;
      }
      let next = input.next(i);
      if (input.hasIndex(next)) { input[next] } else { eof }
    }

## Serializing

The [URL path serializer](https://url.spec.whatwg.org/#url-path-serializer):
an opaque path as it is, or else `/` before each segment.

    let serializePath(url: UrlRecord): String {
      if (url.hasOpaquePath) {
        return url.opaquePath;
      }
      let out = new StringBuilder();
      let path = url.path;
      for (var k = 0; k < path.length; k += 1) {
        out.append("/");
        out.append(path[k]);
      }
      out.toString()
    }

The [URL serializer](https://url.spec.whatwg.org/#concept-url-serializer).
Credentials, if any, go before the host, and a port after it. Without a
host, a path starting with an empty segment gets `/.` in front, as in
`web+demo:/.//not-a-host/`, so that it can't read back as a host.

    let serializeUrl(
      scheme: String, username: String, password: String, host: String?, port: Int,
      path: String, query: String?, fragment: String?,
    ): String {
      let out = new StringBuilder();
      out.append(scheme);
      out.append(":");
      if (host != null) {
        out.append("//");
        if (username != "" || password != "") {
          out.append(username);
          if (password != "") {
            out.append(":");
            out.append(password);
          }
          out.append("@");
        }
        out.append(host);
        if (port >= 0) {
          out.append(":");
          out.append(port.toString());
        }
      } else if (path.hasAtLeast(String.begin, path.end, 2) && startsWithTwoSlashes(path)) {
        out.append("/.");
      }
      out.append(path);
      if (query != null) {
        out.append("?");
        out.append(query);
      }
      if (fragment != null) {
        out.append("#");
        out.append(fragment);
      }
      out.toString()
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
        let inner: UrlRecord? = parseRecord(path, noBase, false) orelse null;
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
      let bad: Url? = parseUrl("https://exa mple.com") orelse null;
      assert(bad == null);
    }
