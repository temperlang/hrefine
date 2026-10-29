# /// script
# requires-python = ">=3.11"
# ///
"""Writes src/idna-tables.temper.md, the Unicode data that international
domain names (UTS #46, as the URL Standard runs it) need, from the Unicode
files that scripts/unicode_data.py gets and pins.

    uv run scripts/idna_tables.py

The tables are:

- The IDNA mapping: each code point's status (valid, ignored, mapped, or
  disallowed) and, if mapped, what it maps to. With nontransitional
  processing, deviations (`ß`, `ς`, and the zero-width joiners) are valid.
- Canonical decompositions, for NFC, which composes with them too.
- Character properties: canonical combining class, bidi class (for the
  Bidi rule), joining type (for the ContextJ rules), and whether it's a
  mark (labels can't start with one).

Mapping gives only valid code points, and domain to ASCII fails at once on
a disallowed one, so the rest of the tables need to be right only for
valid code points, which lets them leave out much. Domain to Unicode keeps
disallowed code points, so they need the right combining class (always 0)
and no decomposition (they have none), for NFC.

Each table is a list of numbers, written as text a few characters per
number, which the Temper code decodes when the library loads. The text
is printable ASCII but `"`, `$`, `\\`, and space (DIGITS): each number is
in base 45, most significant digit first, with the digits `DIGITS[45:90]`
for all but the last, which comes from `DIGITS[0:45]`. Sorted columns are
stored as differences, and signed numbers zigzagged (0, -1, 1, -2, 2 as 0,
1, 2, 3, 4). The script checks every code point's lookup, through the
same searches the Temper code does, against the Unicode files.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unicode_data  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "idna-tables.temper.md"
N = 0x110000

DIGITS = "".join(chr(c) for c in range(0x21, 0x7F) if chr(c) not in '"$\\')
BASE = 45
assert len(DIGITS) >= 2 * BASE

# Status kinds, as `idnaRanges` stores them, in the low three bits.
VALID, DISALLOWED, IGNORED, DELTA, ALTERNATING, POOL = range(6)

# Bidi classes as the Bidi rule (RFC 5893) needs them; others are OTHER.
BIDI = ["L", "R", "AL", "AN", "EN", "ES", "CS", "ET", "ON", "BN", "NSM", "OTHER"]
# Joining types for ContextJ (RFC 5892, appendix A); others are U.
JOINING = ["U", "L", "R", "D", "T"]


def fields(path: Path):
    """Each data line's code point range and its other fields."""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(";")]
        first, _, last = parts[0].partition("..")
        yield int(first, 16), int(last or first, 16), parts[1:]


def is_hangul_syllable(c: int) -> bool:
    return 0xAC00 <= c <= 0xD7A3


class Data:
    """The Unicode files' data, for every code point."""

    def __init__(self, folder: Path):
        self.status = [DISALLOWED] * N
        self.mapping: dict[int, list[int]] = {}
        for first, last, f in fields(folder / "IdnaMappingTable.txt"):
            kind = {"valid": VALID, "deviation": VALID, "disallowed": DISALLOWED,
                    "ignored": IGNORED, "mapped": POOL}[f[0]]
            for c in range(first, last + 1):
                self.status[c] = kind
                if kind == POOL:
                    self.mapping[c] = [int(x, 16) for x in f[1].split()]
        self.ccc = [0] * N
        self.category = ["Cn"] * N
        self.decomposition: dict[int, list[int]] = {}
        range_start = 0
        for line in (folder / "UnicodeData.txt").read_text(encoding="utf-8").splitlines():
            f = line.split(";")
            c = int(f[0], 16)
            if f[1].endswith(", First>"):
                range_start = c
                continue
            for d in range(range_start if f[1].endswith(", Last>") else c, c + 1):
                self.category[d] = f[2]
                self.ccc[d] = int(f[3])
            if f[5] and not f[5].startswith("<"):
                self.decomposition[c] = [int(x, 16) for x in f[5].split()]
        self.excluded = set()
        for first, last, f in fields(folder / "DerivedNormalizationProps.txt"):
            if f[0] == "Full_Composition_Exclusion":
                self.excluded.update(range(first, last + 1))
        self.bidi = ["L"] * N
        for first, last, f in fields(folder / "DerivedBidiClass.txt"):
            for c in range(first, last + 1):
                self.bidi[c] = f[0]
        self.joining = ["U"] * N
        for first, last, f in fields(folder / "DerivedJoiningType.txt"):
            for c in range(first, last + 1):
                self.joining[c] = f[0]
        self.check()

    def valid(self, c: int) -> bool:
        return self.status[c] == VALID

    def check(self) -> None:
        """Spot checks, and the assumptions the Temper code makes."""
        assert self.status[0xDF] == VALID and self.mapping[0x41] == [0x61]
        assert self.status[0xAD] == IGNORED and self.status[0xFFFD] == DISALLOWED
        assert self.bidi[0x5D0] == "R" and self.joining[0x628] == "D" and self.ccc[0x94D] == 9
        # Mapping gives only valid code points, and so does decomposing
        # them, so normalizing needs data only for them (and for disallowed
        # ones, in domain to Unicode).
        for target in self.mapping.values():
            assert all(self.valid(t) for t in target), target
        for c in range(N):
            if self.valid(c):
                assert all(self.valid(d) for d in self.full_decomposition(c)), hex(c)
            if 0xD800 <= c <= 0xDFFF:
                assert not self.valid(c)
        # Hangul syllables decompose by formula into jamo, which are valid.
        assert all(self.valid(c) for r in [(0x1100, 0x1112), (0x1161, 0x1175), (0x11A8, 0x11C2)]
                   for c in range(r[0], r[1] + 1))
        # Below U+0300 everything is a starter, so a string of them is NFC
        # as it is.
        assert all(self.ccc[c] == 0 for c in range(0x300))

    def full_decomposition(self, c: int) -> list[int]:
        parts = self.decomposition.get(c)
        if parts is None or is_hangul_syllable(c):
            return [c]
        return [d for p in parts for d in self.full_decomposition(p)]


