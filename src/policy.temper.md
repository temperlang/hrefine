# Policies

The checks people need before trusting a URL, and often get wrong by
hand: which schemes, no credentials, no IP addresses or no private and
loopback ones (against server-side request forgery, SSRF), a host
allowlist, the same origin, redirect targets that stay on the site, a
maximum length, and strict parsing. Each works on the parsed URL, never
on the input string, so `127.1`, `0x7f.1`, `[::ffff:127.0.0.1]`,
`good.example@evil.example`, and backslashes and tabs can't slip past.

A `UrlPolicy` is built once, from `UrlPolicy.any`, which every URL that
parses passes, adding one rule per `with` method, and applied to many
URLs. It's immutable, as `Url` is, so each `with` method gives a new
policy, and a policy can be shared between threads:

For a URL your server fetches on someone's behalf, start from
`UrlPolicy.fetch`, which has the usual rules already, and add an
allowlist if you have one:

```temper inert
let policy = UrlPolicy.fetch.withHosts(["example.com"], true);
let result = policy.check(input);
if (result.url != null) { fetchUrl(result.url.href) } else { log(result.toString()) }
```

## Rules

    export class UrlPolicy {
      private strict: Boolean;
      private maxLength: Int;
      private base: Url?;
      private schemes: List<String>?;
      private credentials: Boolean;
      private ipHosts: Boolean;
      private specialHosts: Boolean;
      private hosts: List<String>?;
      private subdomains: Boolean;
      private origin: Url?;
      private pathOnly: Boolean;

The constructor is private, so policies start from `UrlPolicy.any`. Its
parameters are plain types, since Temper's C# backend makes private
constructors public.

      private constructor(
        strict: Boolean, maxLength: Int, base: Url?, schemes: List<String>?,
        credentials: Boolean, ipHosts: Boolean, specialHosts: Boolean, hosts: List<String>?,
        subdomains: Boolean, origin: Url?, pathOnly: Boolean,
      ) {
        this.strict = strict;
        this.maxLength = maxLength;
        this.base = base;
        this.schemes = schemes;
        this.credentials = credentials;
        this.ipHosts = ipHosts;
        this.specialHosts = specialHosts;
        this.hosts = hosts;
        this.subdomains = subdomains;
        this.origin = origin;
        this.pathOnly = pathOnly;
      }

No rules: every URL that parses passes. The blank slate, for building
a policy rule by rule.

      public static any: UrlPolicy = new UrlPolicy(
        false, -1, null, null, true, true, true, null, false, null, false,
      );

For a URL a server fetches on someone's behalf, as for webhooks, link
previews, image proxies, and imports, the classic case for server-side
request forgery: `https` only, no credentials, no special hosts (private,
loopback, and the rest, however they're written), strict mode, and at
most 8,192 code points, the request-line limit of common servers, so
longer URLs would fail there anyway. Named for that use, as the Fetch
standard names getting a resource, not as safe for every use: add an
allowlist with `withHosts` where you have one, and still check the
address your client connects to. It's `UrlPolicy.any` with those
rules, so any can be changed, such as `withSchemes(["http", "https"])`.
It refuses credentials in the URL, but can't tell which query
parameters or fragments hold secrets (`?token=`), so don't log URLs
that may carry tokens there.

      public static fetch: UrlPolicy = new UrlPolicy(
        true, 8192, null, ["https"], false, true, false, null, false, null, false,
      );

**Strict:** with `true`, the parse must note no validation error that
strict mode counts (`UrlCheck.strictErrors`): no backslashes, tabs,
newlines, or leading or trailing spaces and controls, no IPv4 address
but as four decimal numbers, no escapes in a domain, no missing `//`,
no `@` without a host after it, and the rest. See `checkUrl`.

      public withStrict(strict: Boolean): UrlPolicy {
        new UrlPolicy(
          strict, maxLength, base, schemes, credentials, ipHosts, specialHosts, hosts, subdomains,
          origin, pathOnly,
        )
      }

**Maximum length,** in code points, of both the input, checked before
parsing it, and `hrefWithCredentials`, which escapes can make longer;
negative for no limit.

      public withMaxLength(maxLength: Int): UrlPolicy {
        new UrlPolicy(
          strict, maxLength, base, schemes, credentials, ipHosts, specialHosts, hosts, subdomains,
          origin, pathOnly,
        )
      }

**Base:** relative input resolves against `base`, as
`base.resolve(input)` does. Without one, relative input fails to parse.

      public withBase(base: Url): UrlPolicy {
        new UrlPolicy(
          strict, maxLength, base, schemes, credentials, ipHosts, specialHosts, hosts, subdomains,
          origin, pathOnly,
        )
      }

**Schemes:** the URL's scheme must be one of `schemes`, as `https` or
`https:`, in any case, such as `["http", "https"]`.

      public withSchemes(schemes: List<String>): UrlPolicy {
        let normalized = schemes.map { (scheme): String =>
          let lower = asciiLowercase(scheme);
          if (lower.hasIndex(String.begin) && lower[lower.prev(lower.end)] == char':') {
            lower.slice(String.begin, lower.prev(lower.end))
          } else {
            lower
          }
        };
        new UrlPolicy(
          strict, maxLength, base, normalized, credentials, ipHosts, specialHosts, hosts, subdomains,
          origin, pathOnly,
        )
      }

**Credentials:** with `false`, the URL may have no credentials: the
username and password written in the URL, as in
`https://user:pass@host/` (not cookies, headers, or tokens in the
query), or as in `https://good.example@evil.example/`, whose host is
`evil.example`.

      public withCredentials(allowed: Boolean): UrlPolicy {
        new UrlPolicy(
          strict, maxLength, base, schemes, allowed, ipHosts, specialHosts, hosts, subdomains,
          origin, pathOnly,
        )
      }

**IP hosts:** with `false`, the host may not be an IPv4 or IPv6
address, however it's written.

      public withIpHosts(allowed: Boolean): UrlPolicy {
        new UrlPolicy(
          strict, maxLength, base, schemes, credentials, allowed, specialHosts, hosts, subdomains,
          origin, pathOnly,
        )
      }

**Special hosts:** with `false`, the host may not be an address in the
[table](#special-addresses-and-names) below (private, loopback,
link-local, unspecified, multicast, IPv4-mapped, and other special
addresses), or a name there (`localhost` and the like), or empty, as a
`file:` URL's is. A URL with no host at all, such as `mailto:`, passes;
limit the schemes too.

It can't see where DNS sends a name: `evil.example` may resolve to
`127.0.0.1`. Against SSRF, check the address your client connects to as
well, or connect through a proxy that does.

      public withSpecialHosts(allowed: Boolean): UrlPolicy {
        new UrlPolicy(
          strict, maxLength, base, schemes, credentials, ipHosts, allowed, hosts, subdomains,
          origin, pathOnly,
        )
      }

**Host allowlist:** the host must be one of `hosts`, or with
`subdomains`, a domain under one of them. Each is read as a URL's host
is, with `parseHost`, so `Example.COM`, `bücher.example`, and `0x7f.1`
mean `example.com`, `xn--bcher-kva.example`, and `127.0.0.1`, and
compared with the URL's parsed host, ignoring a trailing dot on either.
An entry that isn't a host (such as `::1` without brackets) matches
nothing.

      public withHosts(hosts: List<String>, subdomains: Boolean): UrlPolicy {
        let parsed = new ListBuilder<String>();
        for (let entry of hosts) {
          let host: Host? = parseHost(entry) orelse null;
          if (host != null) {
            parsed.add(withoutTrailingDot(host.serialized));
          }
        }
        new UrlPolicy(
          strict, maxLength, base, schemes, credentials, ipHosts, specialHosts, parsed.toList(),
          subdomains, origin, pathOnly,
        )
      }

**Same origin:** the URL must have the same origin as `url`, by
`sameOrigin`, so the same scheme, host, and port.

      public withSameOrigin(url: Url): UrlPolicy {
        new UrlPolicy(
          strict, maxLength, base, schemes, credentials, ipHosts, specialHosts, hosts, subdomains,
          url, pathOnly,
        )
      }

**Path only:** with `true`, the input must name only a path, query, or
fragment, relative to the base, for redirect targets such as
`/account`: no scheme or host of its own. `//evil.example`,
`/\evil.example`, and `\\evil.example` name another host, as browsers
read them, so they fail, as do `//good.example/` and absolute URLs, even
to the base's own host. It needs a base, from `withBase`.

      public withPathOnly(pathOnly: Boolean): UrlPolicy {
        new UrlPolicy(
          strict, maxLength, base, schemes, credentials, ipHosts, specialHosts, hosts, subdomains,
          origin, pathOnly,
        )
      }

## Checking

Parses `input`, against the base if there is one, and checks each rule,
in this order: the input's length, parsing, strict mode,
`hrefWithCredentials`'s length, the scheme, credentials, IP hosts,
special hosts, the host allowlist, the same origin, and path only. It says which rule failed
first, or gives the URL. It never bubbles.

      public check(input: String): PolicyCheck {
        if (maxLength >= 0 && input.hasAtLeast(String.begin, input.end, maxLength + 1)) {
          refuse(PolicyRule.maxLength, "the input is longer than ${maxLength.toString()} code points")
        } else if (strict) {
          let b = base;
          // The base's full form, as resolve uses it, credentials and all.
          let baseText: String? = if (b == null) { null } else { b.hrefWithCredentials };
          let found: UrlCheck? = checkUrl(input, baseText) orelse null;
          let url: Url? = if (found == null) { null } else { found.url };
          let errors: List<ValidationError> = if (found == null) { [] } else { found.strictErrors };
          if (url == null) {
            refuse(PolicyRule.parse, "not a URL")
          } else if (!errors.isEmpty) {
            refuse(PolicyRule.strict, errors[0].toString())
          } else {
            checkParsed(input, url)
          }
        } else {
          let b = base;
          let url = if (b == null) { Url.parse(input) } else { b.tryResolve(input) };
          if (url == null) {
            refuse(PolicyRule.parse, "not a URL")
          } else {
            checkParsed(input, url)
          }
        }
      }

The rules after parsing. An opaque host, in a URL that isn't special,
is read as a special URL's host would be (`gopher://0x7f.1/` has
`127.0.0.1`), since other clients may read it so; one that can't be
read that way fails the host rules.

      private checkParsed(input: String, url: Url): PolicyCheck {
        // Credentials count toward the length, as a client sending them would.
        let href = url.hrefWithCredentials;
        var kind = url.hostKind;
        var host = url.hostname;
        var unreadable = false;
        if (kind == HostKind.opaque) {
          let parsed: Host? = parseHost(host) orelse null;
          if (parsed == null) {
            unreadable = true;
          } else {
            kind = parsed.kind;
            host = parsed.serialized;
          }
        }
        let allowedSchemes = schemes;
        let allowedHosts = hosts;
        let sameAs = origin;
        let special = if (specialHosts) { null } else { specialHostReason(kind, host, unreadable) };
        if (maxLength >= 0 && href.hasAtLeast(String.begin, href.end, maxLength + 1)) {
          refuse(PolicyRule.maxLength, "the URL is longer than ${maxLength.toString()} code points")
        } else if (allowedSchemes != null && !hasString(allowedSchemes, url.scheme)) {
          refuse(PolicyRule.scheme, schemeReason(url.scheme))
        } else if (!credentials && (url.username != "" || url.password != "")) {
          refuse(PolicyRule.credentials, credentialsReason(url))
        } else if (!ipHosts && (kind == HostKind.ipv4 || kind == HostKind.ipv6)) {
          refuse(PolicyRule.ipHost, "${host}, ${kindName(kind)}")
        } else if (special != null) {
          refuse(PolicyRule.specialHost, special)
        } else if (allowedHosts != null && (unreadable || !hostAllowed(kind, host, allowedHosts, subdomains))) {
          refuse(PolicyRule.host, if (url.hostname == "") { "no host" } else { url.hostname })
        } else if (sameAs != null && !url.sameOrigin(sameAs)) {
          refuse(PolicyRule.sameOrigin, url.origin)
        } else if (pathOnly && !isPathOnly(input, url, base)) {
          refuse(PolicyRule.pathOnly, if (base == null) { "no base" } else { "not just a path, query, or fragment" })
        } else {
          new PolicyCheck(url, null, "")
        }
      }
    }

    let refuse(rule: PolicyRule, reason: String): PolicyCheck { new PolicyCheck(null, rule, reason) }

    let kindName(kind: HostKind?): String { if (kind == null) { "no" } else { kind.name } }

