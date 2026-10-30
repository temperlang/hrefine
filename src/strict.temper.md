# The Strict RFC 3986 Form

A URL's `href` is the URL Standard's canonical form, which browsers and
most parsers read alike. But the standard leaves a few characters
unescaped that [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986) doesn't
allow, so strict parsers, such as Java's `URI` and Go's `net/url`,
reject them or read them another way. `url.strictHref` is `href` with
those escaped: a valid RFC 3986 URI, which means the same URL, as
Hrefine (or a browser) reads it back. Like `href`, it has no
credentials; `strictHrefWithCredentials` is the same for
`hrefWithCredentials`, with the username and password.

## What's Escaped

RFC 3986 allows, besides `%` and two hex digits, its *unreserved*
characters (ASCII letters and digits, `-`, `.`, `_`, and `~`) and
*sub-delims* (`!`, `$`, `&`, `'`, `(`, `)`, `*`, `+`, `,`, `;`, and
`=`) in every part, and more in some:

- **User info:** and `:`. The URL Standard's userinfo set escapes all
  the rest already, but for `%`.
- **Hosts** (domains, IPv4 addresses, and opaque hosts): nothing more.
  The standard allows `"`, `` ` ``, `{`, and `}` in domains and opaque
  hosts, as in `http://a{b}.example/`. IPv6 addresses keep their
  brackets, and are left as they are.
- **Paths:** and `:`, `@`, and `/`. The path set leaves `[`, `\`, `]`,
  and `|`, and an opaque path, as in `mailto:` and `data:` URLs, is
  escaped only for controls and non-ASCII, leaving space, `"`, `<`,
  `>`, `[`, `\`, `]`, `^`, `` ` ``, `{`, `|`, and `}`.
- **Queries and fragments:** and `:`, `@`, `/`, and `?`. The query set
  leaves `[`, `\`, `]`, `^`, `` ` ``, `{`, `|`, and `}`; the fragment set
  the same, but for `` ` ``, and `#`, which a fragment can hold.

A `%` without two hex digits after it becomes `%25` everywhere, as in
`/%zz`, which the standard keeps as it is. Non-ASCII never needs it:
`href` escapes it everywhere, and hosts are already in Punycode.

As RFC 3986's normalization (section 6.2.2) says, escapes take
uppercase hex digits, and escapes of unreserved characters are decoded,
so `%7e` becomes `~` and `%2E%2E%2F` becomes `..%2F` (C#'s `Uri` does
the same). That never makes a dot segment: the URL Standard already
reads `%2E` as a dot there, and resolves them. Opaque paths keep `%2E`,
which nothing resolves.

Everything else is `href`'s: the same parts, so `strictHref` parses
back, with Hrefine, to a URL whose every part decodes to the same bytes,
and whose `strictHref` is the same again; and so for
`strictHrefWithCredentials`.

    let strictUserinfo = 0;
    let strictHost = 1;
    let strictPath = 2;
    let strictOpaquePath = 3;
    let strictQuery = 4;

Whether RFC 3986 allows ASCII code point `c` as it is in `part`, other
than in an escape.

    let rfcAllows(c: Int, part: Int): Boolean {
      if (
        (c >= char'a' && c <= char'z') || (c >= char'A' && c <= char'Z') ||
          (c >= char'0' && c <= char'9')
      ) {
        true
      } else if (isUnreservedMark(c) || isSubDelim(c)) {
        true
      } else if (part == strictHost) {
        false
      } else if (c == char':') {
        true
      } else if (part == strictUserinfo) {
        false
      } else if (c == char'@' || c == char'/') {
        true
      } else {
        part == strictQuery && c == char'?'
      }
    }

    let isUnreservedMark(c: Int): Boolean {
      c == char'-' || c == char'.' || c == char'_' || c == char'~'
    }

    let isUnreserved(c: Int): Boolean {
      (c >= char'a' && c <= char'z') || (c >= char'A' && c <= char'Z') ||
        (c >= char'0' && c <= char'9') || isUnreservedMark(c)
    }

    let isSubDelim(c: Int): Boolean {
      c == char'!' || c == char'$' || c == char'&' || c == char'\'' || c == char'(' ||
        c == char')' || c == char'*' || c == char'+' || c == char',' || c == char';' ||
        c == char'='
    }

