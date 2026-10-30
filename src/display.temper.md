# Display

A URL formatted for people to read, as browsers' address bars show it:
international domain names in Unicode where browsers would show them,
escapes of non-ASCII text decoded, and no credentials (the username and
password written in the URL, as in `https://user:pass@host/`); and, if asked, a username, but never a password, and without
the fragment or a lone `/` path.

**The display form is never for security decisions,** nor for handing
on: it may drop parts, and it shows Unicode that can look like other
text. Decide on `Url` and its `href`, and show this. It may still
contain other secrets, such as `?token=` in a query, so don't log it.

```temper inert
let shown = UrlDisplay.addressBar.withRootSlash(false);
shown.format(parseUrl("https://user@xn--bcher-kva.example/") orelse panic()); // "https://bücher.example"
shown.format(parseUrl("https://xn--pple-43d.com/caf%C3%A9") orelse panic()); // "https://xn--pple-43d.com/café"
```

## Formatting

A display format, built from `UrlDisplay.addressBar` with `with`
methods, as policies are, each giving a new format with one option
changed.

    export class UrlDisplay {
      private unicodeHosts: Boolean;
      private decoding: Boolean;
      private credentials: Boolean;
      private fragment: Boolean;
      private rootSlash: Boolean;

      private constructor(
        unicodeHosts: Boolean, decoding: Boolean, credentials: Boolean, fragment: Boolean,
        rootSlash: Boolean,
      ) {
        this.unicodeHosts = unicodeHosts;
        this.decoding = decoding;
        this.credentials = credentials;
        this.fragment = fragment;
        this.rootSlash = rootSlash;
      }

As browsers' address bars show a URL: every part but the credentials,
which browsers leave out, domains in Unicode where browsers would show
them (`domainToDisplay`), and escapes decoded where that's safe.

      public static addressBar: UrlDisplay = new UrlDisplay(true, true, false, true, true);

**Unicode hosts:** with `false`, domains stay as in `href`, with `xn--`
labels.

      public withUnicodeHosts(shown: Boolean): UrlDisplay {
        new UrlDisplay(shown, decoding, credentials, fragment, rootSlash)
      }

**Decoding:** with `false`, the path, query, and fragment stay escaped,
as in `href`. Otherwise escapes of non-ASCII text are decoded where
it's safe: each must be UTF-8 for a code point that's valid in a
domain name (so no controls, spaces, invisible format characters, or
private use), but for the joiners U+200C and U+200D, and a few that look
like `/`, `?`, `#`, or a padlock, or are blank. A combining mark is
decoded only after other decoded text, so it can't change how an ASCII
character before it looks. Escaped ASCII always stays escaped, so `%2F`
still reads as an escaped slash, and the display form parses back to
the same `href`.

      public withDecoding(shown: Boolean): UrlDisplay {
        new UrlDisplay(unicodeHosts, shown, credentials, fragment, rootSlash)
      }

**Credentials:** with `true`, the username is shown, and a password
only as `***`, never itself, as `https://user:***@example.com/`, so a
display can say that a URL has them. With `false`, the default, both
are left out, as browsers' address bars leave them out. A username can
be a secret too, such as an API token, so show it only where that's
safe.

      public withCredentials(shown: Boolean): UrlDisplay {
        new UrlDisplay(unicodeHosts, decoding, shown, fragment, rootSlash)
      }

**Fragment:** with `false`, the fragment is left out, and its `#`.

      public withFragment(shown: Boolean): UrlDisplay {
        new UrlDisplay(unicodeHosts, decoding, credentials, shown, rootSlash)
      }

**Root slash:** with `false`, a path that's only `/`, with nothing
shown after it, is left out, as `https://example.com`, which every
special URL's parser reads back with the `/`.

      public withRootSlash(shown: Boolean): UrlDisplay {
        new UrlDisplay(unicodeHosts, decoding, credentials, fragment, shown)
      }

`url` formatted for display. Never for security decisions, nor for
handing on: use `url.href` for those.

      public format(url: Url): String {
        let href = url.href;
        let beforeHash = beforeFragment(href);
        let hasQuery = beforeQuery(beforeHash) != beforeHash;
        let hasFragment = beforeHash != href && fragment;
        let out = new StringBuilder();
        out.append(url.protocol);
        let kind = url.hostKind;
        if (kind != null) {
          out.append("//");
          if (credentials && (url.username != "" || url.password != "")) {
            out.append(url.username);
            if (url.password != "") {
              out.append(":***");
            }
            out.append("@");
          }
          out.append(
            if (unicodeHosts && kind == HostKind.domain) {
              domainToDisplay(url.hostname)
            } else {
              url.hostname
            },
          );
          if (url.port != "") {
            out.append(":");
            out.append(url.port);
          }
        }
        let path = url.pathname;
        if (kind == null && startsWithText(path, "//")) {
          out.append("/.");
        }
        let special = isSpecialScheme(url.scheme);
        if (!(path == "/" && special && !rootSlash && !hasQuery && !hasFragment)) {
          out.append(shownText(path, decoding));
        }
        if (hasQuery) {
          out.append("?");
          out.append(shownText(withoutLeading(url.search, char'?'), decoding));
        }
        if (hasFragment) {
          out.append("#");
          out.append(shownText(withoutLeading(url.hash, char'#'), decoding));
        }
        out.toString()
      }
    }

