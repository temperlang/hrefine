# Punycode

[Punycode](https://www.rfc-editor.org/rfc/rfc3492) (RFC 3492) writes a
Unicode label in ASCII letters, digits, and hyphens, as international
domain names do after `xn--`: `bücher` is `bcher-kva`. The ASCII code
points come first, then a hyphen if there were any, and then each other
code point as a variable-length number in base 36, giving where it goes
and what it is, as a delta from the one before.

These work on lists of code points, as [IDNA](idna.temper.md) does, and
bubble where RFC 3492 fails: on a bad digit, a truncated number, a
number past `Int`'s range, or a result that isn't a Unicode scalar
value.

    let punycodeBase = 36;
    let punycodeTMin = 1;
    let punycodeTMax = 26;
    let punycodeSkew = 38;
    let punycodeDamp = 700;
    let punycodeInitialBias = 72;
    let punycodeInitialN = 0x80;
    let maxInt = 0x7FFF_FFFF;

## Decoding

Decodes `input` from `start` on (just past the `xn--`), which must be
ASCII. Everything before the last hyphen is the ASCII code points, as
they are, and the rest says where to insert the others.

    let punycodeDecode(input: List<Int>, start: Int): List<Int> throws Bubble {
      var delimiter = -1;
      for (var k = start; k < input.length; k += 1) {
        if (input[k] == char'-') {
          delimiter = k;
        }
      }
      let output = new ListBuilder<Int>();
      for (var k = start; k < delimiter; k += 1) {
        output.add(input[k]);
      }
      var at = if (delimiter >= 0) { delimiter + 1 } else { start };
      var n = punycodeInitialN;
      var i = 0;
      var bias = punycodeInitialBias;
      while (at < input.length) {
        let oldI = i;
        var w = 1;
        var k = punycodeBase;
        while (true) {
          if (at >= input.length) {
            bubble();
          }
          let digit = punycodeDigitValue(input[at]);
          at += 1;
          if (digit < 0 || digit > (maxInt - i) / w) {
            bubble();
          }
          i += digit * w;
          let t = punycodeThreshold(k, bias);
          if (digit < t) {
            break;
          }
          if (w > maxInt / (punycodeBase - t)) {
            bubble();
          }
          w *= punycodeBase - t;
          k += punycodeBase;
        }
        let count = output.length + 1;
        bias = punycodeAdapt(i - oldI, count, oldI == 0);
        if (i / count > maxInt - n) {
          bubble();
        }
        n += i / count;
        i = i % count;
        if (n > 0x10FFFF || (n >= 0xD800 && n <= 0xDFFF)) {
          bubble();
        }
        output.splice(i, 0, [n]);
        i += 1;
      }
      output.toList()
    }

A digit's value: `a` to `z` (in either case) are 0 to 25, and `0` to `9`
are 26 to 35; anything else is -1.

    let punycodeDigitValue(c: Int): Int {
      if (c >= char'a' && c <= char'z') {
        c - char'a'
      } else if (c >= char'A' && c <= char'Z') {
        c - char'A'
      } else if (c >= char'0' && c <= char'9') {
        c - char'0' + 26
      } else {
        -1
      }
    }

The threshold for the digit at position `k`, which ends a number when
the digit is below it.

    let punycodeThreshold(k: Int, bias: Int): Int {
      if (k <= bias + punycodeTMin) {
        punycodeTMin
      } else if (k >= bias + punycodeTMax) {
        punycodeTMax
      } else {
        k - bias
      }
    }

Bias adaptation, after each code point, so the next number's digits
fit the size of the deltas so far.

    let punycodeAdapt(delta: Int, count: Int, first: Boolean): Int throws Bubble {
      var d = if (first) { delta / punycodeDamp } else { delta / 2 };
      d += d / count;
      var k = 0;
      while (d > ((punycodeBase - punycodeTMin) * punycodeTMax) / 2) {
        d = d / (punycodeBase - punycodeTMin);
        k += punycodeBase;
      }
      k + ((punycodeBase - punycodeTMin + 1) * d) / (d + punycodeSkew)
    }

## Encoding

Encodes `input` onto `out`, in lowercase.

    let punycodeEncode(input: List<Int>, out: StringBuilder): Void throws Bubble {
      var basic = 0;
      for (var k = 0; k < input.length; k += 1) {
        if (input[k] < 0x80) {
          appendCode(out, input[k]);
          basic += 1;
        }
      }
      if (basic > 0) {
        out.append("-");
      }
      var n = punycodeInitialN;
      var delta = 0;
      var bias = punycodeInitialBias;
      var handled = basic;
      while (handled < input.length) {

The smallest code point not yet handled.

        var m = maxInt;
        for (var k = 0; k < input.length; k += 1) {
          if (input[k] >= n && input[k] < m) {
            m = input[k];
          }
        }
        if (m - n > (maxInt - delta) / (handled + 1)) {
          bubble();
        }
        delta += (m - n) * (handled + 1);
        n = m;
        for (var k = 0; k < input.length; k += 1) {
          let c = input[k];
          if (c < n) {
            if (delta == maxInt) {
              bubble();
            }
            delta += 1;
          }
          if (c == n) {
            var q = delta;
            var j = punycodeBase;
            while (true) {
              let t = punycodeThreshold(j, bias);
              if (q < t) {
                break;
              }
              appendCode(out, punycodeDigit(t + (q - t) % (punycodeBase - t)));
              q = (q - t) / (punycodeBase - t);
              j += punycodeBase;
            }
            appendCode(out, punycodeDigit(q));
            bias = punycodeAdapt(delta, handled + 1, handled == basic);
            delta = 0;
            handled += 1;
          }
        }
        delta += 1;
        n += 1;
      }
    }

    let punycodeDigit(d: Int): Int {
      if (d < 26) { char'a' + d } else { char'0' + d - 26 }
    }

## Tests

RFC 3492's own samples, among others.

    test("Punycode") {
      let roundTrip(unicode: String, encoded: String): Void {
        let codes = new ListBuilder<Int>();
        for (var i = String.begin; unicode.hasIndex(i); i = unicode.next(i)) {
          codes.add(unicode[i]);
        }
        let out = new StringBuilder();
        punycodeEncode(codes.toList(), out) orelse panic();
        assert(out.toString() == encoded) { "${unicode} encodes as ${out.toString()}" };
        let ascii = new ListBuilder<Int>();
        for (var i = String.begin; encoded.hasIndex(i); i = encoded.next(i)) {
          ascii.add(encoded[i]);
        }
        let decoded = punycodeDecode(ascii.toList(), 0) orelse panic();
        let back = String.fromCodePoints(decoded) orelse panic();
        assert(back == unicode) { "${encoded} decodes as ${back}" };
      }
      roundTrip("bücher", "bcher-kva");
      roundTrip("ß", "zca");
      roundTrip("\u{4ED6}\u{4EEC}\u{4E3A}\u{4EC0}\u{4E48}\u{4E0D}\u{8BF4}\u{4E2D}\u{6587}", "ihqwcrb4cv8a8dqg056pqjye");
      roundTrip("\u{0644}\u{064A}\u{0647}\u{0645}\u{0627}\u{0628}\u{062A}\u{0643}\u{0644}\u{0645}\u{0648}\u{0634}\u{0639}\u{0631}\u{0628}\u{064A}\u{061F}", "egbpdaj6bu4bxfgehfvwxn");
      roundTrip("3\u{5E74}B\u{7D44}\u{91D1}\u{516B}\u{5148}\u{751F}", "3B-ww4c5e180e575a65lsy2b");
      roundTrip("\u{1F600}", "e28h");
      roundTrip("", "");
      let codes(s: String): List<Int> {
        let out = new ListBuilder<Int>();
        for (var i = String.begin; s.hasIndex(i); i = s.next(i)) {
          out.add(s[i]);
        }
        out.toList()
      }
      let valid: List<Int>? = punycodeDecode(codes("a"), 0) orelse null;
      assert(valid != null);  // U+0080: not valid in a domain, but valid Punycode.
      let truncated: List<Int>? = punycodeDecode(codes("z"), 0) orelse null;
      let truncatedFails = truncated == null;  // Not in `assert`, for a Temper bug.
      assert(truncatedFails);
      let notDigit: List<Int>? = punycodeDecode(codes("a!"), 0) orelse null;
      let notDigitFails = notDigit == null;  // Not in `assert`, for a Temper bug.
      assert(notDigitFails);
      let tooBig: List<Int>? = punycodeDecode(codes("zzzzzzzzzzzzzz"), 0) orelse null;
      let tooBigFails = tooBig == null;  // Not in `assert`, for a Temper bug.
      assert(tooBigFails);
    }