Part `s` in its strict form. Most parts need no change, and are given
back as they are.

    let strictPart(s: String, part: Int): String {
      var clean = true;
      for (var i = String.begin; clean && s.hasIndex(i); i = s.next(i)) {
        let c = s[i];
        clean = c != char'%' && c < 0x80 && rfcAllows(c, part);
      }
      if (clean) { s } else { strictRewrite(s, part) }
    }

    let strictRewrite(s: String, part: Int): String {
      let out = new StringBuilder();
      var i = String.begin;
      while (s.hasIndex(i)) {
        let c = s[i];
        let j = s.next(i);
        if (c == char'%') {
          let k = if (s.hasIndex(j)) { s.next(j) } else { j };
          let high = if (s.hasIndex(j)) { hexValue(s[j]) } else { -1 };
          let low = if (s.hasIndex(k)) { hexValue(s[k]) } else { -1 };
          if (high >= 0 && low >= 0) {
            let byte = high * 16 + low;
            if (isUnreserved(byte) && !(part == strictOpaquePath && byte == char'.')) {
              appendCode(out, byte);
            } else {
              appendByte(out, byte);
            }
            i = s.next(k);
          } else {
            out.append("%25");
            i = j;
          }
        } else {
          if (c >= 0x80) {
            // Not from `href`, which escapes it already, but kept safe.
            percentEncodeOnto(out, c, c0ControlSet);
          } else if (rfcAllows(c, part)) {
            appendCode(out, c);
          } else {
            appendByte(out, c);
          }
          i = j;
        }
      }
      out.toString()
    }

## Tests

Whether `s` is a URI by RFC 3986's grammar (section 3, and appendix A),
or what's wrong: a scheme and `:`, then an authority after `//` (user
info, a host, and a port), a path, a query after `?`, and a fragment
after `#`. An IP literal's brackets must hold only hex digits, `:`, and
`.` here, which is looser than the RFC, but fine for `href`'s IPv6.

    let rfc3986Problem(s: String): String {
      var i = String.begin;
      var problem = "";
      if (!s.hasIndex(i) || !isAsciiAlpha(s[i])) {
        problem = "no scheme";
      }
      while (
        problem == "" && s.hasIndex(i) &&
          (isAsciiAlpha(s[i]) || (s[i] >= char'0' && s[i] <= char'9') || s[i] == char'+' ||
            s[i] == char'-' || s[i] == char'.')
      ) {
        i = s.next(i);
      }
      if (problem == "" && !(s.hasIndex(i) && s[i] == char':')) {
        problem = "no colon after the scheme";
      }
      if (problem == "") {
        i = s.next(i);
      }
      let twoSlashes = problem == "" && s.hasIndex(i) && s[i] == char'/' &&
        s.hasIndex(s.next(i)) && s[s.next(i)] == char'/';
      if (twoSlashes) {
        i = s.next(s.next(i));
        var end = i;
        while (s.hasIndex(end) && s[end] != char'/' && s[end] != char'?' && s[end] != char'#') {
          end = s.next(end);
        }
        problem = authorityProblem(s.slice(i, end));
        i = end;
      } else if (
        problem == "" && s.hasIndex(i) && s[i] == char'/' && s.hasIndex(s.next(i)) &&
          s[s.next(i)] == char'/'
      ) {
        problem = "a path starting with // without an authority";
      }
      var section = strictPath;
      while (problem == "" && s.hasIndex(i)) {
        let c = s[i];
        if (c == char'?' && section == strictPath) {
          section = strictQuery;
          i = s.next(i);
        } else if (c == char'#' && section != -1) {
          section = -1;
          i = s.next(i);
        } else {
          problem = charProblem(s, i, if (section == -1) { strictQuery } else { section });
          i = escapeEnd(s, i);
        }
      }
      problem
    }

    let authorityProblem(authority: String): String {
      var problem = "";
      var hostStart = String.begin;
      for (var i = String.begin; authority.hasIndex(i); i = authority.next(i)) {
        if (hostStart == String.begin && authority[i] == char'@') {
          hostStart = authority.next(i);
        }
      }
      for (var i = String.begin; problem == "" && i < hostStart && authority[i] != char'@'; i = escapeEnd(authority, i)) {
        problem = charProblem(authority, i, strictUserinfo);
      }
      var i = hostStart;
      if (authority.hasIndex(i) && authority[i] == char'[') {
        while (problem == "" && authority.hasIndex(i) && authority[i] != char']') {
          let c = authority[i];
          if (!(c == char'[' || c == char':' || c == char'.' || hexValue(c) >= 0)) {
            problem = "U+${c.toString(16)} in an IP literal";
          }
          i = authority.next(i);
        }
        if (problem == "" && !authority.hasIndex(i)) {
          problem = "an unclosed IP literal";
        } else if (problem == "") {
          i = authority.next(i);
        }
      } else {
        while (problem == "" && authority.hasIndex(i) && authority[i] != char':') {
          problem = charProblem(authority, i, strictHost);
          i = escapeEnd(authority, i);
        }
      }
      if (problem == "" && authority.hasIndex(i)) {
        if (authority[i] != char':') {
          problem = "U+${authority[i].toString(16)} after the host";
        }
        i = authority.next(i);
        while (problem == "" && authority.hasIndex(i)) {
          if (authority[i] < char'0' || authority[i] > char'9') {
            problem = "a port that isn't digits";
          }
          i = authority.next(i);
        }
      }
      problem
    }