`href` up to its query, if any. Only the query's `?` can be before the
fragment, since the path set escapes `?`, and `?` ends an opaque path.

    let beforeQuery(s: String): String {
      var i = String.begin;
      while (s.hasIndex(i) && s[i] != char'?') {
        i = s.next(i);
      }
      s.slice(String.begin, i)
    }

    let startsWithText(s: String, prefix: String): Boolean {
      var i = String.begin;
      var j = String.begin;
      while (s.hasIndex(i) && prefix.hasIndex(j) && s[i] == prefix[j]) {
        i = s.next(i);
        j = prefix.next(j);
      }
      !prefix.hasIndex(j)
    }

    let shownText(s: String, decoding: Boolean): String {
      if (decoding) { decodeForDisplay(s) } else { s }
    }

## Decoding for Display

Decodes each run of escapes in `s` as UTF-8, keeping as escapes any
bytes that aren't a whole, well-formed sequence for a code point safe
to show (`isShownDecoded`), and all escaped ASCII. Since every code
point decoded is beyond ASCII, which every part escapes, parsing the
result gives back the same escapes.

    let decodeForDisplay(s: String): String {
      if (s.split("%").length == 1) {
        return s;
      }
      let out = new StringBuilder();
      var decodedBefore = false;
      var i = String.begin;
      while (s.hasIndex(i)) {
        let byte = escapedByte(s, i);
        if (byte < 0x80) {
          if (byte < 0) {
            appendCode(out, s[i]);
            i = s.next(i);
          } else {
            out.append(s.slice(i, escapeAfter(s, i)));
            i = escapeAfter(s, i);
          }
          decodedBefore = false;
        } else {
          let code = utf8At(s, i);
          if (code >= 0 && isShownDecoded(code, decodedBefore)) {
            appendCode(out, code);
            decodedBefore = true;
            i = escapesAfter(s, i, utf8Length(byte));
          } else {
            out.append(s.slice(i, escapeAfter(s, i)));
            decodedBefore = false;
            i = escapeAfter(s, i);
          }
        }
      }
      out.toString()
    }

The byte escaped at `i`, as `%` and two hex digits, or -1 if there's no
escape there.

    let escapedByte(s: String, i: StringIndex): Int {
      if (s[i] != char'%') {
        -1
      } else {
        let first = s.next(i);
        let second = if (s.hasIndex(first)) { s.next(first) } else { first };
        if (!s.hasIndex(second)) {
          -1
        } else {
          let high = hexValue(s[first]);
          let low = hexValue(s[second]);
          if (high < 0 || low < 0) { -1 } else { high * 16 + low }
        }
      }
    }

    let escapeAfter(s: String, i: StringIndex): StringIndex {
      s.next(s.next(s.next(i)))
    }

    let escapesAfter(s: String, i: StringIndex, count: Int): StringIndex {
      var j = i;
      for (var k = 0; k < count && s.hasIndex(j); k += 1) {
        j = escapeAfter(s, j);
      }
      j
    }

