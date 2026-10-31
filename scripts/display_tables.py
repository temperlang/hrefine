# /// script
# requires-python = ">=3.11"
# ///
"""Writes src/display-tables.temper.md, the Unicode data that showing a
domain in Unicode needs, as browsers do, from the files
scripts/unicode_data.py gets and pins.

    uv run scripts/display_tables.py

For each code point, the tables give a kind: 0 if a label holding it keeps
`xn--`, or else an index into `displayKinds`, which gives the code point's
scripts and its flags. The data, and what Hrefine changes, after
Chromium's `idn_spoof_checker.cc` and `skeleton_generator.cc`, at the
commit in CHROMIUM_COMMIT (see docs/plan.md, "Display formatting"):

- Shown at all: Identifier_Status Allowed (IdentifierStatus.txt; Chromium
  takes ICU's recommended and inclusion sets, Identifier_Type Recommended
  and Inclusion, which are the same code points), and valid in IDNA, less
  what Chromium removes from that set (CHROMIUM_REMOVED) and the deviation
  characters (ß, ς, and the joiners), which Chromium never shows.
- Scripts: the Script_Extensions (ScriptExtensions.txt, or else
  Scripts.txt) as a bit set over the scripts that have Allowed letters
  (SCRIPTS), others dropped; Common and Inherited code points with no
  extensions are 0, meaning any script. As UTS #39 resolves scripts, Han
  also has the bits for Japanese and Korean writing, kana Japanese, and
  Hangul Korean, so a label of Han and kana is one script, Japanese.
  Bopomofo, which would add a third, has no Allowed letters in Unicode 18
  (they're Limited_Use), nor does Grantha but for three marks Tamil
  shares.
- Look-alike (flag 1): the code point looks like ASCII letters or
  digits. Latin letters whose confusables.txt prototype is one ASCII
  letter or digit, and those Chromium's skeletons add
  (CHROMIUM_LATIN_LOOKALIKES); and letters of the scripts Chromium checks
  for whole-script look-alikes, in Chromium's list for that script
  (WHOLE_SCRIPT_LOOKALIKES), or whose prototype is ASCII letters and
  digits. Thorn `þ` looks like `p`, but display allows it under `.is` and
  `.fo`, as Chromium does.
- Mark (flag 2): general category M, for repeated marks.
- Digit look-alike (flag 4): in Chromium's list (DIGIT_LOOKALIKES), or
  with an ASCII digit as its prototype.
- Common (flag 8): Script Common or Inherited, which whole-script
  look-alikes ignore, as Chromium's do.
- Digit: for general category Nd, the code point of its zero, times 16,
  so digits of two numbering systems can't mix.

The tables are read where they are, with no decoding ahead and nothing
kept between calls, as the IDNA tables are. Code points that aren't valid
in IDNA never reach these tables (a label is checked against IDNA first),
so they take whichever kind is next to them, which merges most runs. The
code space up to the last shown code point is split into blocks of
1 << BLOCK_SHIFT; a block that's all one kind is that kind in
`displayBlocks`, and the rest point into `displayRuns`, strings of
numbers, a run's length and kind at a time, in the IDNA tables' base 32
(U+0060 to U+007F for each digit but the last, U+0040 to U+005F for the
last). The script checks every IDNA-valid code point's lookup, read as the
Temper code reads it, against the Unicode files.
"""

import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unicode_data  # noqa: E402
from idna_tables import encode, decode, fields, string_literal  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "display-tables.temper.md"
N = 0x110000
BLOCK_SHIFT = 12
FILES = ["IdnaMappingTable.txt", "UnicodeData.txt", "Scripts.txt", "ScriptExtensions.txt",
         "IdentifierStatus.txt", "confusables.txt"]

# The scripts with Allowed letters, in bit order, then Japanese and Korean
# writing.
SCRIPTS = ["Latn", "Grek", "Cyrl", "Armn", "Hebr", "Arab", "Thaa", "Deva", "Beng", "Guru",
           "Gujr", "Orya", "Taml", "Telu", "Knda", "Mlym", "Sinh", "Thai", "Laoo", "Tibt",
           "Mymr", "Geor", "Hang", "Ethi", "Khmr", "Hira", "Kana", "Hani", "Jpan", "Kore"]