# Encoding

def encode(numbers: list[int]) -> str:
    out = []
    for n in numbers:
        assert n >= 0, n
        digits = [n % BASE]
        n //= BASE
        while n:
            digits.append(n % BASE)
            n //= BASE
        out.append("".join(DIGITS[BASE + d] for d in reversed(digits[1:])) + DIGITS[digits[0]])
    return "".join(out)


def decode(text: str) -> list[int]:
    """The same as `decodeNumbers` in the Temper code."""
    out, value = [], 0
    for ch in text:
        d = DIGITS.index(ch)
        if d >= BASE:
            value = value * BASE + d - BASE
        else:
            out.append(value * BASE + d)
            value = 0
    return out


def zigzag(n: int) -> int:
    return n * 2 if n >= 0 else -n * 2 - 1


def unzigzag(n: int) -> int:
    return n >> 1 if n % 2 == 0 else -(n >> 1) - 1


def differences(numbers: list[int]) -> list[int]:
    out, last = [], 0
    for n in numbers:
        assert n >= last
        out.append(n - last)
        last = n
    return out


def sums(numbers: list[int]) -> list[int]:
    out, total = [], 0
    for n in numbers:
        total += n
        out.append(total)
    return out


def search(starts: list[int], c: int) -> int:
    """The index of the last start at or before `c`: the same search as
    `findRun` in src/idna.temper.md."""
    low, high = 0, len(starts)
    while high - low > 1:
        middle = (low + high) // 2
        if starts[middle] <= c:
            low = middle
        else:
            high = middle
    return low


# The IDNA mapping

def idna_ranges(data: Data) -> tuple[list[tuple[int, int, int]], list[int]]:
    """The mapping as ranges of (start, kind, detail), each running to the
    next one's start, and a pool of code points that mappings point into.
    For DELTA, every code point in the range maps to itself plus detail;
    for ALTERNATING, every other one does, from the first, and the rest
    are valid (upper and lowercase pairs); for POOL, detail is an index
    into the pool times 32 plus a length, and the range's code points map
    to that many pool entries each, one after another."""
    status, mapping = data.status, data.mapping

    def single_delta(c: int) -> int | None:
        m = mapping.get(c)
        return m[0] - c if m is not None and len(m) == 1 else None

    def delta_run(c: int) -> int:
        d, e = single_delta(c), c
        while e < N and single_delta(e) == d:
            e += 1
        return e - c

    def alternating_run(c: int) -> int:
        d, e = single_delta(c), c
        while e + 1 < N and single_delta(e) == d and status[e + 1] == VALID:
            e += 2
        return e - c

    ranges: list[tuple[int, int, int]] = []
    pool: list[int] = []
    c = 0
    while c < N:
        kind = status[c]
        if kind != POOL:
            e = c
            while e < N and status[e] == kind:
                e += 1
            ranges.append((c, kind, 0))
            c = e
            continue
        delta = single_delta(c)
        if delta is not None:
            run, alternating = delta_run(c), alternating_run(c)
            if alternating >= 4 and alternating > run:
                ranges.append((c, ALTERNATING, delta))
                c += alternating
                continue
            # A short run is better in the pool if the next code point
            # also maps to just one, so they can share a range there.
            if run >= 3 or single_delta(c + run) is None:
                ranges.append((c, DELTA, delta))
                c += run
                continue
        length, e = len(mapping[c]), c
        while (e < N and e in mapping and len(mapping[e]) == length
               and (e == c or length > 1 or (delta_run(e) < 3 and alternating_run(e) < 4))):
            e += 1
        assert length < 32
        ranges.append((c, POOL, len(pool) * 32 + length))
        for d in range(c, e):
            pool += mapping[d]
        c = e
    return ranges, pool