How many bytes a UTF-8 sequence starting with `byte` has, or 1 for a
byte that can't start one.

    let utf8Length(byte: Int): Int {
      if (byte >= 0xC2 && byte <= 0xDF) {
        2
      } else if (byte >= 0xE0 && byte <= 0xEF) {
        3
      } else if (byte >= 0xF0 && byte <= 0xF4) {
        4
      } else {
        1
      }
    }

The code point that escapes from `i` spell in UTF-8, or -1 if they
don't spell one whole, in its shortest form, and not a surrogate.

    let utf8At(s: String, i: StringIndex): Int {
      let first = escapedByte(s, i);
      let length = utf8Length(first);
      if (length == 1) {
        return -1;
      }
      // The lead byte's payload: 5, 4, or 3 bits. (Not `0x7F >> length`,
      // which Temper's Rust backend can't compile, as of 2026-10-30.)
      var code = first & (if (length == 2) { 0x1F } else if (length == 3) { 0xF } else { 0x7 });
      var j = escapeAfter(s, i);
      for (var k = 1; k < length; k += 1) {
        let byte = if (s.hasIndex(j)) { escapedByte(s, j) } else { -1 };
        if (byte < 0x80 || byte > 0xBF) {
          return -1;
        }
        code = (code << 6) | (byte & 0x3F);
        j = escapeAfter(s, j);
      }
      let shortest = if (length == 3) { code >= 0x800 } else if (length == 4) { code >= 0x10000 } else { true };
      if (shortest && code <= 0x10FFFF && (code < 0xD800 || code > 0xDFFF)) { code } else { -1 }
    }

Whether code point `c`, beyond ASCII, is safe to show decoded: valid in
a domain name, as IDNA's mapping table says, which leaves out controls,
spaces, format characters such as bidi controls, private use,
noncharacters, and unassigned code points; but not the joiners
U+200C and U+200D, which are invisible, nor a few that look like the
URL's own delimiters, a padlock, or nothing (`isLookalikeSymbol`); and a
combining mark only after other decoded text.

    let isShownDecoded(c: Int, decodedBefore: Boolean): Boolean {
      isValidCode(c) && c != 0x200C && c != 0x200D && !isLookalikeSymbol(c) &&
        (decodedBefore || (properties(c) & markBit) == 0)
    }

Code points that look like a URL's `/`, `\`, `?`, or `#`, a padlock
or key, or blank space, which Chromium's and Firefox's decoders also
keep escaped, as far as their documentation shows. Most aren't valid in
domain names anyway; they're listed so the rule doesn't hang on that.

    let isLookalikeSymbol(c: Int): Boolean {
      when (c) {
        0x115F, 0x1160, 0x3164, 0xFFA0, 0x2800,
        0x0338, 0x20E5, 0x2044, 0x2215, 0x2216, 0x2571, 0x2572, 0x29F5, 0x29F8, 0x29F9,
        0x3033, 0xFE68, 0xFF0F, 0xFF3C, 0xFF03, 0xFF1F, 0xFE16, 0xFE56, 0xFE5F,
        0x1F50F, 0x1F510, 0x1F511, 0x1F512, 0x1F513 -> true;
        else -> false;
      }
    }

## Domains for Display

Converts `domain` to Unicode, label by label, where browsers would show
that label in Unicode, and keeps the `xn--` form elsewhere, against
look-alike spoofs such as `xn--pple-43d.com`, which is Cyrillic `а` and
Latin `pple`. **Never for security decisions:** a label shown in
Unicode can still look like another; decide on the ASCII form.

