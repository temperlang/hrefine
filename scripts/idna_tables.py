# /// script
# requires-python = ">=3.11"
# ///
"""Writes src/idna-tables.temper.md, the Unicode data that international
domain names (UTS #46, as the URL Standard runs it) need, from the Unicode
files that scripts/unicode_data.py gets and pins.

    uv run scripts/idna_tables.py

For each code point, the tables give:

- Its IDNA mapping: its status (valid, ignored, mapped, or disallowed)
  and, if mapped, what it maps to. With nontransitional processing,
  deviations (`ß`, `ς`, and the zero-width joiners) are valid.
- Its properties: canonical combining class, bidi class (for the Bidi
  rule), joining type (for the ContextJ rules), whether it's a mark
  (labels can't start with one), and two bits for NFC.
- Its canonical decomposition, if any, for NFC, which composes with the
  same data.

Mapping gives only valid code points, and domain to ASCII fails at once on
a disallowed one, so the rest of the tables need to be right only for
valid code points, which lets them leave out much. Domain to Unicode keeps
disallowed code points, so they need the right combining class (always 0)
and no decomposition (they have none), for NFC.

The tables are read where they are, a block of code points at a time, with
no decoding ahead and nothing kept between calls, so the library has no
state to share between threads, and a domain pays only for the blocks its
code points are in. The code space is split into blocks of 4096 code
points, and those into 64 sub-blocks of 64. A block or sub-block that's
all one run (one mapping and one set of properties) is a number in a list;
the rest are strings of numbers, each in base 32, most significant digit
first: U+0060 to U+007F for each digit but the last, and U+0040 to U+005F
for the last, so a digit's value is its low five bits, and only `\\` and
U+007F need escapes. The script checks every code point's lookups, read
as the Temper code reads them, against the Unicode files.

Tried and dropped (2026-10-29): sub-blocks of 32, which made domain to
ASCII about 17% faster in Python and Lua, but the library 9 KB bigger and
C#'s load slower; and storing each run's end instead of its length, which
was slower to read and bigger.
"""

import sys
import textwrap
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unicode_data  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "idna-tables.temper.md"
N = 0x110000
BLOCK_SHIFT = 12
SUB_SHIFT = 6
SUBS = 1 << (BLOCK_SHIFT - SUB_SHIFT)

# Mapping kinds, as records store them, in the low three bits. Data.status
# uses VALID, DISALLOWED, IGNORED, and POOL (for any mapping).
VALID, DISALLOWED, IGNORED, DELTA, EVEN, ODD, POOL = range(7)

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
        self.nfc_quick_check: dict[int, str] = {}
        for first, last, f in fields(folder / "DerivedNormalizationProps.txt"):
            if f[0] == "Full_Composition_Exclusion":
                self.excluded.update(range(first, last + 1))
            elif f[0] == "NFC_QC":
                for c in range(first, last + 1):
                    self.nfc_quick_check[c] = f[1]
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
                # NFC's quick check never says No for a valid code point, so
                # a string of them is in NFC unless one could compose with
                # the one before (Maybe) or marks are out of order.
                assert self.nfc_quick_check.get(c) != "N", hex(c)
            if 0xD800 <= c <= 0xDFFF:
                assert not self.valid(c)
        assert all(self.valid(c) == (not 0x41 <= c <= 0x5A) for c in range(0x80))
        # Hangul syllables decompose by formula into jamo, which are valid.
        assert all(self.valid(c) for r in [(0x1100, 0x1112), (0x1161, 0x1175), (0x11A8, 0x11C2)]
                   for c in range(r[0], r[1] + 1))

    def full_decomposition(self, c: int) -> list[int]:
        parts = self.decomposition.get(c)
        if parts is None or is_hangul_syllable(c):
            return [c]
        return [d for p in parts for d in self.full_decomposition(p)]


# The IDNA mapping

def idna_ranges(data: Data) -> list[tuple[int, int, int]]:
    """The mapping as ranges of (start, kind, delta), each running to the
    next one's start. For DELTA, every code point in the range maps to
    itself plus delta; for EVEN or ODD, every even or odd one does, and the
    rest are valid (upper and lowercase pairs); for POOL, each maps to its
    own list of code points, all of one length."""
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
                ranges.append((c, ODD if c & 1 else EVEN, delta))
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
        ranges.append((c, POOL, length))
        c = e
    return ranges