def idna_lookup(flat: list[int], pool: list[int], c: int) -> tuple[int, list[int] | None]:
    """The same lookup as `mapCodePoint` in src/idna.temper.md, on the
    decoded tables: the status, and the mapping if mapped."""
    k = search(flat[0::2], c) * 2
    value = flat[k + 1]
    kind, detail = value & 7, unzigzag(value >> 3)
    offset = c - flat[k]
    if kind == DELTA:
        return POOL, [c + detail]
    if kind == ALTERNATING:
        return (POOL, [c + detail]) if offset & 1 == 0 else (VALID, None)
    if kind == POOL:
        length = detail & 31
        at = (detail >> 5) + offset * length
        return POOL, pool[at:at + length]
    return kind, None


# Normalization

def decompositions(data: Data) -> list[tuple[int, int, int]]:
    """Canonical decompositions of valid code points, one level each, as
    (code point, first, second), sorted. Each is two code points, and each
    composes back, so NFC composes with the same table."""
    out = []
    for c in range(N):
        parts = data.decomposition.get(c)
        if data.valid(c) and parts is not None and not is_hangul_syllable(c):
            assert len(parts) == 2 and c not in data.excluded, hex(c)
            out.append((c, parts[0], parts[1]))
    # Every primary composite of valid code points is here, so composing
    # needs nothing more.
    for c, parts in data.decomposition.items():
        if (len(parts) == 2 and c not in data.excluded and not is_hangul_syllable(c)
                and all(data.valid(p) for p in parts)):
            assert data.valid(c), hex(c)
    return out


# Properties

def property_value(data: Data, c: int, seconds: set[int]) -> int:
    """Bidi class (bits 0-3), joining type (4-6), mark (7), canonical
    combining class (8-15), whether it decomposes (16), and whether it
    composes after another (17), as the second part of a decomposition
    (`seconds`), or as a Hangul vowel or trailing consonant."""
    bidi = data.bidi[c] if data.bidi[c] in BIDI else "OTHER"
    joining = data.joining[c] if data.joining[c] in JOINING else "U"
    mark = data.category[c] in ("Mn", "Mc", "Me")
    decomposes = (data.valid(c) and c in data.decomposition) or is_hangul_syllable(c)
    composes = c in seconds or 0x1161 <= c <= 0x1175 or 0x11A8 <= c <= 0x11C2
    return (BIDI.index(bidi) | JOINING.index(joining) << 4 | mark << 7
            | data.ccc[c] << 8 | decomposes << 16 | composes << 17)


# The bits that normalization reads.
NFC_MASK = 0xFF << 8 | 1 << 16 | 1 << 17


def property_constraint(data: Data, c: int, seconds: set[int]) -> tuple[int, int]:
    """The bits of `c`'s property value that matter, as a mask and a value:
    all of them for valid code points, those normalization reads for
    disallowed ones (which are all 0: no combining class, decomposition,
    or composition), and none for mapped and ignored ones, which mapping
    replaces."""
    if data.valid(c):
        return -1, property_value(data, c, seconds)
    if data.status[c] == DISALLOWED:
        assert property_value(data, c, seconds) & NFC_MASK == 0, hex(c)
        assert c not in data.decomposition, hex(c)
        return NFC_MASK, 0
    return 0, 0