Reasons go to logs, so they never echo credentials: they say which kind
was there, never what. A scheme is named only if it's well known, since
in `admin:hunter2@example.com`, which has no `//`, the scheme is
`admin`, a username.

    let credentialsReason(url: Url): String {
      if (url.username == "") {
        "a password"
      } else if (url.password == "") {
        "a username"
      } else {
        "a username and a password"
      }
    }

    let schemeReason(scheme: String): String {
      if (isSpecialScheme(scheme) || hasString(wellKnownSchemes, scheme)) {
        scheme
      } else {
        "one that isn't well known, so not named"
      }
    }

    let wellKnownSchemes: List<String> = [
      "about", "blob", "data", "dict", "gopher", "jar", "javascript", "ldap", "ldaps", "mailto",
      "netdoc", "sftp", "sms", "smb", "ssh", "tel", "telnet", "view-source",
    ];

    let hasString(list: List<String>, s: String): Boolean {
      var found = false;
      for (var k = 0; !found && k < list.length; k += 1) {
        found = list[k] == s;
      }
      found
    }

The host is an allowed one, or under an allowed domain, with
`subdomains`. Only a domain can be under another, so `1.example.com`
isn't, nor is `evilexample.com` under `example.com`.

    let hostAllowed(kind: HostKind?, host: String, allowed: List<String>, subdomains: Boolean): Boolean {
      let h = withoutTrailingDot(host);
      var found = false;
      if (kind != null && kind != HostKind.empty) {
        for (var k = 0; !found && k < allowed.length; k += 1) {
          let entry = allowed[k];
          found = h == entry || (
            subdomains && kind == HostKind.domain && kindOfHost(entry, true) == HostKind.domain &&
              endsWith(h, ".${entry}")
          );
        }
      }
      found
    }

