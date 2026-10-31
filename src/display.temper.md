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

A label is shown in Unicode, as Chromium's IDN display policy decides
each label (Firefox's is much the same; see the
[plan](../docs/plan.md), "Display formatting", for each rule's source),
only if:

- it converts to Unicode and back to the same `xn--` label, so it's
  valid IDNA, in normal form;
- every code point is allowed in identifiers (Unicode's Identifier
  Status), less what Chromium leaves out (such as Pinyin, Greek
  Extended, and the deviation characters `ß`, `ς`, and the joiners,
  which older IDNA mapped differently);
- it's in one script, or Latin with Han and kana, or Latin with Han and
  Hangul (UTS #39's Highly Restrictive), with each code point's
  Script Extensions, and Common and Inherited code points going with any
  script;
- its decimal digits are from one numbering system, and no mark is
  repeated;
- thorn `þ` and eth `ð`, which look like `p` and `o`, are only under
  `.is` and `.fo`, the schwa `ə` only under `.az`, and the middle dot
  `·` only under `.cat`, between two `l`s, as in Catalan's `l·l`;
- it has no Latin letter that looks like an ASCII one, such as dotless
  `ı`;
- it isn't all digits and letters that look like digits, such as
  Bengali `৪`;
- in one script, it isn't all letters that look like ASCII letters and
  digits (a whole-script look-alike, such as Cyrillic `аррӏе`), unless
  its top-level domain is in that script, or is one Chromium allows for
  it, such as `.ru` for Cyrillic, or it's one of the words Chromium
  allows, such as `как`;
- and, in more than one script, or with kana that can look like other
  kana or accents, a Latin letter beyond ASCII mixes only with Latin,
  Greek, and Cyrillic, and it has none of Chromium's dangerous patterns
  (`hasDangerousPattern`), such as Katakana `ノ` between Latin letters.

The tables of scripts, identifier status, and look-alikes are generated
from Unicode's data (see `display-tables.temper.md`). Hrefine doesn't
check labels against a list of popular domains, as Chromium does, so a
label can show in Unicode, such as `gõogle.com`, where Chromium keeps
`xn--`.

A domain that isn't valid stays as it is, lowercased.

    export let domainToDisplay(domain: String): String {
      let ascii = domainToAscii(domain) orelse asciiLowercase(domain);
      if (!hasXnLabel(ascii)) {
        return ascii;
      }
      let labels = ascii.split(".");
      // The top-level domain, as Chromium takes it: after the last dot,
      // so none after a trailing dot.
      let tld = labels[labels.length - 1];
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

The checks, on the label's code points and their kinds from the tables,
in Chromium's order.

    let isShownLabel(label: String, tld: String): Boolean {
      let codes = new ListBuilder<Int>();
      let masks = new ListBuilder<Int>();
      let flags = new ListBuilder<Int>();
      for (var i = String.begin; label.hasIndex(i); i = label.next(i)) {
        let c = label[i];
        let kind = displayKind(c);
        if (kind == 0 || !isShownForTld(c, tld)) {
          return false;
        }
        codes.add(c);
        masks.add(displayKinds[kind * 2]);
        flags.add(displayKinds[kind * 2 + 1]);
      }
      let scripts = resolvedScripts(masks.toList());
      if (scripts == 0) {
        return false;
      }
      let codeList = codes.toList();
      let maskList = masks.toList();
      let flagList = flags.toList();
      if (
        hasMixedNumbers(codeList, flagList) || hasUnsafeMiddleDot(codeList, tld) ||
          hasLatinLookalike(maskList, flagList) || isDigitLookalike(codeList, flagList)
      ) {
        return false;
      }
      if (scripts > 0 && isWholeScriptLookalike(label, flagList, scripts, tld)) {
        return false;
      }
      (scripts > 0 && !hasJapaneseOrMarks(codeList)) ||
        (!mixesLatin(codeList, maskList) && !hasDangerousPattern(codeList, maskList))
    }

Thorn `þ` and eth `ð` only under Iceland's `.is` and the Faroe Islands'
`.fo`, and the schwa `ə` only under Azerbaijan's `.az`, as Chromium
allows them. Chromium allows one alone as a label anywhere; Hrefine
doesn't, since it has no popular domains to check `þ.com` against.

    let isShownForTld(c: Int, tld: String): Boolean {
      when (c) {
        0xFE, 0xF0 -> tld == "is" || tld == "fo";
        0x259 -> tld == "az";
        else -> true;
      }
    }

The middle dot only under `.cat`, between two `l`s.

    let hasUnsafeMiddleDot(codes: List<Int>, tld: String): Boolean {
      let last = codes.length - 1;
      for (var k = 0; k <= last; k += 1) {
        if (
          codes[k] == 0xB7 &&
            (tld != "cat" || k == 0 || k == last || codes[k - 1] != char'l' || codes[k + 1] != char'l')
        ) {
          return true;
        }
      }
      false
    }

UTS #39's Highly Restrictive level, from each code point's scripts as
bits (0 for any script): the scripts all the code points share, as a
positive number of bits, if any (Han, kana, and Hangul code points have
bits for Japanese or Korean writing too, so Han and kana share
Japanese); or else -1 if the label is Latin with Han and kana, or Latin
with Han and Hangul; or else 0, for a label that isn't shown. (UTS #39's
third set, Latin with Han and Bopomofo, adds nothing, since Unicode 18
doesn't allow Bopomofo letters in identifiers.)

    let resolvedScripts(masks: List<Int>): Int {
      var shared = 0x3FFFFFFF;
      var japanese = true;
      var korean = true;
      let base = scriptLatin | scriptHan;
      for (var k = 0; k < masks.length; k += 1) {
        let mask = masks[k];
        if (mask != 0) {
          shared = shared & mask;
          japanese = japanese && (mask & (base | scriptHiragana | scriptKatakana)) != 0;
          korean = korean && (mask & (base | scriptHangul)) != 0;
        }
      }
      if (shared != 0) {
        shared
      } else if (japanese || korean) {
        -1
      } else {
        0
      }
    }

Whether the label has decimal digits from two numbering systems, such
as ASCII `1` and Arabic-Indic `٢`, or a mark twice in a row, which can
draw as one (ICU's mixed numbers and invisible checks).

    let hasMixedNumbers(codes: List<Int>, flags: List<Int>): Boolean {
      var zero = 0;
      for (var k = 0; k < codes.length; k += 1) {
        let digit = flags[k] >> 4;
        if (digit != 0) {
          if (zero != 0 && zero != digit) {
            return true;
          }
          zero = digit;
        }
        if (k > 0 && (flags[k] & 2) != 0 && codes[k] == codes[k - 1]) {
          return true;
        }
      }
      false
    }

Whether the label has a Latin letter that looks like an ASCII one. This
is stricter than Chromium, which keeps `xn--` only where such letters
make the label look like a popular domain.

    let hasLatinLookalike(masks: List<Int>, flags: List<Int>): Boolean {
      for (var k = 0; k < masks.length; k += 1) {
        if ((flags[k] & 1) != 0 && (masks[k] & scriptLatin) != 0) {
          return true;
        }
      }
      false
    }

Whether the label is all ASCII digits and code points that look like
digits, with at least one of those, under any top-level domain. Hrefine
also lets hyphens in, which Chromium doesn't.

    let isDigitLookalike(codes: List<Int>, flags: List<Int>): Boolean {
      var any = false;
      for (var k = 0; k < codes.length; k += 1) {
        if ((flags[k] & 4) != 0) {
          any = true;
        } else if (!isDigit(codes[k]) && codes[k] != char'-') {
          return false;
        }
      }
      any
    }

Whether a label in one script but Latin is a whole-script look-alike:
its letters, ignoring Common and Inherited code points (such as digits,
hyphens, and accents), all look like ASCII letters or digits, under a
top-level domain not in that script nor one Chromium allows for it, and
it's not one of the words Chromium allows. Chromium checks Armenian,
Bengali, Cyrillic, Devanagari, Ethiopic, Georgian, Greek, Gujarati,
Gurmukhi, Hebrew, Kannada, Malayalam, Myanmar, Oriya, Tamil, Telugu,
and Thai, each with its own list of letters, and the tables mark those
letters, and those that Unicode's confusables map to ASCII. Chromium
skips this check on a label with accents or certain kana, where its
popular domains check takes over; Hrefine doesn't.

    let isWholeScriptLookalike(label: String, flags: List<Int>, scripts: Int, tld: String): Boolean {
      var any = false;
      for (var k = 0; k < flags.length; k += 1) {
        if ((flags[k] & 8) == 0) {
          if ((flags[k] & 1) == 0) {
            return false;
          }
          any = true;
        }
      }
      any && (scripts & scriptLatin) == 0 && !isTldForScripts(tld, scripts) &&
        !isListed(allowedWholeScriptWords, label)
    }

    let isTldForScripts(tld: String, scripts: Int): Boolean {
      let unicode = domainToUnicode(tld);
      for (var i = String.begin; unicode.hasIndex(i); i = unicode.next(i)) {
        let kind = displayKind(unicode[i]);
        if (kind != 0 && (displayKinds[kind * 2] & scripts) != 0) {
          return true;
        }
      }
      for (var k = 0; k < wholeScriptTldScripts.length; k += 1) {
        if ((scripts & wholeScriptTldScripts[k]) != 0 && isListed(wholeScriptTlds[k], tld)) {
          return true;
        }
      }
      false
    }

    let isListed(texts: List<String>, text: String): Boolean {
      for (var k = 0; k < texts.length; k += 1) {
        if (texts[k] == text) {
          return true;
        }
      }
      false
    }

The top-level domains Chromium allows whole-script look-alikes under,
for each script it checks that has some, and the Cyrillic words it
allows anywhere, which look like no Latin words.

    let wholeScriptTldScripts: List<Int> = [
      scriptArmenian, scriptCyrillic, scriptEthiopic, scriptGeorgian, scriptGreek,
      scriptHebrew, scriptMyanmar, scriptThai,
    ];
    let wholeScriptTlds: List<List<String>> = [
      ["am"], ["bg", "by", "kz", "pyc", "ru", "su", "ua", "uz"], ["er", "et"], ["ge"], ["gr"],
      ["il"], ["mm"], ["th"],
    ];
    let allowedWholeScriptWords: List<String> = [
      "секс", "как", "коса", "курс", "парк", "такий", "укроп", "сахарок", "покраска",
      "театр", "астро", "пхукет",
    ];

Whether a Latin letter beyond ASCII mixes with anything but Latin,
Greek, Cyrillic, ASCII digits, hyphens, and the accents U+0300 to U+0339.

    let mixesLatin(codes: List<Int>, masks: List<Int>): Boolean {
      var latin = false;
      var other = false;
      let lgc = scriptLatin | scriptGreek | scriptCyrillic;
      for (var k = 0; k < codes.length; k += 1) {
        let c = codes[k];
        let mask = masks[k];
        if (c >= 0x80 && mask == scriptLatin) {
          latin = true;
        } else if (
          !isDigit(c) && c != char'-' && (c < 0x300 || c > 0x339) &&
          (mask == 0 || (mask & lgc) != mask)
        ) {
          other = true;
        }
      }
      latin && other
    }

Chromium looks for dangerous patterns only in labels of more than one
script, or with kana that can look like other kana or accents.

    let hasJapaneseOrMarks(codes: List<Int>): Boolean {
      for (var k = 0; k < codes.length; k += 1) {
        let c = codes[k];
        if (
          (c >= 0x3078 && c <= 0x307A) || (c >= 0x30D8 && c <= 0x30DA) ||
          (c >= 0x30FB && c <= 0x30FE) || (c >= 0x300 && c <= 0x339)
        ) {
          return true;
        }
      }
      false
    }

Chromium's dangerous patterns, where "Japanese" is Hiragana, Katakana,
or Han (and Bopomofo, which no shown code point has alone):

- Katakana `ノ`, `ン`, `ソ`, and `ゾ`, and Han `丶`, `乀`, `乁`, and `丿`,
  which look like slashes, between two code points not Japanese;
- Han and Bopomofo that look like Latin letters or punctuation, such as
  `一`, `七`, `十`, `〇`, and `工`, beside one not Japanese;
- the iteration marks `ヽ` and `ヾ` first or after no Katakana, and the
  prolonged sound mark `ー` first or after no kana;
- Hiragana `へ`, `べ`, or `ぺ` inside an otherwise Katakana label, and
  Katakana `ヘ`, `ベ`, or `ペ` inside an otherwise Hiragana one, since
  they look the same;
- the middle dot `・` last, or beside one not Japanese;
- the combining kana voicing marks;
- and an accent U+0300 to U+0339 after a code point not Latin, Greek,
  or Cyrillic, or after dotless `ı`, and dot above after `i`, `j`, or
  `l`.

Each needs a code point before or after it where it says "beside" or
"after", as Chromium's patterns do.

    let hasDangerousPattern(codes: List<Int>, masks: List<Int>): Boolean {
      let japanese = scriptHiragana | scriptKatakana | scriptHan;
      let lgc = scriptLatin | scriptGreek | scriptCyrillic;
      let last = codes.length - 1;
      for (var k = 0; k <= last; k += 1) {
        let c = codes[k];
        let hasBefore = k > 0;
        let hasAfter = k < last;
        let before = if (hasBefore) { codes[k - 1] } else { -1 };
        let beforeMask = if (hasBefore) { masks[k - 1] } else { 0 };
        let afterMask = if (hasAfter) { masks[k + 1] } else { 0 };
        let notJapaneseBefore = hasBefore && (beforeMask & japanese) == 0;
        let notJapaneseAfter = hasAfter && (afterMask & japanese) == 0;
        let dangerous = if (isListedCode(slashLookalikes, c) && notJapaneseBefore && notJapaneseAfter) {
          true
        } else if (isListedCode(cjkLookalikes, c) && (notJapaneseBefore || notJapaneseAfter)) {
          true
        } else if (c >= 0x3078 && c <= 0x307A) {
          hasBefore && hasAfter && allOthersHave(masks, k, scriptKatakana)
        } else if (c >= 0x30D8 && c <= 0x30DA) {
          hasBefore && hasAfter && allOthersHave(masks, k, scriptHiragana)
        } else if (c >= 0x300 && c <= 0x339) {
          hasBefore && ((beforeMask & lgc) == 0 || before == 0x131) ||
            c == 0x307 && (before == char'i' || before == char'j' || before == char'l')
        } else {
          when (c) {
            0x30FD, 0x30FE -> (beforeMask & scriptKatakana) == 0;
            0x30FC -> (beforeMask & (scriptHiragana | scriptKatakana)) == 0;
            0x30FB -> notJapaneseBefore || !hasAfter || notJapaneseAfter;
            0x3099, 0x309A -> true;
            else -> false;
          }
        };
        if (dangerous) {
          return true;
        }
      }
      false
    }

    let slashLookalikes: List<Int> = [
      0x30CE, 0x30F3, 0x30BD, 0x30BE, 0x4E36, 0x4E40, 0x4E41, 0x4E3F,
    ];
    let cjkLookalikes: List<Int> = [
      0x4E00, 0x3127, 0x4E28, 0x4E5B, 0x4E03, 0x4E05, 0x5341, 0x3007, 0x3112, 0x311A,
      0x311F, 0x3128, 0x3129, 0x3108, 0x31BA, 0x31B3, 0x5DE5, 0x31B2, 0x8BA0, 0x4E01,
      0x4E36, 0x4E85, 0x4E8C, 0x4EA0, 0x5196, 0x5B80, 0x5DDB,
    ];

    let isListedCode(codes: List<Int>, c: Int): Boolean {
      for (var k = 0; k < codes.length; k += 1) {
        if (codes[k] == c) {
          return true;
        }
      }
      false
    }

    let allOthersHave(masks: List<Int>, k: Int, script: Int): Boolean {
      for (var j = 0; j < masks.length; j += 1) {
        if (j != k && (masks[j] & script) == 0) {
          return false;
        }
      }
      true
    }

The kind of code point `c`, from the tables: 0 if a label holding it
isn't shown, and otherwise an index into `displayKinds`, read where the
tables are, a block at a time. A block's string holds runs of a length
and a kind, base 32 digits as in the IDNA tables, and the last run's
length is 0.

    let displayKind(c: Int): Int {
      let b = c >> displayBlockShift;
      if (b >= displayBlocks.length) {
        return 0;
      }
      let entry = displayBlocks[b];
      if (entry >= 0) {
        return entry;
      }
      let text = displayRuns[-1 - entry];
      var offset = c & ((1 << displayBlockShift) - 1);
      var i = String.begin;
      var value = 0;
      var length = -1;
      var result = -1;
      while (result < 0) {
        let d = text[i];
        i = text.next(i);
        value = (value << 5) | (d & 0x1F);
        if (d < 0x60) {
          if (length < 0) {
            length = value;
          } else if (length == 0 || offset < length) {
            result = value;
          } else {
            offset -= length;
            length = -1;
          }
          value = 0;
        }
      }
      result
    }

## Tests

Domains as browsers would show them, a rule at a time. Shown: Latin
labels of modern languages; Japanese (Han, kana, and Latin with kana),
Chinese, and Korean; Cyrillic `пример`; Greek, Armenian, Georgian,
Arabic, Hebrew, Hindi, and Thai, and Arabic-Indic digits; a whole-script
look-alike under its own script's top-level domain or one Chromium
allows (`.рф`, `.ru`); and `þ` under `.is` and `ə` under `.az`.

    test("domains for display") {
      let shown = [
        "bücher.example", "münchen.de", "café.example", "www.bücher.café",
        "Bücher.Example", "Example.COM", "xn--a.example", "țară.ro", "việt.vn",
        "þing.is", "əla.az", "日本語.jp", "ひらがな.jp", "カタカナ.jp",
        "日本ひらがな.jp", "abcカタカナ.jp", "sony日本.jp", "中文.cn",
        "한국어.kr", "abc한국어.kr", "пример.рф", "пример.com", "ελληνικά.gr",
        "հայերեն.am", "ქართული.ge", "مثال.example", "مثال١٢٣.example", "שלום.il",
        "हिन्दी.in", "ไทย.th", "\u{430}\u{440}\u{440}\u{4CF}\u{435}.рф",
        "\u{430}\u{440}\u{440}\u{4CF}\u{435}.ru", "bücher-123.example",
      ];
      for (var k = 0; k < shown.length; k += 1) {
        let lower = domainToUnicode(domainToAscii(shown[k]) orelse panic());
        let got = domainToDisplay(shown[k]);
        assert(got == lower) { "${shown[k]}: ${got}" };
        assert(domainToDisplay(domainToAscii(shown[k]) orelse panic()) == lower) { shown[k] };
      }

Kept as `xn--`, by rule: mixed scripts (Cyrillic `а` with Latin
`pple`, Greek `ο` in `gοοgle`, Latin with Cyrillic or Greek, Hangul
with kana, and Arabic with Hebrew); whole-script look-alikes
(Cyrillic `аррӏе` and `ѕсоре`, Greek `ναι`, and Bengali digit
look-alikes); Latin look-alikes of ASCII letters (dotless `ı`, and
Chromium's `ħ`); code points not allowed in identifiers (small capital
`ᴏ`, kra, script `ɡ`, IPA `ɐ`, the symbol `♥`, and Bopomofo, which
Unicode 18 limits) or that Chromium leaves out (Pinyin's `ǎ`, Latin
Extended Additional's `ḿ`, and Greek Extended's `ἀ`); the deviation `ß`, and `ς`; digits from two numbering
systems; a non-ASCII Latin letter with kana; Chromium's dangerous
patterns (Katakana `ノ` beside Latin, `ー` after Latin, `・` beside a
Latin letter, and a dot above after `i`, or an accent after Han); `þ` and
`ə` outside `.is` and `.az`; and a label that isn't in normal form.

      let kept = [
        "\u{430}pple.com", "\u{430}\u{440}\u{440}\u{4CF}\u{435}.com", "g\u{3BF}\u{3BF}gle.com",
        "abcпример.com", "abcελληνικά.com", "ひらがな한국.example", "مثالשלום.example",
        "\u{455}\u{441}\u{43E}\u{440}\u{435}.com", "\u{3BD}\u{3B1}\u{3B9}.com", "\u{9EA}\u{9ED}.com",
        "l\u{131}nkedin.com", "\u{127}otel.com", "g\u{1D0F}\u{1D0F}gle.com", "\u{138}ayak.com",
        "\u{261}ithub.com", "\u{250}pple.com", "i\u{2665}u.com", "注音ㄅㄆ.tw", "p\u{1CE}nyin.cn",
        "\u{1E3F}a.com", "\u{1F00}\u{3B8}\u{3B7}\u{3BD}\u{3B1}.gr", "faß.de", "\u{3C3}\u{3BF}\u{3C6}\u{3CC}\u{3C2}.gr",
        "\u{939}\u{93F}1\u{967}.in", "caféカタカナ.jp", "abc\u{30CE}def.com", "abc\u{30FC}.com",
        "abc\u{30FB}def.jp", "\u{30AB}\u{30BF}i\u{307}.jp", "日本\u{301}.jp", "þing.com",
        "ðing.example", "əla.com",
      ];
      for (var k = 0; k < kept.length; k += 1) {
        let ascii = domainToAscii(kept[k]) orelse panic();
        assert(domainToDisplay(kept[k]) == ascii) { "${kept[k]}: ${domainToDisplay(kept[k])}" };
      }
      assert(domainToDisplay("xn--pple-43d.com") == "xn--pple-43d.com");
      assert(domainToDisplay("bücher.\u{440}\u{444}") == "bücher.рф");
      // A label not in normal form, e and a combining acute, keeps xn--.
      let decomposed = new StringBuilder();
      decomposed.append("xn--");
      punycodeEncode([0x63, 0x61, 0x66, 0x65, 0x301], decomposed) orelse panic();
      let label = decomposed.toString();
      assert(domainToDisplay("${label}.example") == "${label}.example") { label };
    }

Each rule checked against Chromium's source (see the plan), shown and
kept in pairs where it can be.

    test("display rules from Chromium") {
      let shown = [
        // þ and ð under .fo too; the middle dot under .cat, between ls.
        "þing.fo", "ðing.fo", "col·legi.cat", "pàl·lid.cat",
        // Whole-script look-alikes: Chromium's allowed words, and under
        // the script's own top-level domains (Thai, Ethiopic, Myanmar).
        "\u{43A}\u{430}\u{43A}.com", "\u{441}\u{435}\u{43A}\u{441}.com", "\u{E17}\u{E19}\u{E1A}.th",
        "\u{1200}\u{1220}.et", "\u{1001}\u{1002}.mm", "ไทย.com",
        // Iteration mark after Katakana, ・ between kana, a slash look-alike
        // at a label's end, Katakana ヘ among Katakana, and Han 十 with Han.
        "abc\u{30AB}\u{30FD}.jp", "\u{30AB}\u{30BF}\u{30FB}\u{30AB}\u{30CA}.jp", "abc\u{30CE}.jp",
        "\u{30D8}\u{30EB}\u{30D7}.jp", "\u{5341}\u{5206}.cn",
      ];
      for (var k = 0; k < shown.length; k += 1) {
        let lower = domainToUnicode(domainToAscii(shown[k]) orelse panic());
        assert(domainToDisplay(shown[k]) == lower) { "${shown[k]}: ${domainToDisplay(shown[k])}" };
      }
      let kept = [
        // After a trailing dot, the top-level domain is empty, as in Chromium.
        "əla.az.", "þing.is.", "\u{430}\u{440}\u{440}\u{4CF}\u{435}.ru.",
        // The middle dot elsewhere.
        "col·legi.com", "a·la.cat", "·ll.cat", "ll·.cat",
        // Whole-script look-alikes from Chromium's lists: Cyrillic мк,
        // Thai (Linux's list), Ethiopic, Gujarati, and Myanmar.
        "\u{43C}\u{43A}.com", "\u{E17}\u{E19}\u{E1A}.com", "\u{1200}\u{1220}.com", "\u{AA1}\u{A9F}.com",
        "\u{1001}\u{1002}.com",
        // Digit look-alikes under any top-level domain, and Chromium's з.
        "\u{437}1.ru", "\u{437}1.com",
        // Iteration marks after no Katakana; へ among Katakana and ヘ among
        // Hiragana; ・ last or by a digit; Han that looks like Latin by Latin.
        "ab\u{30FD}.jp", "\u{30FD}\u{30AB}.jp", "\u{30AB}\u{3078}\u{30AB}.jp", "\u{3072}\u{30D8}\u{3072}.jp",
        "\u{30AB}\u{30FB}.jp", "1\u{30FB}\u{30AB}.jp", "ab\u{5DE5}.cn", "\u{5341}ab.cn",
      ];
      for (var k = 0; k < kept.length; k += 1) {
        let ascii = domainToAscii(kept[k]) orelse panic();
        assert(domainToDisplay(kept[k]) == ascii) { "${kept[k]}: ${domainToDisplay(kept[k])}" };
      }
      // Bengali digit look-alikes, even under a Bengali top-level domain.
      let digits = domainToAscii("\u{9EA}\u{9ED}") orelse panic();
      let bangla = "\u{9AC}\u{9BE}\u{982}\u{9B2}\u{9BE}";
      assert(domainToDisplay("\u{9EA}\u{9ED}.${bangla}") == "${digits}.${bangla}") { digits };
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
