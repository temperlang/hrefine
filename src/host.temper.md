# Hosts

The URL Standard's [hosts](https://url.spec.whatwg.org/#hosts-(domains-and-ip-addresses))
section: a URL's host is a domain, an IPv4 address, an IPv6 address, an
opaque host (for URLs that aren't special, such as `foo://host`), or
empty. Each kind parses differently, and serializes to a string. Since
nothing here needs a host's kind after parsing, the parser returns the
host serialized, as the URL's getters give it: `example.com`,
`127.0.0.1`, `[::1]`.

## Host Parsing

The [host parser](https://url.spec.whatwg.org/#concept-host-parser)
takes the text between the `//` and the path, minus any user, password,
and port, and whether it's opaque (the URL isn't special). Bracketed
input is an IPv6 address; opaque input is an opaque host; anything else
is a domain, after percent-decoding, unless it ends in a number, as
`127.0.0.1` and `0x7f.1` do, which makes it an IPv4 address.

    let parseHost(input: String, isOpaque: Boolean): String throws Bubble {
      if (input.hasIndex(String.begin) && input[String.begin] == char'[') {
        let last = input.prev(input.end);
        if (input[last] != char']' || last == String.begin) {
          bubble();
        }
        return "[${serializeIpv6(parseIpv6(input.slice(input.next(String.begin), last)))}]";
      }
      if (isOpaque) {
        return parseOpaqueHost(input);
      }

The standard decodes the percent-decoded bytes as UTF-8 (without a byte
order mark), which gives a string beyond ASCII if any byte is past
U+007F. Domains beyond ASCII need [IDNA](#international-domain-names),
which comes in step 2 of the [plan](../docs/plan.md), so for now they
fail to parse.

      let bytes = percentDecode(input);
      let domain = new StringBuilder();
      for (var k = 0; k < bytes.length; k += 1) {
        let byte = bytes[k];
        if (byte >= 0x80) {
          bubble();
        }
        appendCode(domain, byte);
      }
      let asciiDomain = domainToAscii(domain.toString());
      if (endsInANumber(asciiDomain)) {
        serializeIpv4(parseIpv4(asciiDomain))
      } else {
        asciiDomain
      }
    }

## International Domain Names

[Domain to ASCII](https://url.spec.whatwg.org/#concept-domain-to-ascii)
runs UTS #46's ToASCII, which maps and checks Unicode labels and encodes
them with Punycode, as `xn--` labels. The standard notes that for an
ASCII domain with no label starting with `xn--` (in any case), ToASCII
only lowercases it, and that's all this does so far: other domains,
which need the full mapping and Punycode, fail to parse until step 2.
After that, an empty result, or one with a [forbidden domain code
point](#forbidden-code-points), fails.

    let domainToAscii(domain: String): String throws Bubble {
      let out = new StringBuilder();
      var labelStart = true;
      var i = String.begin;
      while (domain.hasIndex(i)) {
        let c = domain[i];
        if (labelStart && startsWithXnDashes(domain, i)) {
          bubble();
        }
        labelStart = c == char'.';
        appendCode(out, if (c >= char'A' && c <= char'Z') { c + 32 } else { c });
        i = domain.next(i);
      }
      let result = out.toString();
      if (result.isEmpty) {
        bubble();
      }
      for (var j = String.begin; result.hasIndex(j); j = result.next(j)) {
        if (isForbiddenDomainCode(result[j])) {
          bubble();
        }
      }
      result
    }

Whether `s` has `xn--`, in any case, at `i`.

    let startsWithXnDashes(s: String, i: StringIndex): Boolean {
      let x = i;
      if (!s.hasIndex(x) || (s[x] | 0x20) != char'x') { return false; }
      let n = s.next(x);
      if (!s.hasIndex(n) || (s[n] | 0x20) != char'n') { return false; }
      let d1 = s.next(n);
      if (!s.hasIndex(d1) || s[d1] != char'-') { return false; }
      let d2 = s.next(d1);
      s.hasIndex(d2) && s[d2] == char'-'
    }

## Forbidden Code Points

A [forbidden host code
point](https://url.spec.whatwg.org/#forbidden-host-code-point) can't be
in any host: U+0000, tab, newline, carriage return, space, `#`, `/`,
`:`, `<`, `>`, `?`, `@`, `[`, `\`, `]`, `^`, and `|`.

    let isForbiddenHostCode(c: Int): Boolean {
      c == 0 || c == 0x9 || c == 0xA || c == 0xD || c == char' ' || c == char'#' ||
        c == char'/' || c == char':' || c == char'<' || c == char'>' || c == char'?' ||
        c == char'@' || c == char'[' || c == 0x5C || c == char']' || c == char'^' ||
        c == char'|'
    }

A [forbidden domain code
point](https://url.spec.whatwg.org/#forbidden-domain-code-point) can't
be in a domain: those, any C0 control, `%`, and U+007F.

    let isForbiddenDomainCode(c: Int): Boolean {
      isForbiddenHostCode(c) || c <= 0x1F || c == char'%' || c == 0x7F
    }

## Opaque Hosts

The [opaque-host parser](https://url.spec.whatwg.org/#concept-opaque-host-parser)
fails on a forbidden host code point, and otherwise escapes controls and
code points past ASCII, with the C0 control percent-encode set.

    let parseOpaqueHost(input: String): String throws Bubble {
      for (var i = String.begin; input.hasIndex(i); i = input.next(i)) {
        if (isForbiddenHostCode(input[i])) {
          bubble();
        }
      }
      percentEncodeString(input, c0ControlSet)
    }

## IPv4

A domain [ends in a number](https://url.spec.whatwg.org/#ends-in-a-number-checker)
if its last label, ignoring one trailing dot, is all decimal digits or
parses as an IPv4 number, as `0x7f` does. Then it must be an IPv4
address, or it fails: `1.2.3.09` fails, since `09` is a bad octal
number.

    let endsInANumber(input: String): Boolean {
      let parts = input.split(".").toListBuilder();
      if (parts[parts.length - 1] == "") {
        if (parts.length == 1) {
          return false;
        }
        parts.removeLast();
      }
      let last = parts[parts.length - 1];
      if (last != "" && allDigits(last)) {
        return true;
      }
      ipv4NumberOrNegative(last) >= 0i64
    }

    let allDigits(s: String): Boolean {
      for (var i = String.begin; s.hasIndex(i); i = s.next(i)) {
        let c = s[i];
        if (c < char'0' || c > char'9') {
          return false;
        }
      }
      true
    }

The [IPv4 parser](https://url.spec.whatwg.org/#concept-ipv4-parser)
takes one to four numbers, separated by dots, with an optional trailing
dot. Each but the last is a byte, and the last fills the bytes left, so
`127.1` is `127.0.0.1`, and `2130706433` is too. The address is a
32-bit number, so it's an `Int64` here, since `Int` is signed 32-bit.

    let parseIpv4(input: String): Int64 throws Bubble {
      let parts = input.split(".").toListBuilder();
      if (parts[parts.length - 1] == "" && parts.length > 1) {
        parts.removeLast();
      }
      let count = parts.length;
      if (count > 4) {
        bubble();
      }
      var ipv4 = 0i64;
      for (var k = 0; k < count - 1; k += 1) {
        let n = parseIpv4Number(parts[k]);
        if (n > 255i64) {
          bubble();
        }
        ipv4 = (ipv4 << 8) | n;
      }
      let last = parseIpv4Number(parts[count - 1]);
      let bytesLeft = 5 - count;

The last number must fit in the bytes left, so shifting them out leaves
zero. (Comparing with `1i64 << (8 * bytesLeft)` would read better, but
Temper's Java backend writes `1i64` as an `int`, so the shift wraps.)

      if ((last >> (8 * bytesLeft)) != 0i64) {
        bubble();
      }
      (ipv4 << (8 * bytesLeft)) | last
    }

An [IPv4 number](https://url.spec.whatwg.org/#ipv4-number-parser) is
decimal, octal after a leading `0`, or hex after `0x` or `0X`; `0x`
alone is 0. Numbers can have any number of digits, so past 2³² this
stops growing, which is enough to make the address fail.

    let parseIpv4Number(input: String): Int64 throws Bubble {
      let n = ipv4NumberOrNegative(input);
      if (n < 0i64) {
        bubble();
      }
      n
    }

The same, but -1 where it fails, for checking without bubbling.

    let ipv4NumberOrNegative(input: String): Int64 {
      if (input.isEmpty) {
        return -1i64;
      }
      var radix = 10;
      var i = String.begin;
      let second = input.next(i);
      if (input.hasIndex(second)) {
        if (input[i] == char'0') {
          let x = input[second];
          if (x == char'x' || x == char'X') {
            radix = 16;
            i = input.next(second);
          } else {
            radix = 8;
            i = second;
          }
        }
      }
      var value = 0i64;
      while (input.hasIndex(i)) {
        let digit = hexValue(input[i]);
        if (digit < 0 || digit >= radix) {
          return -1i64;
        }
        if (value <= 0xFFFF_FFFFi64) {
          value = value * radix.toInt64() + digit.toInt64();
        }
        i = input.next(i);
      }
      value
    }

The [IPv4 serializer](https://url.spec.whatwg.org/#concept-ipv4-serializer)
writes the four bytes in decimal, separated by dots.

    let serializeIpv4(address: Int64): String {
      let a = ((address >> 24) & 255i64).toInt32Unsafe();
      let b = ((address >> 16) & 255i64).toInt32Unsafe();
      let c = ((address >> 8) & 255i64).toInt32Unsafe();
      let d = (address & 255i64).toInt32Unsafe();
      "${a.toString()}.${b.toString()}.${c.toString()}.${d.toString()}"
    }

## IPv6

The [IPv6 parser](https://url.spec.whatwg.org/#concept-ipv6-parser)
reads eight 16-bit pieces of up to four hex digits each, where `::`
stands for one or more pieces of zeros (once at most), and the last two
pieces may be written as an IPv4 address in plain dotted decimal, as in
`::ffff:192.0.2.1`. It works on a list of code points, as the standard
does, since it looks back and ahead.

    let parseIpv6(text: String): List<Int> throws Bubble {
      let input = new ListBuilder<Int>();
      for (var i = String.begin; text.hasIndex(i); i = text.next(i)) {
        input.add(text[i]);
      }
      let length = input.length;
      let at(p: Int): Int { if (p < length) { input[p] } else { -1 } }
      let address = [0, 0, 0, 0, 0, 0, 0, 0].toListBuilder();
      var pieceIndex = 0;
      var compress = -1;
      var pointer = 0;
      if (at(pointer) == char':') {
        if (at(pointer + 1) != char':') {
          bubble();
        }
        pointer += 2;
        pieceIndex += 1;
        compress = pieceIndex;
      }
      while (at(pointer) != -1) {
        if (pieceIndex == 8) {
          bubble();
        }
        if (at(pointer) == char':') {
          if (compress != -1) {
            bubble();
          }
          pointer += 1;
          pieceIndex += 1;
          compress = pieceIndex;
          continue;
        }
        var value = 0;
        var digits = 0;
        while (digits < 4 && hexValue(at(pointer)) >= 0) {
          value = value * 0x10 + hexValue(at(pointer));
          pointer += 1;
          digits += 1;
        }
        if (at(pointer) == char'.') {

An IPv4 address in the last two pieces: four decimal numbers, each a
byte, without leading zeros.

          if (digits == 0) {
            bubble();
          }
          pointer -= digits;
          if (pieceIndex > 6) {
            bubble();
          }
          var numbersSeen = 0;
          while (at(pointer) != -1) {
            var ipv4Piece = -1;
            if (numbersSeen > 0) {
              if (at(pointer) == char'.' && numbersSeen < 4) {
                pointer += 1;
              } else {
                bubble();
              }
            }
            if (!isDigit(at(pointer))) {
              bubble();
            }
            while (isDigit(at(pointer))) {
              let number = at(pointer) - char'0';
              if (ipv4Piece == -1) {
                ipv4Piece = number;
              } else if (ipv4Piece == 0) {
                bubble();
              } else {
                ipv4Piece = ipv4Piece * 10 + number;
              }
              if (ipv4Piece > 255) {
                bubble();
              }
              pointer += 1;
            }
            address[pieceIndex] = address[pieceIndex] * 0x100 + ipv4Piece;
            numbersSeen += 1;
            if (numbersSeen == 2 || numbersSeen == 4) {
              pieceIndex += 1;
            }
          }
          if (numbersSeen != 4) {
            bubble();
          }
          break;
        } else if (at(pointer) == char':') {
          pointer += 1;
          if (at(pointer) == -1) {
            bubble();
          }
        } else if (at(pointer) != -1) {
          bubble();
        }
        address[pieceIndex] = value;
        pieceIndex += 1;
      }

With `::`, the pieces after it move to the end, leaving zeros between.
Without it, there must be eight pieces.

      if (compress != -1) {
        var swaps = pieceIndex - compress;
        pieceIndex = 7;
        while (pieceIndex != 0 && swaps > 0) {
          let other = compress + swaps - 1;
          let piece = address[pieceIndex];
          address[pieceIndex] = address[other];
          address[other] = piece;
          pieceIndex -= 1;
          swaps -= 1;
        }
      } else if (pieceIndex != 8) {
        bubble();
      }
      address.toList()
    }

    let isDigit(c: Int): Boolean { c >= char'0' && c <= char'9' }

The [IPv6 serializer](https://url.spec.whatwg.org/#concept-ipv6-serializer)
writes each piece in lowercase hex without leading zeros, and the first
longest run of two or more zero pieces as `::`.

    let serializeIpv6(address: List<Int>): String {
      var compress = -1;
      var bestLength = 1;
      var k = 0;
      while (k < 8) {
        if (address[k] == 0) {
          var end = k;
          while (end < 8 && address[end] == 0) {
            end += 1;
          }
          if (end - k > bestLength) {
            compress = k;
            bestLength = end - k;
          }
          k = end;
        } else {
          k += 1;
        }
      }
      let out = new StringBuilder();
      var ignore0 = false;
      for (var pieceIndex = 0; pieceIndex < 8; pieceIndex += 1) {
        if (ignore0 && address[pieceIndex] == 0) {
          continue;
        }
        ignore0 = false;
        if (compress == pieceIndex) {
          out.append(if (pieceIndex == 0) { "::" } else { ":" });
          ignore0 = true;
          continue;
        }
        appendHex(out, address[pieceIndex]);
        if (pieceIndex != 7) {
          out.append(":");
        }
      }
      out.toString()
    }

Lowercase hex, without leading zeros, written out so every backend
agrees on case.

    let appendHex(out: StringBuilder, n: Int): Void {
      var started = false;
      for (var shift = 12; shift >= 0; shift -= 4) {
        let digit = (n >> shift) & 0xF;
        if (started || digit != 0 || shift == 0) {
          started = true;
          appendCode(out, if (digit < 10) { char'0' + digit } else { char'a' + digit - 10 });
        }
      }
    }