Path only: the input resolves to the base's scheme, credentials, host,
and port, and against the base with another host, to that host, so it
names no host of its own. That holds for paths, queries, and fragments,
but not for `//host/` or an absolute URL, even to the base's own host.

    let isPathOnly(input: String, url: Url, base: Url?): Boolean {
      if (base == null) {
        false
      } else {
        let other = base.withHostname("path-only.invalid");
        let again = other.tryResolve(input);
        other.hostname == "path-only.invalid" && again != null && again.host == other.host &&
          url.scheme == base.scheme && url.username == base.username &&
          url.password == base.password && url.host == base.host
      }
    }

    let withoutTrailingDot(host: String): String {
      if (host.hasIndex(String.begin) && host[host.prev(host.end)] == char'.') {
        host.slice(String.begin, host.prev(host.end))
      } else {
        host
      }
    }

    let endsWith(s: String, suffix: String): Boolean {
      var i = s.end;
      var j = suffix.end;
      var same = true;
      while (same && j > String.begin) {
        if (i <= String.begin) {
          same = false;
        } else {
          i = s.prev(i);
          j = suffix.prev(j);
          same = s[i] == suffix[j];
        }
      }
      same
    }

What a policy found: the URL, if it passed every rule, or else null,
with the rule it failed first and why, for logs, as
`specialHost: 127.0.0.1 is loopback (RFC 1122), in 127.0.0.0/8`. A
reason may name a host, a well-known scheme, or an origin, but never
credentials or the input, so it's safe to log; the URL isn't.

    export class PolicyCheck {
      public url: Url?;
      public rule: PolicyRule?;
      public reason: String;

      private constructor(url: Url?, rule: PolicyRule?, reason: String) {
        this.url = url;
        this.rule = rule;
        this.reason = reason;
      }

      public get passed(): Boolean { rule == null }

      public toString(): String {
        let r = rule;
        if (r == null) { "passed" } else { "${r.name}: ${reason}" }
      }
    }

The rules, each named for its `with` method: `parse` (input that isn't a
URL), `strict`, `maxLength`, `scheme`, `credentials`, `ipHost`,
`specialHost`, `host`, `sameOrigin`, and `pathOnly`, as a class with one
instance of each, as `HostKind` is.

    export class PolicyRule {
      public name: String;

      private constructor(name: String) {
        this.name = name;
      }

      public toString(): String { name }

      @operator("==")
      public eq(other: PolicyRule): Boolean { name == other.name }

      public static parse = new PolicyRule("parse");
      public static strict = new PolicyRule("strict");
      public static maxLength = new PolicyRule("maxLength");
      public static scheme = new PolicyRule("scheme");
      public static credentials = new PolicyRule("credentials");
      public static ipHost = new PolicyRule("ipHost");
      public static specialHost = new PolicyRule("specialHost");
      public static host = new PolicyRule("host");
      public static sameOrigin = new PolicyRule("sameOrigin");
      public static pathOnly = new PolicyRule("pathOnly");
    }

## Special Addresses and Names

What `withSpecialHosts(false)` refuses, in one table: each address
block, as an address and prefix length, or name, and what it is. The
first that matches names the reason, so specific blocks come before the
blocks around them.