WRITING = {"Hani": ["Jpan", "Kore"], "Hira": ["Jpan"], "Kana": ["Jpan"], "Hang": ["Kore"]}
LONG = {"Latin": "Latn", "Greek": "Grek", "Cyrillic": "Cyrl", "Armenian": "Armn", "Hebrew": "Hebr",
        "Arabic": "Arab", "Thaana": "Thaa", "Devanagari": "Deva", "Bengali": "Beng",
        "Gurmukhi": "Guru", "Gujarati": "Gujr", "Oriya": "Orya", "Tamil": "Taml", "Telugu": "Telu",
        "Kannada": "Knda", "Malayalam": "Mlym", "Sinhala": "Sinh", "Thai": "Thai", "Lao": "Laoo",
        "Tibetan": "Tibt", "Myanmar": "Mymr", "Georgian": "Geor", "Hangul": "Hang",
        "Ethiopic": "Ethi", "Khmer": "Khmr", "Hiragana": "Hira", "Katakana": "Kana",
        "Bopomofo": "Bopo", "Han": "Hani", "Grantha": "Gran"}

# The Chromium source these rules were checked against, on GitHub's
# mirror (github.com/chromium/chromium), in
# components/url_formatter/spoof_checks/ and components/url_formatter/.
CHROMIUM_COMMIT = "71eb2d8d6c1e036e26c3b1a912242cb11c5d019c"

# What Chromium's IDNSpoofChecker::SetAllowedUnicodeSet removes from the
# allowed set: U+0338, a long solidus overlay; Armenian hyphen, hyphen,
# right single quotation mark, hyphenation point, and the Katakana-Hiragana
# double hyphen; the modifier letters turned comma, apostrophe, and
# voicing (U+02EC); and rarely used blocks: Pinyin's letters in Latin
# Extended-B, Cyrillic Extended-C, Latin Extended Additional but
# Vietnamese, Greek Extended, Cyrillic Extended-B, and Latin Extended-D.
# (It also removes kra, which isn't Allowed, and on macOS a few letters
# its font shows blank, which Hrefine doesn't.)
CHROMIUM_REMOVED = [
    (0x0338, 0x0338), (0x058A, 0x058A), (0x2010, 0x2010), (0x2019, 0x2019), (0x2027, 0x2027),
    (0x30A0, 0x30A0), (0x02BB, 0x02BC), (0x02EC, 0x02EC),
    (0x01CD, 0x01DC), (0x1C80, 0x1C8F), (0x1E00, 0x1E9B), (0x1F00, 0x1FFF), (0xA640, 0xA69F),
    (0xA720, 0xA7FF),
]
# Deviation characters, which IDNA 2003 mapped differently: ß, final sigma,
# and the zero-width joiners. Chromium never shows them: its url_formatter
# decodes labels with UTS #46's transitional processing, which rejects them.
DEVIATIONS = [0x00DF, 0x03C2, 0x200C, 0x200D]

# The scripts Chromium checks for whole-script look-alikes of Latin, each
# with its letters that look like ASCII ones, from kWholeScriptConfusables
# in idn_spoof_checker.cc. For Thai, its Linux list, the longest. Letters
# that Unicode doesn't allow are in Chromium's lists but don't matter here.
WHOLE_SCRIPT_LOOKALIKES = {
    "Armn": "ագզէլհյոսւօՙ",
    "Cyrl": "аысԁеԍһіюкјӏморԗԛѕтԝхуъьҽпгѵѡ",
    "Ethi": "ሀሠሰስበነተከዐዕዘጠፐꬅ",
    "Geor": "იოყძხჽჿ",
    "Grek": "αικνρυωηοτ",
    "Hebr": "דוחיןסװײ׳ﬦ",
    "Beng": "০৭",
    "Deva": "ऽ०ॱ",
    "Gujr": "ડટ૦૧",
    "Guru": "੦੧",
    "Knda": "ಽ೦೧",
    "Mlym": "ടഠധനറ൦",
    "Orya": "ଠ୦୮",
    "Taml": "டப௦",
    "Telu": "౦౧",
    "Mymr": "ခဂငထပဝ၀၂ၔၜ\u1090\u1091\u1095\u1096\u1097",
    "Thai": "ทนบพรหเแ๐ดลปฟม",
}
# Latin letters Chromium's skeletons map to one ASCII letter that
# confusables.txt doesn't (extra_confusable_mapper_ in
# skeleton_generator.cc): kra, h, t, and b with stroke or topbar, and eng.
# Kra and ƅ aren't Allowed.
CHROMIUM_LATIN_LOOKALIKES = "ĸħŧƅŋ"
# Chromium's digit look-alikes (digit_lookalikes_ in idn_spoof_checker.cc).
DIGIT_LOOKALIKES = "θ२২੨૨೩೭շзҙӡउওਤ੩૩౩ဒვპੜკ੫丩ㄐճ৪੪୫૭୨౨"
# Prototypes that are ASCII digits, for digit look-alikes in any script.
# (0 and 1 aren't prototypes: they map to O and l.)
DIGIT_PROTOTYPES = set("0123456789")