What's wrong with the code point at `i`, in `part`, if anything: an
escape needs two hex digits.

    let charProblem(s: String, i: StringIndex, part: Int): String {
      let c = s[i];
      if (c == char'%') {
        let j = s.next(i);
        let k = if (s.hasIndex(j)) { s.next(j) } else { j };
        if (s.hasIndex(j) && s.hasIndex(k) && hexValue(s[j]) >= 0 && hexValue(s[k]) >= 0) {
          ""
        } else {
          "a % without two hex digits"
        }
      } else if (c < 0x80 && rfcAllows(c, part)) {
        ""
      } else {
        "U+${c.toString(16)} unescaped"
      }
    }

    let escapeEnd(s: String, i: StringIndex): StringIndex {
      let j = s.next(i);
      if (s[i] == char'%' && s.hasIndex(j) && s.hasIndex(s.next(j))) { s.next(s.next(j)) } else { j }
    }

What's wrong with `url`'s strict form, if anything: it must be RFC
3986, parse back, give the same strict form again, and have parts that
decode to the same bytes as `url`'s. It checks the form with
credentials, so that they roundtrip too.

    let strictProblem(url: Url): String {
      let strict = url.strictHrefWithCredentials;
      let rfc = rfc3986Problem(strict);
      let back = Url.parse(strict);
      if (rfc != "") {
        "strictHref ${strict} isn't RFC 3986: ${rfc}"
      } else if (back == null) {
        "strictHref ${strict} doesn't parse"
      } else if (back.strictHrefWithCredentials != strict) {
        "strictHref ${strict} parses back as ${back.strictHrefWithCredentials}"
      } else if (
        back.scheme != url.scheme || !sameBytes(back.username, url.username) ||
          !sameBytes(back.password, url.password) || !sameBytes(back.hostname, url.hostname) ||
          back.port != url.port || !sameBytes(back.pathname, url.pathname) ||
          !sameBytes(back.search, url.search) || !sameBytes(back.hash, url.hash)
      ) {
        "strictHref ${strict} parses back to other parts, as ${back.hrefWithCredentials}"
      } else {
        ""
      }
    }

    let sameBytes(a: String, b: String): Boolean {
      let x = percentDecode(a);
      let y = percentDecode(b);
      var same = x.length == y.length;
      for (var k = 0; same && k < x.length; k += 1) {
        // Each byte in a local first: Temper's Java backend compares
        // `x[k] == y[k]` as boxed `Integer`s, by reference (2026-10-30).
        let a = x[k];
        let b = y[k];
        same = a == b;
      }
      same
    }