def property_runs(data: Data, seconds: set[int]) -> list[tuple[int, int]]:
    """Runs of (start, value), where each code point's value meets its
    constraint: a run goes on while it can."""
    constraints = [property_constraint(data, c, seconds) for c in range(N)]
    runs: list[tuple[int, int]] = []
    for c in range(N):
        mask, value = constraints[c]
        if runs and runs[-1][1] & mask == value & mask:
            continue
        if mask != -1:
            # Take the value of the next code point that needs all of one,
            # if it fits, so the run can go on into it.
            e = c + 1
            while e < N and constraints[e][0] != -1:
                e += 1
            if e < N and constraints[e][1] & mask == value & mask:
                value = constraints[e][1]
        runs.append((c, value))
    return runs


# Writing

def text_lines(text: str, width: int = 72) -> str:
    """Text as the lines of a Temper multi-quoted string, without breaks."""
    return "\n".join(f"      ~{text[i:i + width]}" for i in range(0, len(text), width))


def write(version: str, ranges, pool, decomposed, runs, values, tables: dict[str, str]) -> None:
    def table(name: str) -> str:
        return f'      """\n{text_lines(tables[name])}\n'

    OUT.write_text(f"""# IDNA Tables

Generated by `scripts/idna_tables.py` from Unicode {version}'s data files
(see NOTICE); don't edit by hand. The script's notes explain the
choices.

The data that [international domain names](idna.temper.md) need: the
IDNA mapping, canonical decompositions for NFC, and the properties the
validity rules check. Lookups need to be right only for code points that
can get that far, which lets the tables leave out much.

Each table is a list of numbers written as text, a few characters per
number, decoded when the library loads. The text is printable ASCII but
`"`, `$`, `\\`, and space, which leaves 91 digits. Each number is in
base 45, most significant digit first: digits 45 to 89 go on, and 0 to
44 end the number. A digit's value is its place among those characters.

    let decodeNumbers(text: String): List<Int> {{
      let out = new ListBuilder<Int>();
      var value = 0;
      for (var i = String.begin; text.hasIndex(i); i = text.next(i)) {{
        let c = text[i];
        var digit = c - 0x21;
        if (c > 0x22) {{ digit -= 1; }}
        if (c > 0x24) {{ digit -= 1; }}
        if (c > 0x5C) {{ digit -= 1; }}
        if (digit >= 45) {{
          value = value * 45 + digit - 45;
        }} else {{
          out.add(value * 45 + digit);
          value = 0;
        }}
      }}
      out.toList()
    }}

Most tables are rows of `stride` numbers, sorted by the first, which is
stored as the difference from the row before.

    let decodeRows(stride: Int, text: String): List<Int> {{
      let numbers = decodeNumbers(text).toListBuilder();
      var total = 0;
      for (var k = 0; k < numbers.length; k += stride) {{
        total += numbers[k];
        numbers[k] = total;
      }}
      numbers.toList()
    }}

Signed numbers are zigzagged, so 0, -1, 1, -2, and 2 are written as 0,
1, 2, 3, and 4.

    let unzigzag(n: Int): Int {{
      if ((n & 1) == 0) {{ n >> 1 }} else {{ -(n >> 1) - 1 }}
    }}

## The IDNA Mapping

The status of every code point, and what mapped ones map to, from UTS
#46's `IdnaMappingTable.txt`, as {len(ranges)} ranges of two numbers: the first
code point, and a kind (the low three bits) and a zigzagged detail
(the rest). Each range runs to the next one's start. The kinds are:

- 0, valid (deviations too, since processing is nontransitional),
- 1, disallowed,
- 2, ignored,
- 3, mapped to the code point plus the detail,
- 4, alternating: the first code point and every other one after it
  are mapped to themselves plus the detail, and the rest are valid, as
  with uppercase and lowercase letters in turn,
- 5, mapped to code points in `idnaPool`: the detail's low five bits
  are how many for each code point in the range, and the rest is where
  the first code point's start.

<!-- -->

    let idnaRanges: List<Int> = decodeRows(2,
{table("idna")}    );

The {len(pool)} code points that mappings of kind 5 point into, each stored
as its zigzagged difference from the one before.

    let idnaPool: List<Int> = decodePool(
{table("pool")}    );

    let decodePool(text: String): List<Int> {{
      let numbers = decodeNumbers(text).toListBuilder();
      var last = 0;
      for (var k = 0; k < numbers.length; k += 1) {{
        last += unzigzag(numbers[k]);
        numbers[k] = last;
      }}
      numbers.toList()
    }}

## Normalization

The {len(decomposed)} canonical decompositions of valid code points, as
rows of a code point, then its first and second parts, sorted by code
point. The first part is stored as the code point minus it, zigzagged.
Every one is two code points, and each pair composes back, so NFC
composes with this table too. Hangul syllables decompose by formula.

    let decompositions: List<Int> = decodeDecompositions(
{table("decompositions")}    );

    let decodeDecompositions(text: String): List<Int> {{
      let rows = decodeRows(3, text).toListBuilder();
      for (var k = 0; k < rows.length; k += 3) {{
        rows[k + 1] = rows[k] - unzigzag(rows[k + 1]);
      }}
      rows.toList()
    }}

The same rows' indices (divided by three), sorted by first part and then
second part, for composing.

    let compositionOrder: List<Int> = sortCompositions();

    let sortCompositions(): List<Int> {{
      let order = new ListBuilder<Int>();
      for (var k = 0; k < decompositions.length; k += 3) {{
        order.add(k / 3);
      }}
      order.sort(fn (a: Int, b: Int): Int {{
        let byFirst = decompositions[a * 3 + 1] - decompositions[b * 3 + 1];
        if (byFirst != 0) {{ byFirst }} else {{
          decompositions[a * 3 + 2] - decompositions[b * 3 + 2]
        }}
      }});
      order.toList()
    }}

## Properties

Each code point's properties, as one number: its bidi class (bits 0 to
3), as an index in L, R, AL, AN, EN, ES, CS, ET, ON, BN, NSM, and any
other; its joining type (bits 4 to 6), as an index in U, L, R, D, and T,
with C as U; whether it's a mark (general category M, bit 7); its
canonical combining class (bits 8 to 15); whether it decomposes (bit
16); and whether it composes with a code point before it (bit 17).
They're right for valid code points, and the bits for normalization
(8 to 17) for disallowed ones too.

There are {len(values)} different numbers, sorted:

    let propertyValues: List<Int> = decodeNumbers(
{table("values")}    );

And {len(runs)} runs of a start and an index in `propertyValues`, each to
the next one's start:

    let propertyRuns: List<Int> = decodeRows(2,
{table("properties")}    );
""", encoding="utf-8")