LOOKALIKE, MARK, DIGIT_LOOKALIKE, COMMON = 1, 2, 4, 8
ZERO_SHIFT = 4


class Data:
    def __init__(self, folder: Path):
        self.valid = [False] * N
        for first, last, f in fields(folder / "IdnaMappingTable.txt"):
            if f[0] in ("valid", "deviation"):
                for c in range(first, last + 1):
                    self.valid[c] = True
        self.category = ["Cn"] * N
        self.zero: dict[int, int] = {}
        range_start = 0
        for line in (folder / "UnicodeData.txt").read_text(encoding="utf-8").splitlines():
            f = line.split(";")
            c = int(f[0], 16)
            if f[1].endswith(", First>"):
                range_start = c
                continue
            for d in range(range_start if f[1].endswith(", Last>") else c, c + 1):
                self.category[d] = f[2]
            if f[2] == "Nd":
                self.zero[c] = c - int(f[6])
        self.script = ["Zzzz"] * N
        long_to_short = {}
        for first, last, f in fields(folder / "Scripts.txt"):
            for c in range(first, last + 1):
                self.script[c] = f[0]
        self.extensions: dict[int, list[str]] = {}
        for first, last, f in fields(folder / "ScriptExtensions.txt"):
            for c in range(first, last + 1):
                self.extensions[c] = f[0].split()
        self.allowed = [False] * N
        for first, last, f in fields(folder / "IdentifierStatus.txt"):
            if f[0] == "Allowed":
                for c in range(first, last + 1):
                    self.allowed[c] = True
        self.prototype: dict[int, str] = {}
        for line in (folder / "confusables.txt").read_text(encoding="utf-8-sig").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                p = [x.strip() for x in line.split(";")]
                self.prototype[int(p[0], 16)] = "".join(chr(int(x, 16)) for x in p[1].split())
        del long_to_short

    def short_script(self, c: int) -> str:
        return LONG.get(self.script[c], self.script[c])

    def shown(self, c: int) -> bool:
        return (self.valid[c] and self.allowed[c] and c not in DEVIATIONS
                and not any(a <= c <= b for a, b in CHROMIUM_REMOVED))

    def mask(self, c: int) -> int:
        """The code point's scripts as bits; 0 for any script."""
        names = self.extensions.get(c)
        if names is None:
            s = self.script[c]
            if s in ("Common", "Inherited"):
                return 0
            names = [LONG[s]]
        bits = 0
        for name in names:
            for script in [name] + WRITING.get(name, []):
                if script in SCRIPTS:
                    bits |= 1 << SCRIPTS.index(script)
        return bits

    def lookalike(self, c: int) -> bool:
        if c < 0x80:
            return False
        char, script = chr(c), self.short_script(c)
        proto = self.prototype.get(c, "")
        if script == "Latn":
            if char == "þ":
                return False  # Allowed only under .is and .fo, in display.temper.md
            return char in CHROMIUM_LATIN_LOOKALIKES or re.fullmatch("[a-z0-9]", proto) is not None
        if script in WHOLE_SCRIPT_LOOKALIKES:
            return char in WHOLE_SCRIPT_LOOKALIKES[script] or re.fullmatch("[a-z0-9]+", proto) is not None
        return False

    def digit_lookalike(self, c: int) -> bool:
        return c >= 0x80 and (chr(c) in DIGIT_LOOKALIKES or self.prototype.get(c, "") in DIGIT_PROTOTYPES)

    def kind(self, c: int) -> tuple[int, int] | None:
        """(scripts, flags) for a shown code point, or None."""
        if not self.shown(c):
            return None
        mask = self.mask(c)
        if mask == 0 and self.script[c] not in ("Common", "Inherited"):
            return None  # only in scripts that have no Allowed letters
        flags = (LOOKALIKE if self.lookalike(c) else 0) | (MARK if self.category[c][0] == "M" else 0)
        flags |= DIGIT_LOOKALIKE if self.digit_lookalike(c) else 0
        flags |= COMMON if self.script[c] in ("Common", "Inherited") else 0
        flags |= self.zero.get(c, 0) << ZERO_SHIFT
        return mask, flags