A label is shown in Unicode if, as Chromium's and Firefox's IDN display
policies decide each label (see the [plan](../docs/plan.md), "Display
formatting", for each rule's source):

- it converts to Unicode and back to the same `xn--` label, so it's
  valid IDNA, in normal form;
- every code point is an ASCII letter, digit, or hyphen, or a Latin
  letter of modern European languages or Vietnamese
  (`latinLetterRanges`), so it's in one script, Latin, which both
  browsers' profiles show, and has no combining marks, digits from other
  scripts, invisible characters, or IPA and historic letters. Labels in
  other scripts keep `xn--` for now, until Hrefine has Unicode's Script
  and identifier data to check mixed scripts and whole-script look-alikes
  as browsers do;
- it has no Latin letter that looks like a plain ASCII one
  (`isLatinLookalike`), such as dotless `ı` or small capital `ᴏ`;
- and it follows Chromium's rules for single letters: no `ß`, which
  older IDNA mapped to `ss`, so the label could name another domain;
  `þ` and `ð`, which look like `p` and `o`, only under `.is`; and the
  schwa `ə` only under `.az`.

Hrefine doesn't check labels against a list of popular domains, as
Chromium does, so a Latin label can show in Unicode, such as
`gõogle.com`, where Chromium keeps `xn--`.

A domain that isn't valid stays as it is, lowercased.

    export let domainToDisplay(domain: String): String {
      let ascii = domainToAscii(domain) orelse asciiLowercase(domain);
      if (!hasXnLabel(ascii)) {
        return ascii;
      }
      let labels = ascii.split(".");
      // The top-level domain, ignoring a trailing dot.
      var tld = "";
      for (var k = labels.length - 1; tld == "" && k >= 0; k -= 1) {
        tld = labels[k];
      }
      labels.join(".") { label => labelToDisplay(label, tld) }
    }

    let labelToDisplay(label: String, tld: String): String {
      if (!startsWithText(label, "xn--")) {
        return label;
      }
      let unicode = domainToUnicode(label);
      let back = domainToAscii(unicode) orelse "";
      if (back == label && isShownLabel(unicode, tld)) { unicode } else { label }
    }

    let isShownLabel(label: String, tld: String): Boolean {
      var shown = true;
      for (var i = String.begin; shown && label.hasIndex(i); i = label.next(i)) {
        let c = label[i];
        shown = if (c < 0x80) {
          (c >= char'a' && c <= char'z') || isDigit(c) || c == char'-'
        } else {
          isLatinLetter(c) && !isLatinLookalike(c) && isShownForTld(c, tld)
        };
      }
      shown
    }

Chromium's rules for single Latin letters: `ß` (U+00DF), a deviation
character, is never shown, since IDNA 2003 mapped it to `ss`; thorn `þ`
and eth `ð` only under Iceland's `.is`; and the schwa `ə` only under
Azerbaijan's `.az`.

    let isShownForTld(c: Int, tld: String): Boolean {
      when (c) {
        0xDF -> false;
        0xFE, 0xF0 -> tld == "is";
        0x259 -> tld == "az";
        else -> true;
      }
    }

Whether `c` is in `latinLetterRanges`, by binary search.

    let isLatinLetter(c: Int): Boolean {
      let ranges = latinLetterRanges;
      var low = 0;
      var high = ranges.length / 2;
      while (low < high) {
        let middle = (low + high) / 2;
        let last = ranges[middle * 2 + 1];
        if (c > last) {
          low = middle + 1;
        } else {
          high = middle;
        }
      }
      if (low * 2 < ranges.length) {
        let first = ranges[low * 2];
        c >= first
      } else {
        false
      }
    }

Latin letters that look like a plain ASCII letter, so a label with one
keeps `xn--`. A small, hand-picked list, since Hrefine doesn't have
Unicode's confusables data: dotless `ı` and `ȷ`; `ɑ`, `ɡ`, and `ɩ`,
which look like `a`, `g`, and `i`; the clicks `ǀ`, `ǁ`, and `ǃ`, which
look like `l`, `ll`, and `!`; `ĸ`, `ħ`, `ŧ`, `ƅ`, and `ŋ`, which
Chromium adds to Unicode's look-alikes of `k`, `h`, `t`, `b`, and `n`;
and the small capitals, which look like capital ASCII letters.

    let isLatinLookalike(c: Int): Boolean {
      when (c) {
        0x0131, 0x0237, 0x0251, 0x0261, 0x0269, 0x01C0, 0x01C1, 0x01C3,
        0x0138, 0x0127, 0x0167, 0x0185, 0x014B,
        0x1D00, 0x0299, 0x1D04, 0x1D05, 0x1D07, 0xA730, 0x0262, 0x029C, 0x026A, 0x1D0A,
        0x1D0B, 0x029F, 0x1D0D, 0x0274, 0x1D0F, 0x1D18, 0xA7AF, 0x0280, 0xA731, 0x1D1B,
        0x1D1C, 0x1D20, 0x1D21, 0x028F, 0x1D22 -> true;
        else -> false;
      }
    }

## Tests

Domains as browsers would show them: Latin labels in Unicode, and the
rest kept as `xn--`: Cyrillic `а` with Latin `pple` (mixed scripts),
all-Cyrillic `аррӏе` (a whole-script spoof), Greek `ο` in `gοοgle`,
Latin look-alikes of ASCII letters (dotless `ı`, small capital `ᴏ`,
kra, and script `ɡ`), IPA `ɐ`, `ß`, `þ` and `ə` outside `.is` and
`.az`, other scripts (for now), and a label that isn't in normal form.

    test("domains for display") {
      let shown = [
        "bücher.example", "münchen.de", "café.example", "www.bücher.café",
        "Bücher.Example", "Example.COM", "xn--a.example", "țară.ro", "việt.vn",
        "þing.is", "əla.az", "əla.az.",
      ];
      for (var k = 0; k < shown.length; k += 1) {
        let lower = domainToUnicode(domainToAscii(shown[k]) orelse panic());
        let got = domainToDisplay(shown[k]);
        assert(got == lower) { "${shown[k]}: ${got}" };
        assert(domainToDisplay(domainToAscii(shown[k]) orelse panic()) == lower);
      }
      let kept = [
        "\u{430}pple.com", "\u{430}\u{440}\u{440}\u{4CF}\u{435}.com", "g\u{3BF}\u{3BF}gle.com",
        "l\u{131}nkedin.com", "g\u{1D0F}\u{1D0F}gle.com", "\u{138}ayak.com", "\u{261}ithub.com",
        "日本語.jp", "пример.рф", "مثال.example", "faß.de", "\u{250}pple.com", "þing.com",
        "ðing.example", "əla.com",
      ];
      for (var k = 0; k < kept.length; k += 1) {
        let ascii = domainToAscii(kept[k]) orelse panic();
        assert(domainToDisplay(kept[k]) == ascii) { "${kept[k]}: ${domainToDisplay(kept[k])}" };
      }
      assert(domainToDisplay("xn--pple-43d.com") == "xn--pple-43d.com");
      assert(domainToDisplay("bücher.\u{440}\u{444}") == "bücher.xn--p1ai");
      // A label not in normal form, e and a combining acute, keeps xn--.
      let decomposed = new StringBuilder();
      decomposed.append("xn--");
      punycodeEncode([0x63, 0x61, 0x66, 0x65, 0x301], decomposed) orelse panic();
      let label = decomposed.toString();
      assert(domainToDisplay("${label}.example") == "${label}.example") { label };
    }

Formatting a URL, with each option.

    test("display format") {
      let cases = [
        "https://xn--bcher-kva.example:8080/caf%C3%A9?q=%E6%97%A5%E6%9C%AC#%C3%BC",
        "https://bücher.example:8080/café?q=日本#ü",
        "https://xn--pple-43d.com/",
        "https://xn--pple-43d.com/",
        "https://example.com/a%2Fb%20c%25d?x=%3D",
        "https://example.com/a%2Fb%20c%25d?x=%3D",
        "https://example.com/%E2%80%AEtxt.exe%E2%80%8B%E2%88%95x",
        "https://example.com/%E2%80%AEtxt.exe%E2%80%8B%E2%88%95x",
        "https://example.com/%C3x%C3%A9%ED%A0%80%C0%AF",
        "https://example.com/%C3xé%ED%A0%80%C0%AF",
        "https://example.com/a%CC%81%C3%A9%CC%81",
        "https://example.com/a%CC%81é\u{301}",
        "https://example.com/%F0%9F%94%92%F0%9F%98%80",
        "https://example.com/%F0%9F%94%92\u{1F600}",
        "mailto:J%C3%BCrgen@example.com",
        "mailto:Jürgen@example.com",
        "web+demo:/.//not-a-host/",
        "web+demo:/.//not-a-host/",
        "http://[::1]:8080/",
        "http://[::1]:8080/",
      ];
      for (var k = 0; k < cases.length; k += 2) {
        let url = parseUrl(cases[k]) orelse panic();
        let got = UrlDisplay.addressBar.format(url);
        assert(got == cases[k + 1]) { "${cases[k]}: ${got}" };
        let back = parseUrl(got) orelse panic();
        assert(back.href == url.href) { "${got} parses back to ${back.href}" };
      }
      let withAll = parseUrl("https://user:pw@xn--bcher-kva.example/?#top") orelse panic();
      let bare = parseUrl("https://xn--bcher-kva.example/#top") orelse panic();
      let quiet = UrlDisplay.addressBar.withFragment(false).withRootSlash(false);
      assert(quiet.format(withAll) == "https://bücher.example/?");
      assert(quiet.format(bare) == "https://bücher.example");
      assert(UrlDisplay.addressBar.withRootSlash(false).format(bare) == "https://bücher.example/#top");
      let ascii = UrlDisplay.addressBar.withUnicodeHosts(false).withDecoding(false);
      let encoded = parseUrl("https://xn--bcher-kva.example/caf%C3%A9") orelse panic();
      assert(ascii.format(encoded) == encoded.href);
      let opaque = parseUrl("foo:x") orelse panic();
      assert(UrlDisplay.addressBar.withRootSlash(false).format(opaque) == "foo:x") { "opaque" };
    }

Credentials: never by default, and with them, the username but never
the password.

    test("display hides credentials") {
      let cases = [
        "https://alice:hunter2@example.com/", "https://example.com/", "https://alice:***@example.com/",
        "https://TOKEN@example.com/", "https://example.com/", "https://TOKEN@example.com/",
        "https://:hunter2@example.com/", "https://example.com/", "https://:***@example.com/",
        "https://:@example.com/", "https://example.com/", "https://example.com/",
        "foo://alice:hunter2@h/", "foo://h/", "foo://alice:***@h/",
      ];
      let shown = UrlDisplay.addressBar.withCredentials(true);
      for (var k = 0; k < cases.length; k += 3) {
        let url = parseUrl(cases[k]) orelse panic();
        let hidden = UrlDisplay.addressBar.format(url);
        assert(hidden == cases[k + 1]) { "${cases[k + 1]} hidden" };
        assert(shown.format(url) == cases[k + 2]) { "${cases[k + 2]} shown" };
        assert(shown.withCredentials(false).format(url) == hidden) { "off again" };
        let all = shown.withUnicodeHosts(false).withDecoding(false).format(url);
        assert(all.split("hunter2").length == 1) { "never the password" };
        assert(hidden.split("alice").length == 1 && hidden.split("TOKEN").length == 1) {
          "no username by default"
        };
      }
    }

The README's examples.

    test("README display examples") {
      let shown = UrlDisplay.addressBar.withRootSlash(false);
      let url = parseUrl("https://user@xn--bcher-kva.example/") orelse panic();
      assert(shown.format(url) == "https://bücher.example");
      assert(domainToDisplay("xn--pple-43d.com") == "xn--pple-43d.com");
      let page = parseUrl("https://user@EXAMPLE.com:443/a/../b?q=1#top") orelse panic();
      assert(page.sameDocument(page.withHash("other")));
      assert(!(page == page.withHash("other")));
      assert(page.sameDocument(parseUrl("https://user@example.com/b?q=1") orelse panic()));
      assert(!page.sameDocument(parseUrl("https://user@example.com/b?q=2") orelse panic()));
      let source = parseUrlSource(" https://EXAMPLE.com/a\tb") orelse panic();
      let host = source.hostSpan;
      assert(host != null && host.asWritten == "EXAMPLE.com" && host.start == 9 && host.length == 11);
      assert(source.url.href == "https://example.com/ab") { "decisions use url" };
      assert(page.toString() == "https://***@example.com/b?q=1#top");
      assert(page.withoutCredentials().href == "https://example.com/b?q=1#top");
      let policy = UrlPolicy.fetch.withHosts(["example.com"], true);
      assert(policy.check("https://api.example.com/").url != null);
      assert(
        policy.check("https://127.0.0.1/").toString() ==
          "specialHost: 127.0.0.1 is loopback (RFC 1122), in 127.0.0.0/8"
      );
    }
