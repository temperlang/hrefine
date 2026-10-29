# Percent-Encoding

The URL Standard's [percent-encoded
bytes](https://url.spec.whatwg.org/#percent-encoded-bytes) section: each
part of a URL escapes a different set of code points, as `%` and two
uppercase hex digits for each of their UTF-8 bytes, so `é` becomes
`%C3%A9`. Code points outside the part's set are kept as they are,
including `%` itself, so text that's already escaped stays escaped.

## Encode Sets

The standard defines each set by adding to the one before, and so does
`inEncodeSet`. Each set is a number here, from smallest to largest:

- The **C0 control percent-encode set:** C0 controls (U+0000 to U+001F)
  and everything past `~` (U+007E), for opaque paths and opaque hosts.
- The **fragment percent-encode set:** the C0 control set, space, `"`,
  `<`, `>`, and `` ` ``.
- The **query percent-encode set:** the C0 control set, space, `"`, `#`,
  `<`, and `>`. (Not `` ` ``, so it's not quite a superset of the
  fragment set.)
- The **special-query percent-encode set:** the query set and `'`, for
  queries of special URLs, such as `http`.
- The **path percent-encode set:** the query set, `?`, `^`, `` ` ``,
  `{`, and `}`.
- The **userinfo percent-encode set:** the path set, `/`, `:`, `;`, `=`,
  `@`, `[` to `^`, and `|`.

<!-- -->

    let c0ControlSet = 0;
    let fragmentSet = 1;
    let querySet = 2;
    let specialQuerySet = 3;
    let pathSet = 4;
    let userinfoSet = 5;

Whether code point `c` is in encode set `set`. Most code points in most
URLs are letters and digits, which no set holds, so those return early.

    let inEncodeSet(c: Int, set: Int): Boolean {
      if (c < 0x20 || c > 0x7E) {
        return true;
      }
      if (
        (c >= char'a' && c <= char'z') || (c >= char'A' && c <= char'Z') ||
        (c >= char'0' && c <= char'9')
      ) {
        return false;
      }
      if (set == c0ControlSet) {
        return false;
      }
      if (set == fragmentSet) {
        return c == char' ' || c == char'"' || c == char'<' || c == char'>' || c == char'`';
      }
      if (c == char' ' || c == char'"' || c == char'#' || c == char'<' || c == char'>') {
        return true;
      }
      if (set == querySet) {
        return false;
      }
      if (set == specialQuerySet) {
        return c == char'\'';
      }
      if (c == char'?' || c == char'^' || c == char'`' || c == char'{' || c == char'}') {
        return true;
      }
      if (set == pathSet) {
        return false;
      }
      // The userinfo set: `[`, `\`, and `]` are U+005B to U+005D; `^` is
      // already in.
      c == char'/' || c == char':' || c == char';' || c == char'=' || c == char'@' ||
        (c >= 0x5B && c <= 0x5D) || c == char'|'
    }

## Encoding

[UTF-8 percent-encode](https://url.spec.whatwg.org/#utf-8-percent-encode)
code point `c` using encode set `set`, onto `out`: escaped as its UTF-8
bytes if it's in the set, or else as it is.

    let percentEncodeOnto(out: StringBuilder, c: Int, set: Int): Void {
      if (!inEncodeSet(c, set)) {
        appendCode(out, c);
      } else if (c < 0x80) {
        appendByte(out, c);
      } else if (c < 0x800) {
        appendByte(out, 0xC0 | (c >> 6));
        appendByte(out, 0x80 | (c & 0x3F));
      } else if (c < 0x10000) {
        appendByte(out, 0xE0 | (c >> 12));
        appendByte(out, 0x80 | ((c >> 6) & 0x3F));
        appendByte(out, 0x80 | (c & 0x3F));
      } else {
        appendByte(out, 0xF0 | (c >> 18));
        appendByte(out, 0x80 | ((c >> 12) & 0x3F));
        appendByte(out, 0x80 | ((c >> 6) & 0x3F));
        appendByte(out, 0x80 | (c & 0x3F));
      }
    }

The same for every code point in `s`.

    let percentEncodeString(s: String, set: Int): String {
      let out = new StringBuilder();
      for (var i = String.begin; s.hasIndex(i); i = s.next(i)) {
        percentEncodeOnto(out, s[i], set);
      }
      out.toString()
    }

One byte as `%` and two uppercase hex digits.

    let appendByte(out: StringBuilder, byte: Int): Void {
      out.append("%");
      appendCode(out, hexDigitFor(byte >> 4));
      appendCode(out, hexDigitFor(byte & 0xF));
    }

    let hexDigitFor(n: Int): Int {
      if (n < 10) { char'0' + n } else { char'A' + n - 10 }
    }

Code points from strings are always Unicode scalar values, so appending
one can't fail.

    let appendCode(out: StringBuilder, c: Int): Void {
      out.appendCodePoint(c) orelse panic();
    }

## Decoding

[Percent-decode](https://url.spec.whatwg.org/#percent-decode) a string
into bytes, for hosts: each `%` and two hex digits becomes that byte, and
every other code point becomes its UTF-8 bytes. A `%` without two hex
digits after it stays as it is.

    let percentDecode(s: String): List<Int> {
      let bytes = new ListBuilder<Int>();
      var i = String.begin;
      while (s.hasIndex(i)) {
        let c = s[i];
        if (c == char'%') {
          let j = s.next(i);
          let k = if (s.hasIndex(j)) { s.next(j) } else { j };
          if (s.hasIndex(j) && s.hasIndex(k)) {
            let high = hexValue(s[j]);
            let low = hexValue(s[k]);
            if (high >= 0 && low >= 0) {
              bytes.add(high * 16 + low);
              i = s.next(k);
              continue;
            }
          }
          bytes.add(c);
        } else if (c < 0x80) {
          bytes.add(c);
        } else if (c < 0x800) {
          bytes.add(0xC0 | (c >> 6));
          bytes.add(0x80 | (c & 0x3F));
        } else if (c < 0x10000) {
          bytes.add(0xE0 | (c >> 12));
          bytes.add(0x80 | ((c >> 6) & 0x3F));
          bytes.add(0x80 | (c & 0x3F));
        } else {
          bytes.add(0xF0 | (c >> 18));
          bytes.add(0x80 | ((c >> 12) & 0x3F));
          bytes.add(0x80 | ((c >> 6) & 0x3F));
          bytes.add(0x80 | (c & 0x3F));
        }
        i = s.next(i);
      }
      bytes.toList()
    }

[UTF-8 decode without
BOM](https://encoding.spec.whatwg.org/#utf-8-decode-without-bom) bytes
into a string, as the Encoding Standard's UTF-8 decoder does: each bad
sequence becomes U+FFFD, and a byte that can't continue the sequence
before it starts the next one. A byte order mark stays, as U+FEFF.

    let utf8Decode(bytes: List<Int>): String {
      let out = new StringBuilder();
      var needed = 0;
      var seen = 0;
      var code = 0;
      var lower = 0x80;
      var upper = 0xBF;
      var k = 0;
      while (k < bytes.length) {
        let byte = bytes[k];
        if (needed == 0) {
          if (byte < 0x80) {
            appendCode(out, byte);
          } else if (byte >= 0xC2 && byte <= 0xDF) {
            needed = 1;
            code = byte & 0x1F;
          } else if (byte >= 0xE0 && byte <= 0xEF) {
            if (byte == 0xE0) { lower = 0xA0; }
            if (byte == 0xED) { upper = 0x9F; }
            needed = 2;
            code = byte & 0xF;
          } else if (byte >= 0xF0 && byte <= 0xF4) {
            if (byte == 0xF0) { lower = 0x90; }
            if (byte == 0xF4) { upper = 0x8F; }
            needed = 3;
            code = byte & 0x7;
          } else {
            appendCode(out, 0xFFFD);
          }
          k += 1;
          continue;
        }
        if (byte < lower || byte > upper) {

Not a continuation here: the sequence so far is bad, and this byte
starts again, so it isn't consumed.

          needed = 0;
          seen = 0;
          code = 0;
          lower = 0x80;
          upper = 0xBF;
          appendCode(out, 0xFFFD);
          continue;
        }
        lower = 0x80;
        upper = 0xBF;
        code = (code << 6) | (byte & 0x3F);
        seen += 1;
        if (seen == needed) {
          appendCode(out, code);
          needed = 0;
          seen = 0;
          code = 0;
        }
        k += 1;
      }
      if (needed != 0) {
        appendCode(out, 0xFFFD);
      }
      out.toString()
    }

The value of hex digit `c`, in either case, or -1 if it isn't one.

    let hexValue(c: Int): Int {
      if (c >= char'0' && c <= char'9') {
        c - char'0'
      } else if (c >= char'a' && c <= char'f') {
        c - char'a' + 10
      } else if (c >= char'A' && c <= char'F') {
        c - char'A' + 10
      } else {
        -1
      }
    }