class Tables:
    def __init__(self, data: Data):
        kinds: list[tuple[int, int] | None] = [None]
        index: dict[tuple[int, int] | None, int] = {None: 0}
        per = [-1] * N  # -1: not valid in IDNA, so any kind
        for c in range(N):
            if data.valid[c]:
                k = data.kind(c)
                if k not in index:
                    index[k] = len(kinds)
                    kinds.append(k)
                per[c] = index[k]
        self.kinds = kinds
        last = max(c for c in range(N) if per[c] > 0)
        size = ((last >> BLOCK_SHIFT) + 1) << BLOCK_SHIFT
        # Fill the don't-cares with the kind before (or after, at the start).
        filled, current = [0] * size, 0
        first_known = next(c for c in range(size) if per[c] >= 0)
        current = per[first_known]
        for c in range(size):
            if per[c] >= 0:
                current = per[c]
            filled[c] = current
        self.blocks: list[int] = []
        self.runs: list[str] = []
        for b in range(size >> BLOCK_SHIFT):
            values = filled[b << BLOCK_SHIFT:(b + 1) << BLOCK_SHIFT]
            # A run of don't-cares at the block's start takes the next kind.
            if per[b << BLOCK_SHIFT] < 0:
                firsts = [v for c, v in zip(range(b << BLOCK_SHIFT, (b + 1) << BLOCK_SHIFT), values)
                          if per[c] >= 0]
                if firsts:
                    k = 0
                    while per[(b << BLOCK_SHIFT) + k] < 0:
                        values[k] = firsts[0]
                        k += 1
            numbers: list[int] = []
            for v in values:
                if numbers and numbers[-1] == v:
                    numbers[-2] += 1
                else:
                    numbers += [1, v]
            if len(numbers) == 2:
                self.blocks.append(numbers[1])
            else:
                numbers[-2] = 0  # the last run goes to the block's end
                text = encode(numbers)
                if text in self.runs:
                    self.blocks.append(-1 - self.runs.index(text))
                else:
                    self.blocks.append(-1 - len(self.runs))
                    self.runs.append(text)

    def lookup(self, c: int) -> int:
        """As the Temper code reads it."""
        b = c >> BLOCK_SHIFT
        if b >= len(self.blocks):
            return 0
        entry = self.blocks[b]
        if entry >= 0:
            return entry
        numbers = decode(self.runs[-1 - entry])
        offset, k = c & ((1 << BLOCK_SHIFT) - 1), 0
        while numbers[k] != 0 and offset >= numbers[k]:
            offset -= numbers[k]
            k += 2
        return numbers[k + 1]