- **IPv4:** every block in IANA's [IPv4 Special-Purpose Address
  Registry](https://www.iana.org/assignments/iana-ipv4-special-registry/)
  that isn't globally reachable, and multicast, from the [IPv4 Address
  Space Registry](https://www.iana.org/assignments/ipv4-address-space/).
  `192.0.0.0/24` is refused whole, though two anycast addresses in it
  are global, since they aren't web servers. The global AS112 and AMT
  blocks are allowed.
- **IPv6:** every block in IANA's [IPv6 Special-Purpose Address
  Registry](https://www.iana.org/assignments/iana-ipv6-special-registry/)
  that isn't globally reachable, likewise refusing `2001::/23` whole,
  and, from the [IPv6 Address
  Space](https://www.iana.org/assignments/ipv6-address-space/) registry,
  multicast and everything outside global unicast (`2000::/3`), which
  covers the deprecated IPv4-compatible (`::127.0.0.1`) and site-local
  addresses. Also two blocks the registry calls global, since they
  embed any IPv4 address, private ones too: NAT64's `64:ff9b::/96` and
  6to4's `2002::/16`. IPv4-mapped addresses (`::ffff:127.0.0.1`) are
  refused whole, as the registry says they aren't global.
- **Names,** and every name under them, with or without a trailing dot:
  `localhost` ([RFC 6761](https://www.rfc-editor.org/rfc/rfc6761)),
  `local`, for multicast DNS on the local network ([RFC
  6762](https://www.rfc-editor.org/rfc/rfc6762)), `home.arpa`, for home
  networks ([RFC 8375](https://www.rfc-editor.org/rfc/rfc8375)), and
  `internal`, which ICANN reserved for private networks in 2024 (as in
  cloud metadata names).

As of 2026-10-30; check the registries for changes.

    let specialHostTable: List<String> = [
      // IPv4.
      "0.0.0.0/8", "this network (RFC 791)",
      "10.0.0.0/8", "private use (RFC 1918)",
      "100.64.0.0/10", "shared address space (RFC 6598)",
      "127.0.0.0/8", "loopback (RFC 1122)",
      "169.254.0.0/16", "link-local (RFC 3927)",
      "172.16.0.0/12", "private use (RFC 1918)",
      "192.0.0.0/24", "IETF protocol assignments (RFC 6890)",
      "192.0.2.0/24", "documentation (RFC 5737)",
      "192.88.99.0/24", "6to4 relay anycast (RFC 7526)",
      "192.168.0.0/16", "private use (RFC 1918)",
      "198.18.0.0/15", "benchmarking (RFC 2544)",
      "198.51.100.0/24", "documentation (RFC 5737)",
      "203.0.113.0/24", "documentation (RFC 5737)",
      "224.0.0.0/4", "multicast (RFC 5771)",
      "255.255.255.255/32", "limited broadcast (RFC 919)",
      "240.0.0.0/4", "reserved (RFC 1112)",
      // IPv6.
      "::/128", "unspecified (RFC 4291)",
      "::1/128", "loopback (RFC 4291)",
      "::ffff:0:0/96", "IPv4-mapped (RFC 4291)",
      "64:ff9b::/96", "IPv4/IPv6 translation (RFC 6052)",
      "64:ff9b:1::/48", "local IPv4/IPv6 translation (RFC 8215)",
      "100::/64", "discard-only (RFC 6666)",
      "2001::/23", "IETF protocol assignments (RFC 2928)",
      "2001:db8::/32", "documentation (RFC 3849)",
      "2002::/16", "6to4 (RFC 3056)",
      "3fff::/20", "documentation (RFC 9637)",
      "fc00::/7", "unique local (RFC 4193)",
      "fe80::/10", "link-local (RFC 4291)",
      "ff00::/8", "multicast (RFC 4291)",
      "::/3", "not global unicast (RFC 4291)",
      "4000::/2", "not global unicast (RFC 4291)",
      "8000::/1", "not global unicast (RFC 4291)",
      // Names.
      "localhost", "loopback (RFC 6761)",
      "local", "multicast DNS (RFC 6762)",
      "home.arpa", "home network (RFC 8375)",
      "internal", "private network (ICANN, 2024)",
    ];

The table, parsed once: each address as 16-bit pieces, two for IPv4
and eight for IPv6, with its prefix length, or a name, with none.

    class SpecialHost {
      public text: String;
      public about: String;
      public pieces: List<Int>;
      public bits: Int;

      public constructor(text: String, about: String, pieces: List<Int>, bits: Int) {
        this.text = text;
        this.about = about;
        this.pieces = pieces;
        this.bits = bits;
      }
    }

    let specialHosts: List<SpecialHost> = parseSpecialHosts(specialHostTable);

    let parseSpecialHosts(table: List<String>): List<SpecialHost> {
      let out = new ListBuilder<SpecialHost>();
      for (var k = 0; k < table.length; k += 2) {
        let text = table[k];
        let parts = text.split("/");
        if (parts.length == 1) {
          out.add(new SpecialHost(text, table[k + 1], [], -1));
        } else {
          let address = parts[0];
          let pieces = if (address.split(":").length > 1) {
            parseIpv6(address, null, 0) orelse panic()
          } else {
            ipv4Pieces(parseIpv4(address, null, 0) orelse panic())
          };
          out.add(new SpecialHost(text, table[k + 1], pieces, parts[1].toInt32() orelse panic()));
        }
      }
      out.toList()
    }

    let ipv4Pieces(address: Int64): List<Int> {
      [((address >> 16) & 0xFFFFi64).toInt32Unsafe(), (address & 0xFFFFi64).toInt32Unsafe()]
    }

Why a host is special, or null if it isn't. A host is read as its kind
says; an empty host is the local machine, as in `file:///etc/passwd`.

    let specialHostReason(kind: HostKind?, host: String, unreadable: Boolean): String? {
      if (unreadable) {
        "${host} isn't a domain or address"
      } else if (kind == null) {
        null
      } else if (kind == HostKind.empty) {
        "empty host, the local machine"
      } else if (kind == HostKind.domain) {
        let name = withoutTrailingDot(host);
        var reason: String? = null;
        for (var k = 0; reason == null && k < specialHosts.length; k += 1) {
          let special = specialHosts[k];
          if (special.bits < 0 && (name == special.text || endsWith(name, ".${special.text}"))) {
            reason = "${host} is ${special.about}";
          }
        }
        reason
      } else {
        let pieces = if (kind == HostKind.ipv4) {
          ipv4Pieces(parseIpv4(host, null, 0) orelse panic())
        } else {
          parseIpv6(host.slice(host.next(String.begin), host.prev(host.end)), null, 0) orelse panic()
        };
        var reason: String? = null;
        for (var k = 0; reason == null && k < specialHosts.length; k += 1) {
          let special = specialHosts[k];
          if (inBlock(pieces, special.pieces, special.bits)) {
            reason = "${host} is ${special.about}, in ${special.text}";
          }
        }
        reason
      }
    }

Whether `address` starts with the first `bits` bits of `block`, both in
16-bit pieces of the same count. Each piece is copied before comparing,
since Temper's Java backend compares list elements as boxed objects.

    let inBlock(address: List<Int>, block: List<Int>, bits: Int): Boolean {
      var matches = bits >= 0 && address.length == block.length;
      var left = bits;
      for (var k = 0; matches && left > 0; k += 1) {
        let a = address[k];
        let b = block[k];
        let shift = if (left >= 16) { 0 } else { 16 - left };
        matches = (a >> shift) == (b >> shift);
        left -= 16;
      }
      matches
    }

## Tests

    test("Policies: strict mode") {
      // Each input, the strict errors, or "" for none, and whether it
      // parses at all; all of them do.
      let cases = [
        "https://example.com/", "",
        "https://example.com/a b?q={x}&a[]=1#a|b", "",
        "https://user@example.com/", "invalid-credentials at 12",
        " https://example.com/", "invalid-URL-unit at 0",
        "https://example.com/\n", "invalid-URL-unit at 20",
        "https://exa\tmple.com/", "invalid-URL-unit at 11",
        "https:\\\\example.com/", "special-scheme-missing-following-solidus at 6, special-scheme-missing-following-solidus at 6, special-scheme-missing-following-solidus at 7",
        "https://example.com\\a", "invalid-reverse-solidus at 19",
        "https:example.com", "special-scheme-missing-following-solidus at 6",
        "http://127.0.0.1/", "",
        "http://127.1/", "IPv4-non-canonical at 7",
        "http://0x7f.1/", "IPv4-non-decimal-part at 7, IPv4-non-canonical at 7",
        "http://0177.0.0.1/", "IPv4-non-decimal-part at 7, IPv4-non-canonical at 7",
        "http://2130706433/", "IPv4-out-of-range-part at 7, IPv4-non-canonical at 7",
        "http://127.0.0.1./", "IPv4-empty-part at 7, IPv4-non-canonical at 7",
        "http://%31%32%37.0.0.1/", "IPv4-non-canonical at 7",
        "http://１２７.0.0.1/", "IPv4-non-canonical at 7",
        "https://%65vil.example/", "domain-percent-encoded at 8",
        "https://EXAMPLE.com/", "",
        "HTTPS://example.com/", "",
        "https://bücher.example/", "",
        "http://[::ffff:127.0.0.1]/", "",
        "foo://ex{ample/", "",
        "mailto:a<b", "",
      ];
      for (var k = 0; k < cases.length; k += 2) {
        let check = checkUrl(cases[k]) orelse panic();
        let errors = check.strictErrors.join(", ") { e => e.toString() };
        assert(check.url != null && errors == cases[k + 1]) { "${cases[k]}: ${errors}" };
        assert((check.strictUrl != null) == (errors == "")) { "${cases[k]}: strictUrl" };
      }
      // Strict errors are all of errors but code points that are kept or
      // escaped, and Hrefine's own two.
      let check = checkUrl(" https://example.com/a b") orelse panic();
      assert(check.errors.length == 2 && check.strictErrors.length == 1);
    }

    test("Policies: schemes, credentials, and length") {
      let policyResult(policy: UrlPolicy, input: String): String {
        let result = policy.check(input);
        let url = result.url;
        if (url == null) { result.toString() } else { "passed ${url.href}" }
      }
      let expectPolicy(policy: UrlPolicy, cases: List<String>): Void {
        for (var k = 0; k < cases.length; k += 2) {
          let got = policyResult(policy, cases[k]);
          let want = cases[k + 1];
          assert(got == want || got.split(":")[0] == want) { "${cases[k]}: ${got}, not ${want}" };
        }
      }
      let schemes = UrlPolicy.any.withSchemes(["HTTP", "https:"]);
      expectPolicy(schemes, [
        "https://example.com/", "passed https://example.com/",
        "HTTP://example.com/", "passed http://example.com/",
        "javascript:alert(1)", "scheme",
        "java\tscript:alert(1)", "scheme",
        "\u{1}javascript:alert(1)", "scheme",
        "ftp://example.com/", "scheme",
        "file:///etc/passwd", "scheme",
        "not a URL", "parse",
      ]);
      assert(policyResult(UrlPolicy.any.withSchemes([]), "https://example.com/") == "scheme: https");
      assert(policyResult(schemes, "javascript:alert(1)") == "scheme: javascript");
      // Without "//", the username is the scheme, so it isn't named.
      assert(
        policyResult(schemes, "admin:hunter2@example.com") ==
          "scheme: one that isn't well known, so not named"
      );
      let noCredentials = UrlPolicy.any.withCredentials(false);
      expectPolicy(noCredentials, [
        "https://example.com/", "passed https://example.com/",
        "https://good.example@evil.example/", "credentials",
        "https://user@good.example@evil.example/", "credentials",
        "https://good.example:443@evil.example/", "credentials",
        "https://:pass@example.com/", "credentials",
        "https://@example.com/", "passed https://example.com/",
        "https://evil.example#@good.example/", "passed https://evil.example/#@good.example/",
        "https://good.example%40evil.example/", "parse",
      ]);
      // Reasons say which credentials were there, never what they are.
      let reasons = [
        "https://alice:hunter2@example.com/", "credentials: a username and a password",
        "https://alice@example.com/", "credentials: a username",
        "https://alice:@example.com/", "credentials: a username",
        "https://:hunter2@example.com/", "credentials: a password",
      ];
      for (var k = 0; k < reasons.length; k += 2) {
        let result = noCredentials.check(reasons[k]);
        assert(result.toString() == reasons[k + 1] && result.reason.split("alice").length == 1) {
          reasons[k + 1]
        };
      }
      let short = UrlPolicy.any.withMaxLength(24);
      expectPolicy(short, [
        "https://example.com/", "passed https://example.com/",
        "https://example.com/abcd", "passed https://example.com/abcd",
        "https://example.com/abcde", "maxLength",
        "https://example.com/ä", "maxLength",
      ]);
      assert(
        policyResult(short, "https://example.com/abcde") ==
          "maxLength: the input is longer than 24 code points"
      );
      assert(
        policyResult(short, "https://example.com/ä") ==
          "maxLength: the URL is longer than 24 code points"
      );
      assert(policyResult(UrlPolicy.any.withMaxLength(0), "") == "parse: not a URL");
    }

The classic SSRF bypasses: every way of writing a loopback, private, or
link-local address, and names that mean the local machine.

    test("Policies: IP and special hosts") {
      let policyResult(policy: UrlPolicy, input: String): String {
        let result = policy.check(input);
        let url = result.url;
        if (url == null) { result.toString() } else { "passed ${url.href}" }
      }
      let expectPolicy(policy: UrlPolicy, cases: List<String>): Void {
        for (var k = 0; k < cases.length; k += 2) {
          let got = policyResult(policy, cases[k]);
          let want = cases[k + 1];
          assert(got == want || got.split(":")[0] == want) { "${cases[k]}: ${got}, not ${want}" };
        }
      }
      let noIp = UrlPolicy.any.withIpHosts(false);
      expectPolicy(noIp, [
        "https://example.com/", "passed https://example.com/",
        "http://127.1/", "ipHost",
        "http://0x7f.1/", "ipHost",
        "http://2130706433/", "ipHost",
        "http://[::1]/", "ipHost",
        "http://%31%32%37.1/", "ipHost",
        "gopher://0x7f.1:6379/", "ipHost",
        "foo://example.com/", "passed foo://example.com/",
        "mailto:a@b", "passed mailto:a@b",
      ]);
      let noSpecial = UrlPolicy.any.withSpecialHosts(false);
      expectPolicy(noSpecial, [
        "https://example.com/", "passed https://example.com/",
        "https://93.184.215.14/", "passed https://93.184.215.14/",
        "https://[2606:2800:21f:cb07:6820:80da:af6b:8b2c]/", "passed https://[2606:2800:21f:cb07:6820:80da:af6b:8b2c]/",
        "http://127.0.0.1/", "specialHost",
        "http://127.1/", "specialHost",
        "http://0x7f.1/", "specialHost",
        "http://0x7f000001/", "specialHost",
        "http://0177.0.0.1/", "specialHost",
        "http://127.000.000.001/", "specialHost",
        "http://2130706433/", "specialHost",
        "http://127.0.0.1./", "specialHost",
        "http://%31%32%37.1/", "specialHost",
        "http://１２７.0.0.1/", "specialHost",
        "http://0/", "specialHost",
        "http://0.0.0.0/", "specialHost",
        "http://10.1.2.3/", "specialHost",
        "http://172.16.0.1/", "specialHost",
        "http://172.32.0.1/", "passed http://172.32.0.1/",
        "http://192.168.1.1/", "specialHost",
        "http://169.254.169.254/latest/meta-data/", "specialHost",
        "http://100.64.0.1/", "specialHost",
        "http://100.128.0.1/", "passed http://100.128.0.1/",
        "http://224.0.0.1/", "specialHost",
        "http://255.255.255.255/", "specialHost",
        "http://[::1]/", "specialHost",
        "http://[::]/", "specialHost",
        "http://[0:0:0:0:0:0:0:1]/", "specialHost",
        "http://[::ffff:127.0.0.1]/", "specialHost",
        "http://[::ffff:7f00:1]/", "specialHost",
        "http://[::ffff:8.8.8.8]/", "specialHost",
        "http://[::127.0.0.1]/", "specialHost",
        "http://[64:ff9b::7f00:1]/", "specialHost",
        "http://[2002:7f00:1::]/", "specialHost",
        "http://[fe80::1]/", "specialHost",
        "http://[fc00::1]/", "specialHost",
        "http://[fd12:3456::1]/", "specialHost",
        "http://[fec0::1]/", "specialHost",
        "http://[ff02::1]/", "specialHost",
        "http://[2001:db8::1]/", "specialHost",
        "http://localhost/", "specialHost",
        "http://localhost./", "specialHost",
        "http://LOCALHOST/", "specialHost",
        "http://a.b.localhost/", "specialHost",
        "http://printer.local/", "specialHost",
        "http://router.home.arpa/", "specialHost",
        "http://metadata.google.internal/", "specialHost",
        "http://notlocalhost/", "passed http://notlocalhost/",
        "http://localhost.example/", "passed http://localhost.example/",
        "file:///etc/passwd", "specialHost",
        "file://localhost/etc/passwd", "specialHost",
        "gopher://127.0.0.1:6379/_INFO", "specialHost",
        "gopher://%31%32%37.1/", "specialHost",
        "foo://[::1]/", "specialHost",
        "foo://exa%zzmple/", "specialHost",
        "mailto:a@127.0.0.1", "passed mailto:a@127.0.0.1",
      ]);
      assert(
        policyResult(noSpecial, "http://0x7f.1/") ==
          "specialHost: 127.0.0.1 is loopback (RFC 1122), in 127.0.0.0/8"
      );
      assert(
        policyResult(noSpecial, "http://[::ffff:127.0.0.1]/") ==
          "specialHost: [::ffff:7f00:1] is IPv4-mapped (RFC 4291), in ::ffff:0:0/96"
      );
      assert(policyResult(noSpecial, "http://localhost./") == "specialHost: localhost. is loopback (RFC 6761)");
    }

Allowlists compare the parsed host, so look-alikes, escapes, and user
info can't pass, but other spellings of an allowed host do.

    test("Policies: host allowlists") {
      let policyResult(policy: UrlPolicy, input: String): String {
        let result = policy.check(input);
        let url = result.url;
        if (url == null) { result.toString() } else { "passed ${url.href}" }
      }
      let expectPolicy(policy: UrlPolicy, cases: List<String>): Void {
        for (var k = 0; k < cases.length; k += 2) {
          let got = policyResult(policy, cases[k]);
          let want = cases[k + 1];
          assert(got == want || got.split(":")[0] == want) { "${cases[k]}: ${got}, not ${want}" };
        }
      }
      let exact = UrlPolicy.any.withHosts(["Good.Example", "bücher.example", "10.0.0.1", "[::1]", "::2", "bad host"], false);
      expectPolicy(exact, [
        "https://good.example/", "passed https://good.example/",
        "https://GOOD.example./", "passed https://good.example./",
        "https://ｇｏｏｄ.example/", "passed https://good.example/",
        "https://xn--bcher-kva.example/", "passed https://xn--bcher-kva.example/",
        "https://Bücher.example/", "passed https://xn--bcher-kva.example/",
        "http://10.0.0.1/", "passed http://10.0.0.1/",
        "http://10.1/", "passed http://10.0.0.1/",
        "http://[::1]/", "passed http://[::1]/",
        "http://[::2]/", "host",
        "https://www.good.example/", "host",
        "https://good.example.evil.example/", "host",
        "https://evilgood.example/", "host",
        "https://good.example@evil.example/", "host",
        "https://evil.example#@good.example/", "host",
        "https://evil.example\\@good.example/", "host",
        "https://good.example\\.evil.example/", "passed https://good.example/.evil.example/",
        "https://good.example\t.evil.example/", "host",
        "https://good.example%2Eevil.example/", "host",
        "https://good.example%40evil.example/", "parse",
        "https://good.example。evil.example/", "host",
        "https://gооd.example/", "host",
        "https://ｅｖｉｌ.example/", "host",
        "mailto:someone@good.example", "host",
        "file:///etc/passwd", "host",
        "foo://good.example/", "passed foo://good.example/",
      ]);
      let under = UrlPolicy.any.withHosts(["good.example", "10.0.0.1"], true);
      expectPolicy(under, [
        "https://good.example/", "passed https://good.example/",
        "https://www.good.example/", "passed https://www.good.example/",
        "https://a.b.good.example./", "passed https://a.b.good.example./",
        "https://evilgood.example/", "host",
        "https://good.example.evil.example/", "host",
        "https://good.example%2Eevil.example/", "host",
        "https://evil.example/good.example", "host",
        "http://1.10.0.0.1/", "parse",
        "http://x.10.0.0.1/", "parse",
      ]);
      expectPolicy(UrlPolicy.any.withHosts([], true), ["https://good.example/", "host"]);
    }

Redirect targets, against a site: same origin, or a path only.

    test("Policies: same origin and redirects") {
      let policyResult(policy: UrlPolicy, input: String): String {
        let result = policy.check(input);
        let url = result.url;
        if (url == null) { result.toString() } else { "passed ${url.href}" }
      }
      let expectPolicy(policy: UrlPolicy, cases: List<String>): Void {
        for (var k = 0; k < cases.length; k += 2) {
          let got = policyResult(policy, cases[k]);
          let want = cases[k + 1];
          assert(got == want || got.split(":")[0] == want) { "${cases[k]}: ${got}, not ${want}" };
        }
      }
      let site = parseUrl("https://good.example/app/") orelse panic();
      let sameOrigin = UrlPolicy.any.withBase(site).withSameOrigin(site);
      expectPolicy(sameOrigin, [
        "/account", "passed https://good.example/account",
        "settings?tab=2", "passed https://good.example/app/settings?tab=2",
        "https://good.example/x", "passed https://good.example/x",
        "https://GOOD.example:443/x", "passed https://good.example/x",
        "http://good.example/x", "sameOrigin",
        "https://good.example:8443/x", "sameOrigin",
        "//evil.example/", "sameOrigin",
        "///evil.example/", "sameOrigin",
        "/\\evil.example", "sameOrigin",
        "\\\\evil.example\\path", "sameOrigin",
        "\\/evil.example/", "sameOrigin",
        "/\t/evil.example", "sameOrigin",
        "https:evil.example/", "passed https://good.example/app/evil.example/",
        "http:evil.example/", "sameOrigin",
        "javascript:alert(1)", "sameOrigin",
        "//[::1", "parse",
      ]);
      let pathOnly = UrlPolicy.any.withBase(site).withPathOnly(true);
      expectPolicy(pathOnly, [
        "/account", "passed https://good.example/account",
        "settings?tab=2", "passed https://good.example/app/settings?tab=2",
        "#top", "passed https://good.example/app/#top",
        "/a/%2F%2Fevil.example", "passed https://good.example/a/%2F%2Fevil.example",
        "https://good.example/x", "pathOnly",
        "//good.example/x", "pathOnly",
        "//evil.example/", "pathOnly",
        "/\\evil.example", "pathOnly",
        "\\\\evil.example\\path", "pathOnly",
        "/\t/evil.example", "pathOnly",
        "https:evil.example/", "passed https://good.example/app/evil.example/",
        "javascript:alert(1)", "pathOnly",
      ]);
      expectPolicy(UrlPolicy.any.withPathOnly(true), [
        "/account", "parse",
        "https://good.example/", "pathOnly",
      ]);
      let strictPaths = pathOnly.withStrict(true);
      expectPolicy(strictPaths, [
        "/account", "passed https://good.example/account",
        "/a\\b", "strict",
        "/\t/evil.example", "strict",
      ]);
      // A base's credentials carry over to relative input, strict or not,
      // as the standard says; href still leaves them out.
      let signedIn = parseUrl("https://user:pw@good.example/app/") orelse panic();
      for (let p of [UrlPolicy.any.withBase(signedIn), UrlPolicy.any.withBase(signedIn).withStrict(true)]) {
        let url = p.check("/account").url;
        let full = if (url == null) { "refused" } else { url.hrefWithCredentials };
        let bare = if (url == null) { "refused" } else { url.href };
        assert(full == "https://user:pw@good.example/account") { "base credentials kept" };
        assert(bare == "https://good.example/account") { "href without credentials" };
      }
    }

The recorded corpus's inputs, the gallery's and the table's on the site
(`site/gallery.json`), against a policy for fetching from one host:
`UrlPolicy.fetch` (strict, `https` only, no credentials or special
hosts), and `good.example` and its subdomains. Each input, its base or "" for none,
and the rule it fails, or the `href` it passes with.

    test("Policies: the recorded corpus") {
      let policyResult(policy: UrlPolicy, input: String): String {
        let result = policy.check(input);
        let url = result.url;
        if (url == null) { result.toString() } else { "passed ${url.href}" }
      }
      let expectPolicy(policy: UrlPolicy, cases: List<String>): Void {
        for (var k = 0; k < cases.length; k += 2) {
          let got = policyResult(policy, cases[k]);
          let want = cases[k + 1];
          assert(got == want || got.split(":")[0] == want) { "${cases[k]}: ${got}, not ${want}" };
        }
      }
      let site = parseUrl("https://good.example/") orelse panic();
      let policy = UrlPolicy.fetch.withHosts(["good.example"], true);
      let relative = policy.withBase(site);
      let cases = [
        "https://example.com\\@evil.example/", "strict",
        "http://127.1/", "strict",
        "http://0x7f.1/", "strict",
        "http://2130706433/", "strict",
        "https:\\\\evil.example\\path", "strict",
        "https://good.example@evil.example/", "strict",
        "https://evil.example#@good.example/", "host",
        "https://good.example\t.evil.example/", "strict",
        "java\tscript:alert(1)", "strict",
        "https://аpple.com/", "host",
        "https://good.example。evil.example/", "host",
        "https:///evil.example/", "strict",
        "https://good.example\\.evil.example/", "strict",
        "https:/\\evil.example/", "strict",
        "\u{1}javascript:alert(1)", "strict",
        "https://good.example%09.evil.example/", "parse",
        "https://good.example\u{0}.evil.example/", "parse",
        "https://good.example/a/..\t/b", "strict",
        "https://user@good.example@evil.example/", "strict",
        "https://good.example%40evil.example/", "parse",
        "http://1.1.1.1 &@2.2.2.2# @3.3.3.3/", "strict",
        "https://good.example:443@evil.example/", "strict",
        "http://0177.0.0.1/", "strict",
        "http://0x7f000001/", "strict",
        "http://127.000.000.001/", "strict",
        "http://0/", "strict",
        "http://127.0.0.1./", "strict",
        "http://%31%32%37.1/", "strict",
        "http://4294967296/", "parse",
        "http://1.2.3.4.5/", "parse",
        "http://[fe80::1%25eth0]/", "parse",
        "http://[::1]./", "parse",
        "http://[::ffff:127.0.0.1]/", "scheme",
        "https://[::ffff:127.0.0.1]/", "specialHost",
        "https://%65vil.example/", "strict",
        "https://evil%2Eexample/", "strict",
        "https://evil.example%2F.good.example/", "parse",
        "https://ｅｖｉｌ.example/", "host",
        "https://ⓔⓥⓘⓛ.example/", "host",
        "https://ev\u{ad}il.example/", "host",
        "https://faß.example/", "host",
        "https://evil.example./", "host",
        "https:evil.example/", "strict",
        "https:/evil.example/", "strict",
        "http://evil.example:65536/", "parse",
        "http://evil.example:0x50/", "parse",
        "http://evil.example: 80/", "parse",
        "https://good.example/public/%2e%2e/admin", "passed https://good.example/admin",
        "https://good.example/public\\..\\admin", "strict",
        "https://good.example/a/./b/../../../c", "passed https://good.example/c",
        "https://good.example/public/%2E%2E%2Fadmin", "passed https://good.example/public/%2E%2E%2Fadmin",
        "https://good.example/a b", "passed https://good.example/a%20b",
        "https://good.example/ä", "passed https://good.example/%C3%A4",
        "https://good.example/%zz", "passed https://good.example/%zz",
        "https://good.example/a|b^c", "passed https://good.example/a|b%5Ec",
        "https://www.good.example/", "passed https://www.good.example/",
      ];
      expectPolicy(policy, cases);
      expectPolicy(relative, [
        "/\\evil.example", "strict",
        "//evil.example/", "host",
        "\\\\evil.example\\path", "strict",
        "/\t/evil.example", "strict",
        "///evil.example/", "strict",
        "\\/evil.example/", "strict",
        "http:evil.example/", "strict",
        "https:evil.example/", "strict",
        "/account", "passed https://good.example/account",
      ]);
    }

The preset for fetching refuses every credentials and SSRF case above,
for one rule or another, and never echoes credentials in its reasons.

    test("Policies: the fetch preset") {
      let refused = [
        "https://good.example@evil.example/", "https://user@good.example@evil.example/",
        "https://good.example:443@evil.example/", "https://:pass@example.com/",
        "https://alice:hunter2@example.com/", "https://alice@example.com/",
        "https://hunter2@example.com/", "admin:hunter2@example.com",
        "http://127.0.0.1/", "http://127.1/", "http://0x7f.1/", "http://0x7f000001/",
        "http://0177.0.0.1/", "http://127.000.000.001/", "http://2130706433/",
        "http://127.0.0.1./", "http://%31%32%37.1/", "http://１２７.0.0.1/", "http://0/",
        "http://0.0.0.0/", "http://10.1.2.3/", "http://172.16.0.1/", "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/", "http://100.64.0.1/", "http://224.0.0.1/",
        "http://255.255.255.255/", "http://[::1]/", "http://[::]/", "http://[0:0:0:0:0:0:0:1]/",
        "http://[::ffff:127.0.0.1]/", "http://[::ffff:7f00:1]/", "http://[::ffff:8.8.8.8]/",
        "http://[::127.0.0.1]/", "http://[64:ff9b::7f00:1]/", "http://[2002:7f00:1::]/",
        "http://[fe80::1]/", "http://[fc00::1]/", "http://[fd12:3456::1]/", "http://[fec0::1]/",
        "http://[ff02::1]/", "http://[2001:db8::1]/", "http://localhost/", "http://localhost./",
        "http://LOCALHOST/", "http://a.b.localhost/", "http://printer.local/",
        "http://router.home.arpa/", "http://metadata.google.internal/", "file:///etc/passwd",
        "file://localhost/etc/passwd", "gopher://127.0.0.1:6379/_INFO", "gopher://%31%32%37.1/",
        "foo://[::1]/", "foo://exa%zzmple/", "mailto:a@127.0.0.1", "javascript:alert(1)",
      ];
      for (let input of refused) {
        let result = UrlPolicy.fetch.check(input);
        assert(result.url == null) { "the preset must refuse ${input}" };
        let text = result.toString();
        assert(
          text.split("alice").length == 1 && text.split("hunter2").length == 1 &&
            text.split("good.example@").length == 1 && text.split("user").length == 1 &&
            text.split("pass").length == 1 && text.split("admin").length == 1
        ) { "the reason for ${input} echoes credentials" };
      }
      // Each of the specialHost cases fails the same way as https.
      for (let input of refused) {
        let plain = Url.parse(input);
        let secure = if (plain == null) { "" } else { plain.withProtocol("https").hrefWithCredentials };
        if (secure.split("https:").length == 2) {
          let result = UrlPolicy.fetch.check(secure);
          assert(result.url == null) { "the preset must refuse ${input} as https" };
        }
      }
      let ok = UrlPolicy.fetch.check("https://example.com/a?b#c");
      assert(ok.url != null && ok.toString() == "passed");
      let rules = [
        "https://alice:hunter2@example.com/", "strict: invalid-credentials at 21",
        "https://127.0.0.1/", "specialHost: 127.0.0.1 is loopback (RFC 1122), in 127.0.0.0/8",
        "https://127.1/", "strict: IPv4-non-canonical at 8",
        "http://example.com/", "scheme: http",
        "https://example.com/a\\b", "strict: invalid-reverse-solidus at 21",
      ];
      for (var k = 0; k < rules.length; k += 2) {
        let text = UrlPolicy.fetch.check(rules[k]).toString();
        assert(text == rules[k + 1]) { "${rules[k + 1]}, not ${text}" };
      }
      let long = new StringBuilder();
      long.append("https://example.com/");
      for (var k = 0; k < 8172; k += 1) {
        long.append("a");
      }
      assert(UrlPolicy.fetch.check(long.toString()).url != null) { "at the limit" };
      long.append("a");
      assert(UrlPolicy.fetch.check(long.toString()).rule == PolicyRule.maxLength) { "max length" };
      assert(UrlPolicy.fetch.withSchemes(["http"]).check("http://example.com/").url != null);
    }
