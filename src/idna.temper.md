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
      if (isAsciiString(domain)) {
        let out = new StringBuilder();
        for (var i = String.begin; domain.hasIndex(i); i = domain.next(i)) {
          let c = domain[i];
          appendCode(out, if (c >= char'A' && c <= char'Z') { c + 32 } else { c });
        }
        let result = out.toString();
        if (result.isEmpty) {
          bubble();
        }
        return result;
      }
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
        let out = new StringBuilder();
        for (var i = String.begin; domain.hasIndex(i); i = domain.next(i)) {
          let c = domain[i];
          appendCode(out, if (c >= char'A' && c <= char'Z') { c + 32 } else { c });
        }
        return out.toString();
      }
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
first error, since any fails the whole domain. It's the only way in to
the [tables](#lookups), so it gets them, decoding them the first time.

    let processDomain(
      domain: String, forAscii: Boolean, labels: ListBuilder<List<Int>>,
    ): Boolean {
      let tables = idnaTables();
      var ok = true;

First, map each code point: ASCII letters to lowercase, and the rest by
the IDNA mapping table. Disallowed code points are errors.

      let mapped = new ListBuilder<Int>();
      for (var i = String.begin; domain.hasIndex(i); i = domain.next(i)) {
        let c = domain[i];
        if (c < 0x80) {
          mapped.add(if (c >= char'A' && c <= char'Z') { c + 32 } else { c });
        } else if (mapCodePoint(tables, c, mapped) == disallowedKind) {
          if (forAscii) {
            return false;
          }
          ok = false;
        }
      }

Then normalize to NFC, and split into labels at dots. Each code point's
[properties](#lookups) are needed later, and they tell whether
normalizing would change anything, which is rare, so they're looked up
here, and again only if it would.

      let mappedProps = new ListBuilder<Int>();
      var normal = true;
      for (var k = 0; k < mapped.length; k += 1) {
        let c = mapped[k];
        let p = properties(tables, c);
        mappedProps.add(p);
        normal = normal && (c < 0x300 || (p & nfcBits) == 0);
      }
      let normalized = if (normal) { mapped.toList() } else { toNfc(tables, mapped) };
      let allProps = if (normal) { mappedProps.toList() } else { propertiesOf(tables, normalized) };
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
      for (var k = 0; k < labels.length; k += 1) {
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
            props = propertiesOf(tables, rest);
            labelProperties[k] = props;
            valid = !rest.isEmpty && !isAsciiLabel(rest) && isNfcValid(tables, rest);
          }
        }
        if (!valid || !isValidLabel(label, props)) {
          if (forAscii) {
            return false;
          }
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
        for (var k = 0; k < labels.length; k += 1) {
          if (!meetsBidiRule(labelProperties[k])) {
            if (forAscii) {
              return false;
            }
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

Whether a label from Punycode is all valid code points (deviations
included), in NFC. It can't hold a dot, since Punycode's are all ASCII.

    let isNfcValid(tables: IdnaTables, label: List<Int>): Boolean {
      var valid = true;
      for (var k = 0; k < label.length && valid; k += 1) {
        valid = isValidCode(tables, label[k]);
      }
      if (!valid || isNfcAlready(tables, label)) {
        return valid;
      }
      let normal = toNfc(tables, label);
      var same = normal.length == label.length;
      for (var k = 0; k < label.length && same; k += 1) {
        same = normal[k] == label[k];
      }
      same
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
      if (props.isEmpty) {
        return true;
      }
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

Most domains are NFC already, and that's quick to see: a string is, if
no code point decomposes, composes with the one before, or has a
combining class (which might need reordering). Code points below U+0300
are left out, since any that decompose (as `é` does) compose back, with
nothing after them that could join them.

    let isNfcAlready(tables: IdnaTables, codes: Listed<Int>): Boolean {
      var already = true;
      for (var k = 0; k < codes.length && already; k += 1) {
        let c = codes[k];
        already = c < 0x300 || (properties(tables, c) & nfcBits) == 0;
      }
      already
    }

    let toNfc(tables: IdnaTables, input: Listed<Int>): List<Int> {
      let out = new ListBuilder<Int>();
      let props = new ListBuilder<Int>();
      for (var k = 0; k < input.length; k += 1) {
        decomposeOnto(tables, out, props, input[k]);
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
          composed = composePair(tables, result[starter], c);
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

    let decomposeOnto(
      tables: IdnaTables, out: ListBuilder<Int>, props: ListBuilder<Int>, c: Int,
    ): Void {
      let p = if (c < 0xC0) { 0 } else { properties(tables, c) };
      if ((p & decomposesBit) == 0) {
        out.add(c);
        props.add(p);
        return;
      }
      let s = c - hangulBase;
      if (s >= 0 && s < hangulCount) {
        decomposeOnto(tables, out, props, jamoLBase + s / (jamoVCount * jamoTCount));
        decomposeOnto(
          tables, out, props, jamoVBase + (s % (jamoVCount * jamoTCount)) / jamoTCount,
        );
        if (s % jamoTCount != 0) {
          decomposeOnto(tables, out, props, jamoTBase + s % jamoTCount);
        }
      } else {
        let decompositions = tables.decompositions;
        let at = findDecomposition(decompositions, c);
        decomposeOnto(tables, out, props, decompositions[at + 1]);
        decomposeOnto(tables, out, props, decompositions[at + 2]);
      }
    }

The code point that `first` and `second` compose to, or -1.

    let composePair(tables: IdnaTables, first: Int, second: Int): Int {
      let l = first - jamoLBase;
      let v = second - jamoVBase;
      if (l >= 0 && l < 19 && v >= 0 && v < jamoVCount) {
        return hangulBase + (l * jamoVCount + v) * jamoTCount;
      }
      let s = first - hangulBase;
      let t = second - jamoTBase;
      if (s >= 0 && s < hangulCount && s % jamoTCount == 0 && t > 0 && t < jamoTCount) {
        return first + t;
      }
      let decompositions = tables.decompositions;
      let compositionOrder = tables.compositionOrder;
      var low = 0;
      var high = compositionOrder.length;
      var found = -1;
      while (low < high && found < 0) {
        let middle = (low + high) / 2;
        let at = compositionOrder[middle] * 3;
        let a = decompositions[at + 1];
        let b = decompositions[at + 2];
        if (a < first || (a == first && b < second)) {
          low = middle + 1;
        } else if (a == first && b == second) {
          found = decompositions[at];
        } else {
          high = middle;
        }
      }
      found
    }

## Lookups

In the [generated tables](idna-tables.temper.md), decoded the first time
a domain needs them, so loading the library, and domains in ASCII, cost
nothing for them. Two threads getting there at once may each decode
them, and either result serves; in C++, though, Temper doesn't guard
module-level variables, so that's a race.

    class IdnaTables(
      public idnaRanges: List<Int>,
      public idnaIndex: List<Int>,
      public idnaPool: List<Int>,
      public decompositions: List<Int>,
      public compositionOrder: List<Int>,
      public propertyValues: List<Int>,
      public propertyRuns: List<Int>,
      public propertyIndex: List<Int>,
      public asciiProperties: List<Int>,
    ) {}

    var idnaTablesCache: IdnaTables? = null;

    let idnaTables(): IdnaTables {
      let cached = idnaTablesCache;
      if (cached != null) { cached } else { decodeIdnaTables() }
    }

`decodeIdnaTables` ends here, with the decoded tables, adding what's
made from them (the indices below, the composition order, and ASCII's
properties), and keeping them. Keeping them here, not in `idnaTables`,
also stops Temper from trying to decode them while compiling, as it
does for calls it thinks it can work out ahead, which crashes the
build (as of 2026-10-29).

    let keepIdnaTables(
      idnaRanges: List<Int>, idnaPool: List<Int>, decompositions: List<Int>,
      propertyValues: List<Int>, propertyRuns: List<Int>,
    ): IdnaTables {
      let propertyIndex = runIndex(propertyRuns);
      let asciiProperties = new ListBuilder<Int>();
      for (var c = 0; c < 0x80; c += 1) {
        asciiProperties.add(
          propertyValues[propertyRuns[findRun(propertyRuns, propertyIndex, c) + 1]],
        );
      }
      let tables = new IdnaTables(
        idnaRanges, runIndex(idnaRanges), idnaPool, decompositions,
        sortCompositions(decompositions), propertyValues, propertyRuns, propertyIndex,
        asciiProperties.toList(),
      );
      idnaTablesCache = tables;
      tables
    }

The decompositions' row indices (divided by three), sorted by first part
and then second part, for composing.

    let sortCompositions(decompositions: List<Int>): List<Int> {
      let order = new ListBuilder<Int>();
      for (var k = 0; k < decompositions.length; k += 3) {
        order.add(k / 3);
      }
      order.sort(fn (a: Int, b: Int): Int {
        let byFirst = decompositions[a * 3 + 1] - decompositions[b * 3 + 1];
        if (byFirst != 0) { byFirst } else {
          decompositions[a * 3 + 2] - decompositions[b * 3 + 2]
        }
      });
      order.toList()
    }

Both the IDNA mapping and the properties are runs of two numbers, sorted
by the first, the code point where each starts. To find the run holding
a code point quickly, an index gives, for each block of 1024 code
points, the run holding the block's first; the search is then between
that run and the next block's, often only one or two.

    let blockShift = 10;

    let runIndex(table: List<Int>): List<Int> {
      let index = new ListBuilder<Int>();
      let runs = table.length / 2;
      var run = 0;
      for (var block = 0; block <= 0x10FFFF >> blockShift; block += 1) {
        let c = block << blockShift;
        while (run + 1 < runs && table[(run + 1) * 2] <= c) {
          run += 1;
        }
        index.add(run);
      }
      index.toList()
    }

The index in `table` of the run holding `c`, given its block index.

    let findRun(table: List<Int>, index: List<Int>, c: Int): Int {
      let block = c >> blockShift;
      var low = index[block];
      var high = if (block + 1 < index.length) { index[block + 1] + 1 } else { table.length / 2 };
      while (high - low > 1) {
        let middle = (low + high) / 2;
        if (table[middle * 2] <= c) {
          low = middle;
        } else {
          high = middle;
        }
      }
      low * 2
    }

The index of `c`'s row in `decompositions`, which must have it.

    let findDecomposition(decompositions: List<Int>, c: Int): Int {
      var low = 0;
      var high = decompositions.length / 3;
      while (high - low > 1) {
        let middle = (low + high) / 2;
        if (decompositions[middle * 3] <= c) {
          low = middle;
        } else {
          high = middle;
        }
      }
      low * 3
    }

IDNA mapping kinds, as `idnaRanges` stores them.

    let validKind = 0;
    let disallowedKind = 1;
    let ignoredKind = 2;
    let deltaKind = 3;
    let alternatingKind = 4;
    let poolKind = 5;

Maps code point `c` onto `out`, as the IDNA mapping says, and returns
its kind. Valid and disallowed code points stay as they are, and
ignored ones go.

    let mapCodePoint(tables: IdnaTables, c: Int, out: ListBuilder<Int>): Int {
      let idnaRanges = tables.idnaRanges;
      let at = findRun(idnaRanges, tables.idnaIndex, c);
      let value = idnaRanges[at + 1];
      let kind = value & 7;
      let detail = unzigzag(value >> 3);
      if (kind == deltaKind) {
        out.add(c + detail);
      } else if (kind == alternatingKind) {
        if (((c - idnaRanges[at]) & 1) == 0) {
          out.add(c + detail);
        } else {
          out.add(c);
          return validKind;
        }
      } else if (kind == poolKind) {
        let length = detail & 31;
        let first = (detail >> 5) + (c - idnaRanges[at]) * length;
        let idnaPool = tables.idnaPool;
        for (var k = first; k < first + length; k += 1) {
          out.add(idnaPool[k]);
        }
      } else if (kind != ignoredKind) {
        out.add(c);
      }
      kind
    }

Whether `c` is valid (deviations included), and not to be mapped.

    let isValidCode(tables: IdnaTables, c: Int): Boolean {
      let idnaRanges = tables.idnaRanges;
      let at = findRun(idnaRanges, tables.idnaIndex, c);
      let kind = idnaRanges[at + 1] & 7;
      kind == validKind || (kind == alternatingKind && ((c - idnaRanges[at]) & 1) == 1)
    }

Properties, packed as the tables say: the bidi class in bits 0 to 3,
the joining type in 4 to 6, whether it's a mark in 7, the combining
class in 8 to 15, whether it decomposes in 16, and whether it composes
with a code point before it in 17.

ASCII's are looked up once, since labels are often mostly ASCII.

    let properties(tables: IdnaTables, c: Int): Int {
      if (c < 0x80) {
        tables.asciiProperties[c]
      } else {
        let runs = tables.propertyRuns;
        tables.propertyValues[runs[findRun(runs, tables.propertyIndex, c) + 1]]
      }
    }

    let propertiesOf(tables: IdnaTables, label: List<Int>): List<Int> {
      let props = new ListBuilder<Int>();
      for (var k = 0; k < label.length; k += 1) {
        props.add(properties(tables, label[k]));
      }
      props.toList()
    }

    let markBit = 0x80;
    let decomposesBit = 0x1_0000;
    let composesBit = 0x2_0000;
    let nfcBits = 0x3_FF00;

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
      for (var i = String.begin; s.hasIndex(i); i = s.next(i)) {
        if (s[i] >= 0x80) {
          return false;
        }
      }
      true
    }

    let isAsciiLabel(label: List<Int>): Boolean {
      for (var k = 0; k < label.length; k += 1) {
        if (label[k] >= 0x80) {
          return false;
        }
      }
      true
    }

Whether any of a domain's labels starts with `xn--`, in any case.

    let hasXnLabel(domain: String): Boolean {
      var matched = 0; // How much of `xn--` the label starts with, or -1.
      for (var i = String.begin; domain.hasIndex(i); i = domain.next(i)) {
        let c = domain[i];
        if (c == char'.') {
          matched = 0;
        } else if (matched >= 0) {
          let lower = if (c >= char'A' && c <= char'Z') { c + 32 } else { c };
          let want = if (matched == 0) { char'x' } else if (matched == 1) { char'n' } else { char'-' };
          matched = if (lower == want) { matched + 1 } else { -1 };
          if (matched == 4) {
            return true;
          }
        }
      }
      false
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
        String.fromCodePoints(toNfc(idnaTables(), codes)) orelse panic()
      }
      assert(nfc("e\u{301}") == "\u{E9}");
      assert(nfc("a\u{323}\u{302}") == "\u{1EAD}");
      assert(nfc("a\u{302}\u{323}") == "\u{1EAD}");
      assert(nfc("\u{1100}\u{1161}\u{11A8}") == "\u{AC01}");
      assert(nfc("\u{AC01}") == "\u{AC01}");
      assert(nfc("\u{1E0B}\u{323}") == "\u{1E0D}\u{307}");
    }