The examples above, and some of each part. web-platform-tests' URLs and
setters check `strictProblem` for every case too.

    test("Strict RFC 3986 form") {
      let cases = [
        "https://example.com/a|b?q={x}#c^d", "https://example.com/a%7Cb?q=%7Bx%7D#c%5Ed",
        "https://good.example/%zz", "https://good.example/%25zz",
        "https://good.example/public/%2E%2E%2Fadmin", "https://good.example/public/..%2Fadmin",
        "https://example.com/%7e%c3%a9", "https://example.com/~%C3%A9",
        "http://a{b}.example/", "http://a%7Bb%7D.example/",
        "foo://h%41st/[x]", "foo://hAst/%5Bx%5D",
        "https://u%zz:p@example.com/a|b", "https://example.com/a%7Cb",
        "https://example.com/#a#b`[]", "https://example.com/#a%23b%60%5B%5D",
        "https://example.com/?a b'|\\", "https://example.com/?a%20b%27%7C%5C",
        "foo://h/a\\b", "foo://h/a%5Cb",
        "mailto:a b<c>@example.com", "mailto:a%20b%3Cc%3E@example.com",
        "foo:%2E%2E/x", "foo:%2E%2E/x",
        "web+demo:/.//not-a-host/|", "web+demo:/.//not-a-host/%7C",
        "https://[::1]:8080/", "https://[::1]:8080/",
        "https://example.com/a;b=c:d@e?f/g?h", "https://example.com/a;b=c:d@e?f/g?h",
      ];
      for (var k = 0; k < cases.length; k += 2) {
        let url = parseUrl(cases[k]) orelse panic();
        assert(url.strictHref == cases[k + 1]) { "${cases[k]}: ${url.strictHref}" };
        let problem = strictProblem(url);
        assert(problem == "") { problem };
      }
      let user = parseUrl("https://u%zz:p|q@example.com/a|b") orelse panic();
      assert(user.strictHrefWithCredentials == "https://u%25zz:p%7Cq@example.com/a%7Cb") {
        user.strictHrefWithCredentials
      };
      assert(rfc3986Problem("https://example.com/a|b") != "");
      assert(rfc3986Problem("https://exa mple.com/") != "");
      assert(rfc3986Problem("https://example.com/%zz") != "");
      assert(rfc3986Problem("https://example.com/#a#b") != "");
      assert(rfc3986Problem("https://[::1]/?a/b?c#d/e?") == "");
    }

web-platform-tests' `percent-encoding.json`: each input, put in a
URL's query and fragment, must be percent-encoded as its `utf-8`
output. Its other outputs are for pages in legacy encodings, whose
queries browsers encode in that encoding, and which the `URL` API never
uses, so they're left out.

    test("Percent-encoding: web-platform-tests' percent-encoding.json (UTF-8)") {
      let cases = [
        "\u{2020}", "%E2%80%A0",
        "\u{E}A", "%0EA",
        "\u{203E}\\", "%E2%80%BE\\",
        "\u{E5E5}", "%EE%97%A5",
        "\u{2212}", "%E2%88%92",
        "\u{A2}", "%C2%A2",
        "\u{E1}|", "%C3%A1|",
      ];
      for (var k = 0; k < cases.length; k += 2) {
        let url = parseUrl("https://doesnotmatter.invalid/?${cases[k]}#${cases[k]}") orelse panic();
        assert(url.search == "?${cases[k + 1]}" && url.hash == "#${cases[k + 1]}") { url.href };
      }
    }