def check(tables: Tables, data: Data) -> None:
    for c in range(N):
        if data.valid[c]:
            assert tables.kinds[tables.lookup(c)] == data.kind(c), hex(c)
    kind = lambda s: tables.kinds[tables.lookup(ord(s))]  # noqa: E731
    latin = 1 << SCRIPTS.index("Latn")
    # ü is Latin; ß, kra, and ɐ aren't shown; ı and а look like ASCII.
    assert kind("ü") == (latin, 0) and kind("ß") is None and kind("ĸ") is None
    assert kind("ɐ") is None and kind("ı")[1] & LOOKALIKE and kind("а")[1] & LOOKALIKE
    assert kind("п")[1] & LOOKALIKE and not kind("ж")[1] & LOOKALIKE
    assert kind("7")[1] >> ZERO_SHIFT == 0x30 and kind("٣")[1] >> ZERO_SHIFT == 0x660
    assert kind("к")[1] & LOOKALIKE and kind("บ")[1] & LOOKALIKE and kind("ခ")[1] & LOOKALIKE
    assert kind("৪")[1] & DIGIT_LOOKALIKE and kind("з")[1] & DIGIT_LOOKALIKE
    assert not kind("ж")[1] & DIGIT_LOOKALIKE and kind("·")[1] & COMMON and kind("-")[1] & COMMON
    # Chromium's dangerous patterns treat Bopomofo as Japanese and Chinese
    # writing; no shown code point is Bopomofo without Han or kana.
    for c in range(N):
        ext = data.extensions.get(c, [])
        if data.valid[c] and data.kind(c) is not None and "Bopo" in ext:
            assert set(ext) & {"Hani", "Hira", "Kana"}, hex(c)
    bit = lambda *names: sum(1 << SCRIPTS.index(n) for n in names)  # noqa: E731
    assert kind("ー")[0] == bit("Hira", "Kana", "Jpan") and kind("日")[0] == bit("Hani", "Jpan", "Kore")
    assert kind("한")[0] == bit("Hang", "Kore") and kind("ㄅ") is None
    # Every Allowed letter outside Common and Inherited has a script here.
    for c in range(N):
        if data.valid[c] and data.allowed[c] and data.script[c] not in ("Common", "Inherited"):
            assert data.mask(c) != 0 or data.short_script(c) == "Bopo", hex(c)
    assert kind("\u0301") == (0b111, MARK | COMMON) and kind("\u0670")[1] & MARK
    assert all(kind(s) is not None for s in "日本語ひらがなカタカナ中文한국어примерשלוםمثال")


def write(version: str, tables: Tables) -> None:
    def items(values: list, indent: str, width: int = 90) -> str:
        lines, line = [], indent
        for v in values:
            item = f" {v},"
            if len(line) + len(item) > width and line != indent:
                lines.append(line)
                line = indent
            line += item
        lines.append(line)
        return "\n".join(lines)

    kinds = [n for k in tables.kinds[1:] for n in k]
    kinds = [0, 0] + kinds
    script_bits = "\n".join(
        f"    let script{name}: Int = 0x{1 << SCRIPTS.index(code):X};"
        for name, code in [("Latin", "Latn"), ("Greek", "Grek"), ("Cyrillic", "Cyrl"),
                           ("Armenian", "Armn"), ("Hebrew", "Hebr"), ("Thai", "Thai"),
                           ("Georgian", "Geor"), ("Myanmar", "Mymr"), ("Ethiopic", "Ethi"), ("Hiragana", "Hira"),
                           ("Katakana", "Kana"), ("Han", "Hani"), ("Hangul", "Hang"),
                           ("Japanese", "Jpan"), ("Korean", "Kore")])
    OUT.write_text(f"""# Display Tables

Generated by `scripts/display_tables.py` from Unicode {version}'s
`IdentifierStatus.txt`, `Scripts.txt`, `ScriptExtensions.txt`,
`confusables.txt`, `UnicodeData.txt`, and `IdnaMappingTable.txt`; don't
edit by hand. The script says what each part holds.

{textwrap.fill("The bits of the scripts that display checks by name, of all of them, in order: " + ", ".join(SCRIPTS) + " (the last two for Japanese and Korean writing).", 72)}

{script_bits}

Each kind's scripts (0 for any) and flags (1 for a look-alike of ASCII
letters, 2 for a mark, 4 for a look-alike of a digit, 8 for Common or
Inherited, and the zero of a decimal digit times 16), two numbers per
kind, from kind 1; kind 0 isn't shown.

    let displayKinds: List<Int> = [
{items(kinds, "     ", 84)}
    ];

The kind of each block of {1 << BLOCK_SHIFT} code points, from U+0000, or `-1 - k` for
the `k`th string of runs, each a length and a kind, the last running to
the block's end. Past the list, nothing is shown.

    let displayBlockShift = {BLOCK_SHIFT};

    let displayBlocks: List<Int> = [
{items(tables.blocks, "     ", 84)}
    ];

    let displayRuns: List<String> = [
{items([string_literal(t) for t in tables.runs], "     ", 84)}
    ];
""", encoding="utf-8")


def main() -> None:
    folder = unicode_data.ensure(FILES)
    data = Data(folder)
    tables = Tables(data)
    check(tables, data)
    write(unicode_data.VERSION, tables)
    size = OUT.stat().st_size
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(tables.kinds) - 1} kinds, {len(tables.blocks)} blocks, "
          f"{len(tables.runs)} run strings, {size} bytes", file=sys.stderr)


if __name__ == "__main__":
    main()