def mapping_keys(data: Data) -> list[tuple[int, int]]:
    """Each code point's mapping, as a kind and a detail that a run of code
    points can share: the delta for DELTA, EVEN, and ODD, and the length of
    each one's mapping for POOL."""
    keys: list[tuple[int, int]] = [(DISALLOWED, 0)] * N
    ranges = idna_ranges(data)
    for i, (start, kind, detail) in enumerate(ranges):
        end = ranges[i + 1][0] if i + 1 < len(ranges) else N
        for c in range(start, end):
            keys[c] = (kind, detail)
    return keys


# Normalization

def decompositions(data: Data) -> list[tuple[int, int, int]]:
    """Canonical decompositions of valid code points, one level each, as
    (code point, first, second), sorted. Each is two code points, and each
    composes back, so NFC composes with the same data."""
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
    may compose with the one before (17)."""
    bidi = data.bidi[c] if data.bidi[c] in BIDI else "OTHER"
    joining = data.joining[c] if data.joining[c] in JOINING else "U"
    mark = data.category[c] in ("Mn", "Mc", "Me")
    decomposes = (data.valid(c) and c in data.decomposition) or is_hangul_syllable(c)
    # NFC's quick check Maybe: it may compose with the one before, as the
    # second part of a decomposition (`seconds`), a Hangul vowel or trailing
    # consonant, or as one whose decomposition starts with such a part.
    composes = data.nfc_quick_check.get(c) == "M"
    if c in seconds or 0x1161 <= c <= 0x1175 or 0x11A8 <= c <= 0x11C2:
        assert composes, hex(c)
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


# Encoding

def encode(numbers: list[int]) -> str:
    """Base 32, as the module notes say."""
    out = []
    for n in numbers:
        assert n >= 0, n
        digits = [n & 31]
        n >>= 5
        while n:
            digits.append(n & 31)
            n >>= 5
        out.append("".join(chr(0x60 + d) for d in reversed(digits[1:])) + chr(0x40 + digits[0]))
    return "".join(out)


def zigzag(n: int) -> int:
    return n * 2 if n >= 0 else -n * 2 - 1


def unzigzag(n: int) -> int:
    return n >> 1 if n % 2 == 0 else -(n >> 1) - 1


class Tables:
    """The tables, as strings for blocks and sub-blocks, and the property
    values that records point to."""

    def __init__(self, data: Data):
        self.data = data
        keys = mapping_keys(data)
        decomposed = decompositions(data)
        seconds = {second for _, _, second in decomposed}
        constraints = [property_constraint(data, c, seconds) for c in range(N)]
        self.ascii = [property_value(data, c, seconds) for c in range(0x80)]
        by_code = {c: (first, second) for c, first, second in decomposed}
        by_second: dict[int, list[tuple[int, int]]] = {}
        for c, first, second in decomposed:
            by_second.setdefault(second, []).append((first, c))
        # Records per sub-block: (length, kind and detail, property value),
        # and its pool, decompositions, and compositions.
        subs = []
        for base in range(0, N, 1 << SUB_SHIFT):
            end = base + (1 << SUB_SHIFT)
            records, pool, c = [], [], base
            while c < end:
                key = keys[c]
                mask, value = constraints[c]
                if mask != -1:
                    # Take the value of the next code point in the run that
                    # needs all of one, if it fits, so the run can go on.
                    e = c + 1
                    while e < end and keys[e] == key and constraints[e][0] != -1:
                        e += 1
                    if e < end and keys[e] == key and constraints[e][1] & mask == value & mask:
                        value = constraints[e][1]
                e, pool_start = c, len(pool)
                while (e < end and keys[e] == key
                       and value & constraints[e][0] == constraints[e][1] & constraints[e][0]):
                    if key[0] == POOL:
                        assert len(data.mapping[e]) == key[1]
                        pool += data.mapping[e]
                    e += 1
                kind, detail = key
                if kind in (DELTA, EVEN, ODD):
                    mapped = kind + 8 * zigzag(detail)
                elif kind == POOL:
                    mapped = kind + 8 * (pool_start * 32 + detail)
                else:
                    mapped = kind
                records.append([e - c, mapped, value])
                c = e
            records[-1][0] = 0
            decomps = [(c - base, *by_code[c]) for c in range(base, end) if c in by_code]
            comps = sorted((second - base, first, c) for second in range(base, end)
                           for first, c in by_second.get(second, []))
            subs.append((base, records, pool, decomps, comps))
        counts = Counter(r[2] for _, records, *_ in subs for r in records)
        self.values = [v for v, _ in counts.most_common()]
        # Lookups return a run's mapping and property index as one number.
        assert len(self.values) <= 128
        assert all(r[1] < 1 << 24 for _, records, *_ in subs for r in records)
        index = {v: k for k, v in enumerate(self.values)}
        self.sub_texts = []
        for base, records, pool, decomps, comps in subs:
            numbers = [n for length, mapped, value in records for n in (length, mapped, index[value])]
            if pool or decomps or comps:
                numbers += [len(pool), len(decomps)]
                last = base
                for target in pool:
                    numbers.append(zigzag(target - last))
                    last = target
                last = 0
                for offset, first, second in decomps:
                    numbers += [offset - last, zigzag(base + offset - first), second]
                    last = offset
                last_offset = last_first = 0
                for offset, first, composite in comps:
                    if offset != last_offset:
                        last_first = 0
                    numbers += [offset - last_offset, first - last_first, zigzag(composite - first)]
                    last_offset, last_first = offset, first
            # ASCII is never looked up, since it's all valid but uppercase
            # letters, which map to lowercase.
            self.sub_texts.append(encode([0, 0, 0] if base < 0x80 else numbers))
        # Blocks of 4096: the run's mapping and property index, as one
        # number, if it's all one run, or else -1 less the index of its
        # split block. For each split block, a number for each of its 64
        # sub-blocks, in the same way, or else -1 less the index of its
        # string among the split block's.
        self.blocks: list[int] = []
        self.sub_blocks: list[list[int]] = []
        self.texts: list[list[str]] = []
        for b in range(N >> BLOCK_SHIFT):
            entries, texts = [], []
            for text in self.sub_texts[b * SUBS:(b + 1) * SUBS]:
                numbers = decode(text)
                if len(numbers) == 3:
                    entries.append(numbers[1] << 7 | numbers[2])
                else:
                    if text not in texts:
                        texts.append(text)
                    entries.append(-1 - texts.index(text))
            if len(set(entries)) == 1 and entries[0] >= 0:
                self.blocks.append(entries[0])
            else:
                self.blocks.append(-1 - len(self.sub_blocks))
                self.sub_blocks.append(entries)
                self.texts.append(texts)

    # Lookups, read as the Temper code reads them.

    def entry(self, c: int) -> int:
        block = self.blocks[c >> BLOCK_SHIFT]
        if block >= 0:
            return block
        return self.sub_blocks[-1 - block][(c >> SUB_SHIFT) & (SUBS - 1)]

    def text(self, c: int) -> tuple[str, int, int]:
        """The string for `c`, the offset of `c` in it, and its start."""
        entry = self.entry(c)
        assert entry < 0
        mask = (1 << SUB_SHIFT) - 1
        split = -1 - self.blocks[c >> BLOCK_SHIFT]
        return self.texts[split][-1 - entry], c & mask, c - (c & mask)

    def record(self, c: int) -> tuple[list[int], int, int, int]:
        """The numbers of `c`'s string, the index just past its record
        (negative if it isn't the last), the record's start offset, and its
        kind and detail and property index."""
        text, offset, _ = self.text(c)
        numbers, at, start = decode(text), 0, 0
        while True:
            length, mapped, prop = numbers[at:at + 3]
            at += 3
            if length == 0 or offset < start + length:
                return numbers, at if length == 0 else -at, start, mapped, prop
            start += length

    def extras(self, numbers: list[int], at: int) -> int:
        """The index of the pool's length, past the records, or -1."""
        if at < 0:
            at = -at
            while numbers[at] != 0:
                at += 3
            at += 3
        return at if at < len(numbers) else -1

    def lookup(self, c: int) -> tuple[int, list[int] | None, int]:
        """`c`'s mapping kind, what it maps to if mapped, and properties."""
        if self.entry(c) >= 0:
            numbers, at, start, mapped, prop = None, 0, 0, self.entry(c) >> 7, self.entry(c) & 127
        else:
            numbers, at, start, mapped, prop = self.record(c)
        kind, detail = mapped & 7, mapped >> 3
        targets = None
        if kind == DELTA or (kind == EVEN and c & 1 == 0) or (kind == ODD and c & 1 == 1):
            targets = [c + unzigzag(detail)]
        elif kind in (EVEN, ODD):
            kind = VALID
        elif kind == POOL:
            length = detail & 31
            first = (detail >> 5) + (self.text(c)[1] - start) * length
            at = self.extras(numbers, at) + 2
            last = self.text(c)[2]
            values = []
            for k in range(first + length):
                last += unzigzag(numbers[at + k])
                values.append(last)
            targets = values[first:]
        return kind, targets, self.values[prop]

    def decomposition(self, c: int) -> tuple[int, int] | None:
        if self.entry(c) >= 0:
            return None
        numbers, at, *_ = self.record(c)
        at = self.extras(numbers, at)
        if at < 0:
            return None
        pool, count = numbers[at:at + 2]
        at += 2 + pool
        offset, base = self.text(c)[1:]
        last = 0
        for k in range(count):
            delta, first, second = numbers[at + 3 * k:at + 3 * k + 3]
            last += delta
            if last == offset:
                return c - unzigzag(first), second
        return None

    def composition(self, first: int, second: int) -> int:
        if self.entry(second) >= 0:
            return -1
        numbers, at, *_ = self.record(second)
        at = self.extras(numbers, at)
        if at < 0:
            return -1
        pool, count = numbers[at:at + 2]
        at += 2 + pool + 3 * count
        offset = self.text(second)[1]
        last_offset = last_first = 0
        while at < len(numbers):
            delta, first_delta, composite = numbers[at:at + 3]
            at += 3
            if delta != 0:
                last_first = 0
            last_offset += delta
            last_first += first_delta
            if last_offset == offset and last_first == first:
                return first + unzigzag(composite)
        return -1


def decode(text: str) -> list[int]:
    """The same as the Temper code's reading."""
    out, value = [], 0
    for ch in text:
        c = ord(ch)
        if c >= 0x60:
            value = value << 5 | c & 31
        else:
            out.append(value << 5 | c & 31)
            value = 0
    return out


def check(tables: Tables, data: Data) -> None:
    """Every code point's lookups, against the Unicode files."""
    decomposed = decompositions(data)
    seconds = {second for _, _, second in decomposed}
    by_code = {c: (first, second) for c, first, second in decomposed}
    for c in range(0x80, N):
        kind, targets, value = tables.lookup(c)
        status = data.status[c]
        if status == POOL:
            assert targets == data.mapping[c], hex(c)
        else:
            assert kind == status and targets is None, hex(c)
        mask, want = property_constraint(data, c, seconds)
        assert value & mask == want & mask, hex(c)
        if data.valid(c) or status == DISALLOWED:
            assert tables.decomposition(c) == by_code.get(c), hex(c)
    for c, first, second in decomposed:
        assert tables.composition(first, second) == c, hex(c)
    assert tables.composition(0x61, 0x62) == -1


# Writing

def string_literal(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace("\x7f", "\\u{7F}") + '"'


def write(version: str, tables: Tables) -> None:
    def items(values: list, indent: str, width: int = 90) -> list[str]:
        lines, line = [], indent
        for v in values:
            item = f" {v},"
            if len(line) + len(item) > width and line != indent:
                lines.append(line)
                line = indent
            line += item
        lines.append(line)
        return lines

    def nested(lists: list[list], literal) -> str:
        lines = []
        for k, values in enumerate(lists):
            b = tables.blocks.index(-1 - k)
            lines.append(f"      [ // {k}: U+{b << BLOCK_SHIFT:04X}")
            lines += items([literal(v) for v in values], "       ")
            lines.append("      ],")
        return "\n".join(lines)

    def numbers(values: list[int], indent: str) -> str:
        return "\n".join(items(values, indent, 80))

    split = len(tables.sub_blocks)
    strings = [t for texts in tables.texts for t in texts]
    blocks_paragraph = textwrap.fill(
        f"The code space is split into {len(tables.blocks)} blocks of {1 << BLOCK_SHIFT} code "
        f"points, and each of those into {SUBS} sub-blocks of {1 << SUB_SHIFT}. Most blocks "
        "and sub-blocks are all one run of code points with the same mapping and properties, "
        "given as one number: the run's mapping times 128, plus its properties' index in "
        "`propertyValues`. `idnaBlocks` has that number for each block that's all one run, "
        f"and -1 less its index in `idnaSubBlocks` for each of the other {split}. Those have a "
        "number for each sub-block, the same way, but for one that's not all one run, which "
        "has -1 less its index in its block's list in `idnaTexts`. The "
        f"{len(strings)} strings hold {sum(map(len, strings))} characters.", 72)
    OUT.write_text(f"""# IDNA Tables

Generated by `scripts/idna_tables.py` from Unicode {version}'s data files
(see NOTICE); don't edit by hand. The script's notes explain the
choices.

The data that [international domain names](idna.temper.md) need, for
each code point: its IDNA mapping, its properties, and its canonical
decomposition, for NFC. Lookups need to be right only for code points
that can get that far, which lets the tables leave out much.

They're read where they are, by the lookups in
[IDNA](idna.temper.md#lookups), with no decoding ahead and nothing kept
between calls: loading the library costs only these constants, a domain
reads only the blocks its code points are in, and there's no state for
threads to share.

## Blocks

{blocks_paragraph}

A sub-block's string is numbers, each written in base 32, most
significant digit first, with U+0060 to U+007F for each digit but the
last, and U+0040 to U+005F for the last, so a digit's value is its low
five bits. It starts with runs of code points, three numbers each: the
run's length (0 for the last, which runs to the end), its mapping, and
its properties' index.

A mapping's low three bits are its kind, and the rest its detail. The
kinds are:

- 0, valid (deviations too, since processing is nontransitional),
- 1, disallowed,
- 2, ignored,
- 3, mapped to the code point plus the detail, zigzagged (so 0, -1, 1,
  -2, and 2 are written as 0, 1, 2, 3, and 4),
- 4 and 5, alternating: even (4) or odd (5) code points are mapped as
  in 3, and the rest are valid, as with uppercase and lowercase letters
  in turn,
- 6, mapped to code points in the string's pool: the detail's low five
  bits are how many for each code point in the run, and the rest is
  where the run's first code point's start.

If the string goes on, next are the pool's length and the count of
decompositions, then the pool, each code point zigzagged as the
difference from the one before (or from the sub-block's start); the
decompositions of valid code points, as three numbers each: the code
point's offset from the one before (or the sub-block's start), the code
point minus its first part, zigzagged, and its second part; and last,
the compositions whose second part is in this sub-block, by second and
then first part, as three numbers each: the second part's offset from
the one before, the first part, less the one before if the second part
is the same, and the composite minus the first part, zigzagged. Every
decomposition is two code points, and each pair composes back, so NFC
composes with this data too. Hangul syllables go by formula.

Blocks and sub-blocks are this many code points, as powers of two:

    let idnaBlockShift = {BLOCK_SHIFT};
    let idnaSubBlockShift = {SUB_SHIFT};

    let idnaBlocks: List<Int> = [
{numbers(tables.blocks, "     ")}
    ];

    let idnaSubBlocks: List<List<Int>> = [
{nested(tables.sub_blocks, str)}
    ];

    let idnaTexts: List<List<String>> = [
{nested(tables.texts, string_literal)}
    ];

## Properties

Each code point's properties, as one number: its bidi class (bits 0 to
3), as an index in L, R, AL, AN, EN, ES, CS, ET, ON, BN, NSM, and any
other; its joining type (bits 4 to 6), as an index in U, L, R, D, and T,
with C as U; whether it's a mark (general category M, bit 7); its
canonical combining class (bits 8 to 15); whether it decomposes (bit
16); and whether it composes with a code point before it (bit 17, NFC's
quick check Maybe). They're right for valid code points, and the bits
for normalization (8 to 17) for disallowed ones too.

There are {len(tables.values)} different values, most used first:

    let propertyValues: List<Int> = [
{numbers(tables.values, "     ")}
    ];

And ASCII's, which labels are often mostly made of:

    let asciiProperties: List<Int> = [
{numbers(tables.ascii, "     ")}
    ];
""", encoding="utf-8")


def main() -> None:
    folder = unicode_data.ensure()
    data = Data(folder)
    tables = Tables(data)
    check(tables, data)
    write(unicode_data.VERSION, tables)
    texts = [t for texts in tables.texts for t in texts]
    print(f"Wrote {OUT.relative_to(ROOT)}, {OUT.stat().st_size} bytes; {len(texts)} strings, "
          f"{sum(map(len, texts))} characters, {len(tables.values)} property values",
          file=sys.stderr)


if __name__ == "__main__":
    main()