def main() -> None:
    folder = unicode_data.ensure()
    data = Data(folder)

    ranges, pool = idna_ranges(data)
    idna_numbers = [n for (_, kind, detail), gap in zip(ranges, differences([r[0] for r in ranges]))
                    for n in (gap, zigzag(detail) * 8 + kind)]
    pool_numbers = [zigzag(b - a) for a, b in zip([0] + pool, pool)]
    decomposed = decompositions(data)
    decomposition_numbers = [n for (c, first, second), gap in
                             zip(decomposed, differences([d[0] for d in decomposed]))
                             for n in (gap, zigzag(c - first), second)]
    seconds = {second for _, _, second in decomposed}
    runs = property_runs(data, seconds)
    values = sorted({v for _, v in runs})
    property_numbers = [n for (_, value), gap in zip(runs, differences([r[0] for r in runs]))
                        for n in (gap, values.index(value))]
    tables = {"idna": encode(idna_numbers), "pool": encode(pool_numbers),
              "decompositions": encode(decomposition_numbers), "values": encode(values),
              "properties": encode(property_numbers)}

    # Check every code point through the decoded tables.
    flat = decode(tables["idna"])
    flat[0::2] = sums(flat[0::2])
    decoded_pool = sums([unzigzag(n) for n in decode(tables["pool"])])
    for c in range(N):
        kind, mapped = idna_lookup(flat, decoded_pool, c)
        assert kind == data.status[c], hex(c)
        assert kind != POOL or mapped == data.mapping[c], hex(c)
    rows = decode(tables["decompositions"])
    rows[0::3] = sums(rows[0::3])
    assert [(rows[k], rows[k] - unzigzag(rows[k + 1]), rows[k + 2])
            for k in range(0, len(rows), 3)] == decomposed
    property_flat = decode(tables["properties"])
    starts = sums(property_flat[0::2])
    decoded_values = decode(tables["values"])
    for c in range(N):
        mask, value = property_constraint(data, c, seconds)
        got = decoded_values[property_flat[search(starts, c) * 2 + 1]]
        assert got & mask == value & mask, hex(c)

    write(unicode_data.VERSION, ranges, pool, decomposed, runs, values, tables)
    sizes = ", ".join(f"{name} {len(text)}" for name, text in tables.items())
    print(f"Wrote {OUT.relative_to(ROOT)}, {OUT.stat().st_size} bytes; table text: {sizes}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
