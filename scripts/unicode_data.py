# /// script
# requires-python = ">=3.11"
# ///
"""Gets the Unicode data files that the IDNA and display tables are
generated from, into data/unicode-<version>/, and checks each against its
pinned SHA-256.

    uv run scripts/unicode_data.py           # get missing files, check all
    uv run scripts/unicode_data.py --repin   # after raising VERSION, or to
                                             # pin newly added files

The files are big (about 4.5 MB) and not in git; the tables generated from
them are. The generating script calls `ensure()` first, so one command
refreshes everything. To move to a new Unicode version, raise VERSION, run
with --repin (which downloads the files and records their hashes here),
regenerate the tables, and update NOTICE. The vendored IDNA tests must be
for the same version.

A file listed with an empty hash isn't pinned yet: run --repin where
unicode.org is reachable (not from the dev container), and commit the
hashes it writes here. Until then, ensure() skips it, so the IDNA tables
still build.
"""

import argparse
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "18.0.0"
PUBLIC = "https://www.unicode.org/Public"
# File name to (directory under PUBLIC/VERSION, SHA-256). Since Unicode 17,
# UTS #39's security data lives in PUBLIC/VERSION/security too.
FILES = {
    "IdnaMappingTable.txt": ("idna", "a03b1eb38032268c696406a83f0972d6a815acd2c8d4151d42ec0fda70ffced1"),
    "UnicodeData.txt": ("ucd", "0736451de439ae7baf1425136617da495e09ee5afbe6e394374db7009ea08950"),
    "DerivedNormalizationProps.txt": ("ucd", "98ac7f67d985fe781e317f6182e885e94cabb0c314769e6dd73e48b226931ccd"),
    "DerivedBidiClass.txt": ("ucd/extracted", "d9e23222522551348ea1ccfbb4f62efbf98982afb95840f8959c08ed992c5607"),
    "DerivedJoiningType.txt": ("ucd/extracted", "e2408ff2c92b175b0f7bf62c989bbb54c7b077528fe31f8d69b96fa09e7d61ed"),
    # For showing hosts as browsers do (src/display.temper.md): scripts, and
    # UTS #39's identifier status, types, and confusables.
    "Scripts.txt": ("ucd", "0071fd81b6aeae25f6e8bce8efec3066a6476a91b49bdb2f52dc76e817862a6a"),
    "ScriptExtensions.txt": ("ucd", "5c9d34a922f687726f2a8bcf57d49f905987e51f1b21b58c95a00fbe255cec23"),
    "IdentifierStatus.txt": ("security", "5863c7d99ca18f213c41c7318aa5528bebfb6d32ec0f1d5944e37192c119aebd"),
    "IdentifierType.txt": ("security", "fa24851acc669e58670e354e7b98a4ec8f52a809ec4f80524b6a60efdb868831"),
    "confusables.txt": ("security", "6ed3ee967c9dfdf6677d563c9985182fbc50a2efb7d6059cd57b2e2ce18f5b92"),
}


def data_dir() -> Path:
    return ROOT / "data" / f"unicode-{VERSION}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(name: str) -> Path:
    path = data_dir() / name
    url = f"{PUBLIC}/{VERSION}/{FILES[name][0]}/{name}"
    print(f"Getting {url}", file=sys.stderr)
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        path.write_bytes(response.read())
    return path


def ensure(names: list[str] | None = None) -> Path:
    """Gets any missing file and checks every file's hash; returns the
    directory holding them. Given names, it handles just those, and fails
    on one not yet pinned; otherwise it skips files not yet pinned."""
    for name in names or FILES:
        expected = FILES[name][1]
        if expected == "":
            if names:
                sys.exit(f"{name} isn't pinned yet: run this script with --repin "
                         "where unicode.org is reachable, and commit the hashes")
            continue
        path = data_dir() / name
        if not path.exists():
            download(name)
        actual = sha256(path)
        if actual != expected:
            sys.exit(f"{path} has SHA-256 {actual}, not the pinned {expected}; "
                     "delete it to download it again, or --repin after raising VERSION")
    return data_dir()


def repin() -> None:
    """Downloads every file for VERSION and records its hash in this script."""
    script = Path(__file__)
    text = script.read_text(encoding="utf-8")
    for name in FILES:
        digest = sha256(download(name))
        text, count = re.subn(rf'("{re.escape(name)}": \("[^"]+", ")[0-9a-f]*(")', rf"\g<1>{digest}\g<2>", text)
        assert count == 1, name
    script.write_text(text, encoding="utf-8")
    print(f"Pinned the Unicode {VERSION} files' hashes", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repin", action="store_true", help="download every file and record new hashes")
    if p.parse_args().repin:
        repin()
    else:
        print(ensure())


if __name__ == "__main__":
    main()
