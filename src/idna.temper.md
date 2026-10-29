# International Domain Names

The URL Standard's [domain to
ASCII](https://url.spec.whatwg.org/#concept-domain-to-ascii) and [domain
to Unicode](https://url.spec.whatwg.org/#concept-domain-to-unicode), which
run [UTS #46](https://www.unicode.org/reports/tr46/)'s ToASCII and
ToUnicode with the options the standard sets: nontransitional processing
(so `ß` stays `ß`), CheckBidi and CheckJoiners on, and CheckHyphens,
UseSTD3ASCIIRules, and VerifyDnsLength off. Each maps a domain's code
points (lowercasing, among much else), normalizes them to NFC, splits
them into labels at dots, and checks each label, decoding `xn--` labels
from [Punycode](punycode.temper.md) first. ToASCII then encodes each
label beyond ASCII as `xn--` and Punycode, and fails on any error.

The Unicode data is in [generated tables](idna-tables.temper.md).

## Domain to ASCII

Converts `domain` to ASCII, as the URL Standard's domain to ASCII does,
without its strict option: `Bücher.example` becomes
`xn--bcher-kva.example`. It bubbles where the standard fails, as on a
disallowed code point or an empty result. A domain that's already ASCII
is only lowercased, even with `xn--` labels that wouldn't decode, as
browsers do.

    export let domainToAscii(domain: String): String throws Bubble {
      if (domain.isEmpty) {
        bubble();
      }
      if (isAsciiString(domain)) { asciiLowercase(domain) } else { internationalToAscii(domain) }
    }

    let internationalToAscii(domain: String): String throws Bubble {
      let labels = new ListBuilder<List<Int>>();
      if (!processDomain(domain, true, labels)) {
        bubble();
      }
      let out = new StringBuilder();
      for (var k = 0; k < labels.length; k += 1) {
        if (k > 0) {
          out.append(".");
        }
        let label = labels[k];
        if (isAsciiLabel(label)) {
          for (var j = 0; j < label.length; j += 1) {
            appendCode(out, label[j]);
          }
        } else {
          out.append("xn--");
          punycodeEncode(label, out);
        }
      }
      let result = out.toString();
      if (result.isEmpty) {
        bubble();
      }
      result
    }

## Domain to Unicode

Converts `domain` to Unicode, for showing it, as the URL Standard's
domain to Unicode does: `xn--bcher-kva.example` becomes
`bücher.example`. It never fails: as UTS #46's ToUnicode says, labels
with errors are converted as far as they can be, and an `xn--` label
that isn't Punycode stays as it is. Use domain to ASCII to check a
domain. An ASCII domain without `xn--` labels is only lowercased, as
processing would do, without needing the tables.

    export let domainToUnicode(domain: String): String {
      if (isAsciiString(domain) && !hasXnLabel(domain)) {
        asciiLowercase(domain)
      } else {
        internationalToUnicode(domain)
      }
    }

    let internationalToUnicode(domain: String): String {
      let labels = new ListBuilder<List<Int>>();
      processDomain(domain, false, labels);
      let out = new StringBuilder();
      for (var k = 0; k < labels.length; k += 1) {
        if (k > 0) {
          out.append(".");
        }
        let label = labels[k];
        for (var j = 0; j < label.length; j += 1) {
          appendCode(out, label[j]);
        }
      }
      out.toString()
    }

## Processing

UTS #46's [processing](https://www.unicode.org/reports/tr46/#Processing)
of `domain`, onto `labels`, each a list of code points. It returns
whether there were no errors. For ToASCII (`forAscii`), it stops at the
first error, since any fails the whole domain.

    let processDomain(
      domain: String, forAscii: Boolean, labels: ListBuilder<List<Int>>,
    ): Boolean {
      var ok = true;

First, map each code point: ASCII letters to lowercase, and the rest by
the IDNA mapping table. Disallowed code points are errors. Each code
point's [properties](#lookups) are needed later, and mapping looks them
up anyway, so they're kept beside it.

      let mapped = new ListBuilder<Int>();
      let mappedProps = new ListBuilder<Int>();
      for (var i = String.begin; (ok || !forAscii) && domain.hasIndex(i); i = domain.next(i)) {
        let c = domain[i];
        if (c < 0x80) {
          let lower = if (c >= char'A' && c <= char'Z') { c + 32 } else { c };
          mapped.add(lower);
          mappedProps.add(asciiProperties[lower]);
        } else if (mapCodePoint(c, mapped, mappedProps) == disallowedKind) {
          ok = false;
        }
      }
      if (!ok && forAscii) {
        return false;
      }

Then normalize to NFC, which is rarely needed, as the properties tell,
and split into labels at dots.

      let normal = isNfcQuick(mappedProps);
      let normalized = if (normal) { mapped.toList() } else { toNfc(mapped) };
      let allProps = if (normal) { mappedProps.toList() } else { propertiesOf(normalized) };
      let labelProperties = new ListBuilder<List<Int>>();
      var labelStart = 0;
      for (var k = 0; k <= normalized.length; k += 1) {
        if (k == normalized.length || normalized[k] == char'.') {
          labels.add(normalized.slice(labelStart, k));
          labelProperties.add(allProps.slice(labelStart, k));
          labelStart = k + 1;
        }
      }

Then convert and check each label, with each code point's
[properties](#lookups) beside it. An `xn--` label must be ASCII, must
decode from Punycode, and must then be neither empty nor ASCII; it's
checked as any other label, and must be valid code points in NFC too.
Where one doesn't decode, it stays as it was.

      var bidiDomain = false;
      for (var k = 0; k < labels.length && (ok || !forAscii); k += 1) {
        var label = labels[k];
        var props = labelProperties[k];
        var valid = true;
        if (startsWithXnDashes(label)) {
          let rest: List<Int>? = if (isAsciiLabel(label)) {
            punycodeDecode(label, 4) orelse null
          } else {
            null
          };
          if (rest == null) {
            valid = false;
          } else {
            label = rest;
            labels[k] = rest;
            props = propertiesOf(rest);
            labelProperties[k] = props;
            valid = !rest.isEmpty && !isAsciiLabel(rest) && isNfcValid(rest, props);
          }
        }
        if (!valid || !isValidLabel(label, props)) {
          ok = false;
        }

The domain is a Bidi domain name if it has a right-to-left letter or an
Arabic digit anywhere.

        for (var j = 0; j < props.length && !bidiDomain; j += 1) {
          let bidi = props[j] & 0xF;
          bidiDomain = bidi == bidiR || bidi == bidiAL || bidi == bidiAN;
        }
      }

Last, the Bidi rule, for each label of a Bidi domain name.

      if (bidiDomain) {
        for (var k = 0; k < labels.length && (ok || !forAscii); k += 1) {
          if (!meetsBidiRule(labelProperties[k])) {
            ok = false;
          }
        }
      }
      ok
    }

## Validity Criteria

UTS #46's [validity
criteria](https://www.unicode.org/reports/tr46/#Validity_Criteria), but
the Bidi rule, which needs the whole domain, for `label`, with its code
points' properties. With CheckHyphens off, hyphens can go anywhere, but
a label can't start with `xn--`. It can't start with a mark, and must
meet the ContextJ rules. (That its code points are valid and in NFC is
checked above, for labels from Punycode; others are, but for disallowed
code points, which are errors already.)

    let isValidLabel(label: List<Int>, props: List<Int>): Boolean {
      !startsWithXnDashes(label) && (props.isEmpty || (props[0] & markBit) == 0) &&
        meetsContextJ(label, props)
    }

Whether a label from Punycode, with its properties, is all valid code
points (deviations included), in NFC. It can't hold a dot, since
Punycode's are all ASCII.

    let isNfcValid(label: List<Int>, props: List<Int>): Boolean {
      var valid = true;
      for (var k = 0; k < label.length && valid; k += 1) {
        valid = isValidCode(label[k]);
      }
      if (!valid || isNfcQuick(props)) {
        valid
      } else {
        let normal = toNfc(label);
        var same = normal.length == label.length;
        for (var k = 0; k < label.length && same; k += 1) {
          same = normal[k] == label[k];
        }
        same
      }
    }

The [ContextJ rules](https://www.rfc-editor.org/rfc/rfc5892#appendix-A.1)
for the zero-width joiners (CheckJoiners). Either may follow a virama
(canonical combining class 9). Otherwise a zero-width non-joiner must be
between a letter that joins on the left (joining type L or D) and one
that joins on the right (R or D), with only transparent ones (T)
between, and a zero-width joiner is an error.

    let meetsContextJ(label: List<Int>, props: List<Int>): Boolean {
      var ok = true;
      for (var k = 0; k < label.length && ok; k += 1) {
        let c = label[k];
        if ((c == 0x200C || c == 0x200D) && !(k > 0 && ((props[k - 1] >> 8) & 0xFF) == 9)) {
          if (c == 0x200D) {
            ok = false;
          } else {
            var before = k - 1;
            while (before >= 0 && joiningType(props[before]) == joiningT) {
              before -= 1;
            }
            var after = k + 1;
            while (after < label.length && joiningType(props[after]) == joiningT) {
              after += 1;
            }
            ok = before >= 0 && after < label.length;
            if (ok) {
              let left = joiningType(props[before]);
              let right = joiningType(props[after]);
              ok = (left == joiningL || left == joiningD) && (right == joiningR || right == joiningD);
            }
          }
        }
      }
      ok
    }

The [Bidi rule](https://www.rfc-editor.org/rfc/rfc5893#section-2)
(RFC 5893), for each label of a Bidi domain name, empty ones aside,
given its code points' properties. A label starting with a
right-to-left letter (bidi class R or AL) may hold only right-to-left
letters, numbers, neutrals, and marks, must end with a right-to-left
letter or a number (ignoring marks after it), and can't mix European
and Arabic digits. Any other label must start with a left-to-right
letter (L), may hold no right-to-left letters or Arabic digits, and must
end with a left-to-right letter or European digit.

    let meetsBidiRule(props: List<Int>): Boolean {
      props.isEmpty || meetsBidiRuleNotEmpty(props)
    }

    let meetsBidiRuleNotEmpty(props: List<Int>): Boolean {
      let first = props[0] & 0xF;
      var last = props.length - 1;
      while (last > 0 && (props[last] & 0xF) == bidiNSM) {
        last -= 1;
      }
      let ending = props[last] & 0xF;
      var ok = true;
      if (first == bidiR || first == bidiAL) {
        var european = false;
        var arabic = false;
        for (var k = 0; k < props.length && ok; k += 1) {
          let bidi = props[k] & 0xF;
          ok = bidi != bidiL && bidi != bidiOther;
          european = european || bidi == bidiEN;
          arabic = arabic || bidi == bidiAN;
        }
        ok && !(european && arabic) &&
          (ending == bidiR || ending == bidiAL || ending == bidiEN || ending == bidiAN)
      } else if (first == bidiL) {
        for (var k = 0; k < props.length && ok; k += 1) {
          let bidi = props[k] & 0xF;
          ok = bidi != bidiR && bidi != bidiAL && bidi != bidiAN && bidi != bidiOther;
        }
        ok && (ending == bidiL || ending == bidiEN)
      } else {
        false
      }
    }

## NFC

[Normalization Form C](https://www.unicode.org/reports/tr15/): decompose
each code point canonically, put each run of combining marks in order
of combining class, then compose each mark with the starter before it,
where nothing between blocks it.

Most domains are NFC already, and NFC's [quick
check](https://www.unicode.org/reports/tr15/#Detecting_Normalization_Forms)
sees that from code points' properties: a string is, if its marks are in
order of combining class and none may compose with the code point
before. For valid code points, the check never says a string isn't NFC
without needing a closer look, so this says only whether it surely is.
Disallowed ones have no combining class, decomposition, or composition.

    let isNfcQuick(props: Listed<Int>): Boolean {
      var quick = true;
      var lastClass = 0;
      for (var k = 0; k < props.length && quick; k += 1) {
        let p = props[k];
        let cc = (p >> 8) & 0xFF;
        quick = (p & composesBit) == 0 && (cc == 0 || lastClass <= cc);
        lastClass = cc;
      }
      quick
    }

    let toNfc(input: Listed<Int>): List<Int> {
      let out = new ListBuilder<Int>();
      let props = new ListBuilder<Int>();
      for (var k = 0; k < input.length; k += 1) {
        decomposeOnto(out, props, input[k]);
      }
      for (var k = 1; k < out.length; k += 1) {
        let c = out[k];
        let p = props[k];
        let cc = (p >> 8) & 0xFF;
        if (cc != 0) {
          var j = k;
          while (j > 0 && ((props[j - 1] >> 8) & 0xFF) > cc) {
            out[j] = out[j - 1];
            props[j] = props[j - 1];
            j -= 1;
          }
          out[j] = c;
          props[j] = p;
        }
      }

A mark is blocked from the starter if a code point between them has a
combining class of 0 or at least its own. Since marks are in order, only
the last one before it, not composed, matters.

      let result = new ListBuilder<Int>();
      var starter = -1;
      var lastClass = 0;
      for (var k = 0; k < out.length; k += 1) {
        let c = out[k];
        let cc = (props[k] >> 8) & 0xFF;
        var composed = -1;
        if (
          starter >= 0 && (props[k] & composesBit) != 0 &&
          (result.length - 1 == starter || (lastClass != 0 && lastClass < cc))
        ) {
          composed = composePair(result[starter], c);
        }
        if (composed >= 0) {
          result[starter] = composed;
        } else {
          if (cc == 0) {
            starter = result.length;
          }
          lastClass = cc;
          result.add(c);
        }
      }
      result.toList()
    }

Hangul syllables are made of two or three jamo, by formula.

    let hangulBase = 0xAC00;
    let hangulCount = 11172;
    let jamoLBase = 0x1100;
    let jamoVBase = 0x1161;
    let jamoTBase = 0x11A7;
    let jamoVCount = 21;
    let jamoTCount = 28;

Decomposes `c` fully onto `out`, and each code point's properties onto
`props`.

    let decomposeOnto(out: ListBuilder<Int>, props: ListBuilder<Int>, c: Int): Void {
      let p = properties(c);
      let s = c - hangulBase;
      if ((p & decomposesBit) == 0) {
        out.add(c);
        props.add(p);
      } else if (s >= 0 && s < hangulCount) {
        decomposeOnto(out, props, jamoLBase + s / (jamoVCount * jamoTCount));
        decomposeOnto(out, props, jamoVBase + (s % (jamoVCount * jamoTCount)) / jamoTCount);
        if (s % jamoTCount != 0) {
          decomposeOnto(out, props, jamoTBase + s % jamoTCount);
        }
      } else {
        let parts = decompositionOf(c);
        decomposeOnto(out, props, parts[0]);
        decomposeOnto(out, props, parts[1]);
      }
    }

The code point that `first` and `second` compose to, or -1.

    let composePair(first: Int, second: Int): Int {
      let l = first - jamoLBase;
      let v = second - jamoVBase;
      let s = first - hangulBase;
      let t = second - jamoTBase;
      if (l >= 0 && l < 19 && v >= 0 && v < jamoVCount) {
        hangulBase + (l * jamoVCount + v) * jamoTCount
      } else if (s >= 0 && s < hangulCount && s % jamoTCount == 0 && t > 0 && t < jamoTCount) {
        first + t
      } else if (idnaEntry(second) >= 0) {
        -1
      } else {
        compositionOf(first, second)
      }
    }

## Lookups

In the [generated tables](idna-tables.temper.md), read where they are:
a lookup finds its code point's number, or string, of its block or
sub-block, and reads the string up to the run holding the code point,
and maybe on to the data after the runs. Nothing is decoded ahead or
kept, so loading the library costs only the tables' constants, a domain
reads only the blocks its code points are in, and the first domain
beyond ASCII costs no more than any other.

It's also safe from many threads at once, in every language, since the
library has no module-level `var`, only `let`s, which are set once as it
loads and only read after. That matters most in C++, where Temper makes
a module-level `var` a plain `static std::shared_ptr`, so two threads
setting one lazily, as these tables once were, race (undefined
behavior). Its `let`s are set in `hrefine::global_init_init()`, which a
program must call before using the library, so before any threads do,
and then only read, and many threads may read, and so copy, the same
`shared_ptr` at once. (Rust, Java, and C# make module-level state safe
on their own, if not as cheaply: Rust locks it.) Keep it that way: any
cache here would need a lock that Temper can't yet write portably.

The rarer lookups, of mappings in the pool, decompositions, and
compositions, read past the runs, so they decode the whole sub-block
string of code point `c` first. Its digits from U+0060 to U+007F go on,
and the last is from U+0040 to U+005F, each digit its low five bits.

    let subBlockNumbers(c: Int): List<Int> {
      let split = -1 - idnaBlocks[c >> idnaBlockShift];
      let text = idnaTexts[split][-1 - idnaSubBlocks[split][(c & blockMask) >> idnaSubBlockShift]];
      let numbers = new ListBuilder<Int>();
      var value = 0;
      for (var i = String.begin; text.hasIndex(i); i = text.next(i)) {
        let d = text[i];
        value = (value << 5) | (d & 0x1F);
        if (d < 0x60) {
          numbers.add(value);
          value = 0;
        }
      }
      numbers.toList()
    }

Where the run holding `offset` starts, among the runs at the start of
`numbers`.

    let runStartIn(numbers: List<Int>, offset: Int): Int {
      var start = 0;
      var k = 0;
      while (numbers[k] != 0 && offset >= start + numbers[k]) {
        start += numbers[k];
        k += 3;
      }
      start
    }

The index just past the runs, where the data after them starts, if
there is any. The last run's length is 0.

    let afterRuns(numbers: List<Int>): Int {
      var k = 0;
      while (numbers[k] != 0) {
        k += 3;
      }
      k + 3
    }

Adds the code points that `c` maps to, by `mapping`, of kind 6, from its
sub-block's pool onto `out`, with their properties onto `props`.

    let mapFromPool(c: Int, mapping: Int, out: ListBuilder<Int>, props: ListBuilder<Int>): Void {
      let numbers = subBlockNumbers(c);
      let offset = c & subBlockMask;
      let detail = mapping >> 3;
      let length = detail & 31;
      let start = (detail >> 5) + (offset - runStartIn(numbers, offset)) * length;
      let pool = afterRuns(numbers) + 2;
      var target = c - offset;
      for (var k = 0; k < start + length; k += 1) {
        target += unzigzag(numbers[pool + k]);
        if (k >= start) {
          out.add(target);
          props.add(properties(target));
        }
      }
    }

The canonical decomposition of `c`, which must have one, as its first
and second parts.

    let decompositionOf(c: Int): List<Int> {
      let numbers = subBlockNumbers(c);
      let offset = c & subBlockMask;
      let at = afterRuns(numbers);
      var k = at + 2 + numbers[at];
      var position = numbers[k];
      while (position != offset) {
        k += 3;
        position += numbers[k];
      }
      [c - unzigzag(numbers[k + 1]), numbers[k + 2]]
    }

The code point that `first` and `second` compose to, or -1, for
`second` in a sub-block with data after its runs.

    let compositionOf(first: Int, second: Int): Int {
      let numbers = subBlockNumbers(second);
      let offset = second & subBlockMask;
      let at = afterRuns(numbers);
      var k = if (at < numbers.length) { at + 2 + numbers[at] + numbers[at + 1] * 3 } else { at };
      var secondAt = 0;
      var firstAt = 0;
      var found = -1;
      while (found < 0 && k < numbers.length && secondAt <= offset) {
        if (numbers[k] != 0) {
          secondAt += numbers[k];
          firstAt = 0;
        }
        firstAt += numbers[k + 1];
        if (secondAt == offset && firstAt == first) {
          found = first + unzigzag(numbers[k + 2]);
        }
        k += 3;
      }
      found
    }

`c`'s number for its block or sub-block, as `idnaBlocks` and
`idnaSubBlocks` give it.

    let idnaEntry(c: Int): Int {
      let block = idnaBlocks[c >> idnaBlockShift];
      if (block >= 0) {
        block
      } else {
        idnaSubBlocks[-1 - block][(c & blockMask) >> idnaSubBlockShift]
      }
    }

    let blockMask = (1 << idnaBlockShift) - 1;
    let subBlockMask = (1 << idnaSubBlockShift) - 1;

Most lookups need only a run's mapping and property index, so this finds
them without decoding, returning `mapping * 128 + propertyIndex` for code
point `c`, beyond ASCII. Most are in the directory; for the rest, it
reads the three numbers of each run, digit by digit, till the run that
holds `c`.

    let runOf(c: Int): Int {
      let entry = idnaEntry(c);
      if (entry >= 0) {
        entry
      } else {
        readRun(idnaTexts[-1 - idnaBlocks[c >> idnaBlockShift]][-1 - entry], c & subBlockMask)
      }
    }

    let readRun(text: String, offset: Int): Int {
      var i = String.begin;
      var start = 0;
      var field = 0;
      var value = 0;
      var length = 0;
      var mapping = 0;
      var result = -1;
      while (result < 0) {
        let d = text[i];
        i = text.next(i);
        value = if (value == 0) { d & 0x1F } else { (value << 5) | (d & 0x1F) };
        if (d < 0x60) {
          if (field == 0) {
            length = value;
            field = 1;
          } else if (field == 1) {
            mapping = value;
            field = 2;
          } else if (length == 0 || offset < start + length) {
            result = (mapping << 7) | value;
          } else {
            start += length;
            field = 0;
          }
          value = 0;
        }
      }
      result
    }

Signed numbers are zigzagged, so 0, -1, 1, -2, and 2 are written as 0,
1, 2, 3, and 4.

    let unzigzag(n: Int): Int {
      if ((n & 1) == 0) { n >> 1 } else { -(n >> 1) - 1 }
    }

IDNA mapping kinds, as the tables store them.

    let validKind = 0;
    let disallowedKind = 1;
    let ignoredKind = 2;
    let deltaKind = 3;
    let evenKind = 4;
    let oddKind = 5;
    let poolKind = 6;

Maps code point `c`, beyond ASCII, onto `out`, as the IDNA mapping says,
with each code point's properties onto `props`, and returns its kind:
valid and disallowed code points stay as they are, ignored ones go, and
alternating ones that aren't mapped are valid.

    let mapCodePoint(c: Int, out: ListBuilder<Int>, props: ListBuilder<Int>): Int {
      let run = runOf(c);
      let mapping = run >> 7;
      let kind = mapping & 7;
      let alternating = kind == evenKind || kind == oddKind;
      if (kind == deltaKind || (alternating && (c & 1) == kind - evenKind)) {
        let target = c + unzigzag(mapping >> 3);
        out.add(target);
        props.add(properties(target));
        deltaKind
      } else if (kind == poolKind) {
        mapFromPool(c, mapping, out, props);
        kind
      } else if (kind == ignoredKind) {
        kind
      } else {
        out.add(c);
        props.add(propertyValues[run & 127]);
        if (kind == disallowedKind) { kind } else { validKind }
      }
    }

Whether `c` is valid (deviations included), and not to be mapped. All
of ASCII is but uppercase letters.

    let isValidCode(c: Int): Boolean {
      if (c < 0x80) {
        c < char'A' || c > char'Z'
      } else {
        let kind = (runOf(c) >> 7) & 7;
        kind == validKind || ((kind == evenKind || kind == oddKind) && (c & 1) != kind - evenKind)
      }
    }

Properties, packed as the tables say: the bidi class in bits 0 to 3,
the joining type in 4 to 6, whether it's a mark in 7, the combining
class in 8 to 15, whether it decomposes in 16, and whether it may
compose with a code point before it in 17.

    let properties(c: Int): Int {
      if (c < 0x80) {
        asciiProperties[c]
      } else {
        propertyValues[runOf(c) & 127]
      }
    }

    let propertiesOf(label: List<Int>): List<Int> {
      let props = new ListBuilder<Int>();
      for (var k = 0; k < label.length; k += 1) {
        props.add(properties(label[k]));
      }
      props.toList()
    }

    let markBit = 0x80;
    let decomposesBit = 0x1_0000;
    let composesBit = 0x2_0000;

    let bidiL = 0;
    let bidiR = 1;
    let bidiAL = 2;
    let bidiAN = 3;
    let bidiEN = 4;
    let bidiNSM = 10;
    let bidiOther = 11;

    let joiningL = 1;
    let joiningR = 2;
    let joiningD = 3;
    let joiningT = 4;

    let joiningType(props: Int): Int { (props >> 4) & 7 }

## Helpers

    let isAsciiString(s: String): Boolean {
      var ascii = true;
      for (var i = String.begin; ascii && s.hasIndex(i); i = s.next(i)) {
        ascii = s[i] < 0x80;
      }
      ascii
    }

ASCII letters lowercased, and the rest as they are, without a copy if
there's nothing to change.

    let asciiLowercase(s: String): String {
      var i = String.begin;
      while (s.hasIndex(i) && (s[i] < char'A' || s[i] > char'Z')) {
        i = s.next(i);
      }
      if (!s.hasIndex(i)) {
        s
      } else {
        let out = new StringBuilder();
        out.append(s.slice(String.begin, i));
        while (s.hasIndex(i)) {
          let c = s[i];
          appendCode(out, if (c >= char'A' && c <= char'Z') { c + 32 } else { c });
          i = s.next(i);
        }
        out.toString()
      }
    }

    let isAsciiLabel(label: List<Int>): Boolean {
      var ascii = true;
      for (var k = 0; ascii && k < label.length; k += 1) {
        ascii = label[k] < 0x80;
      }
      ascii
    }

Whether any of a domain's labels starts with `xn--`, in any case.

    let hasXnLabel(domain: String): Boolean {
      var matched = 0; // How much of `xn--` the label starts with, or -1.
      for (var i = String.begin; matched < 4 && domain.hasIndex(i); i = domain.next(i)) {
        let c = domain[i];
        if (c == char'.') {
          matched = 0;
        } else if (matched >= 0) {
          let lower = if (c >= char'A' && c <= char'Z') { c + 32 } else { c };
          let want = if (matched == 0) { char'x' } else if (matched == 1) { char'n' } else { char'-' };
          matched = if (lower == want) { matched + 1 } else { -1 };
        }
      }
      matched == 4
    }

Whether a label starts with `xn--`. Mapping has lowercased it already.

    let startsWithXnDashes(label: List<Int>): Boolean {
      label.length >= 4 && label[0] == char'x' && label[1] == char'n' &&
        label[2] == char'-' && label[3] == char'-'
    }

## Tests

    test("domain to ASCII") {
      let ascii(domain: String): String { domainToAscii(domain) orelse "(fails)" }
      assert(ascii("EXAMPLE.com") == "example.com");
      assert(ascii("Bücher.example") == "xn--bcher-kva.example");
      assert(ascii("faß.de") == "xn--fa-hia.de");
      assert(ascii("XN--a.example") == "xn--a.example");
      assert(ascii("xn--a.ß") == "(fails)");
      assert(ascii("\u{3002}") == ".");
      assert(ascii("") == "(fails)");
      assert(ascii("\u{AD}") == "(fails)");
    }

    test("domain to Unicode") {
      assert(domainToUnicode("xn--bcher-kva.example") == "bücher.example");
      assert(domainToUnicode("XN--FA-HIA.DE") == "faß.de");
      assert(domainToUnicode("EXAMPLE.com") == "example.com");
      assert(domainToUnicode("a.Xn--Bcher-kva.example") == "a.bücher.example");
      assert(domainToUnicode("xn-.Axn--b") == "xn-.axn--b");
      assert(domainToUnicode("xn--a!.example") == "xn--a!.example");
      assert(domainToUnicode("a\u{FFFD}b") == "a\u{FFFD}b");
      assert(domainToUnicode("A\u{30A}") == "\u{E5}");
    }

    test("NFC") {
      let nfc(s: String): String {
        let codes = new ListBuilder<Int>();
        for (var i = String.begin; s.hasIndex(i); i = s.next(i)) {
          codes.add(s[i]);
        }
        String.fromCodePoints(toNfc(codes)) orelse panic()
      }
      assert(nfc("e\u{301}") == "\u{E9}");
      assert(nfc("a\u{323}\u{302}") == "\u{1EAD}");
      assert(nfc("a\u{302}\u{323}") == "\u{1EAD}");
      assert(nfc("\u{1100}\u{1161}\u{11A8}") == "\u{AC01}");
      assert(nfc("\u{AC01}") == "\u{AC01}");
      assert(nfc("\u{1E0B}\u{323}") == "\u{1E0D}\u{307}");
      assert(nfc("\u{113C2}\u{113C5}") == "\u{113C5}\u{113C2}");
    }
