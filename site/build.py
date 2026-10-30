# /// script
# requires-python = ">=3.11"
# ///
"""Builds Hrefine's site into `site/build/`.

    temper build -b js
    uv run site/build.py
    python3 -m http.server --bind 127.0.0.1 -d site/build

Copies Temper's JS output for Hrefine, with Temper's JS runtime, as plain ES
modules, which the page's import map names, so the page parses URLs live
with the same library as every other language. No bundler, so nothing to
install; the cost is size (see `sizes.json`).

Renders the opening and the trick gallery into the page from
`site/gallery.json` and `site/recorded.json` (other parsers' answers, which
`site/record/record.py` records), so they show before any script runs. The
fix's code comes from each tour's "Using it safely" section, which CI runs
in every language, and the tours themselves go in `tour/`.
"""

import gzip
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "build"
JS = ROOT / "temper.out" / "js"
TOUR = ROOT / "demos" / "tour"

# Each tour's source, by the extension the page asks for, in the site's
# language order.
TOURS = {
    "cpp": "cpp/tour.cpp",
    "cs": "csharp/Program.cs",
    "java": "java/src/main/java/Tour.java",
    "js": "js/tour.js",
    "lua": "lua/tour.lua",
    "py": "py/tour.py",
    "rs": "rust/src/main.rs",
}

# Parsers in the order the opening shows them, after the browser and
# Hrefine: those that differ from the browser first.
HERO_FIRST = ["browser", "hrefine"]


def esc(text):
    return html.escape(text, quote=True)


def shown(text):
    """Text as HTML, with tabs and newlines shown as symbols."""
    out = esc(text)
    out = out.replace("\t", '<span class="ctl" title="tab">\\t</span>')
    return out.replace("\n", '<span class="ctl" title="newline">\\n</span>')


def status(answer, browser):
    """How an answer compares with the browser's: same, differs, or rejects."""
    if not answer["ok"]:
        return "same" if not browser["ok"] else "rejects"
    if not browser["ok"]:
        return "differs"
    return "same" if answer.get("host") == browser.get("host") else "differs"


STATUS_TEXT = {"same": "same as the browser", "differs": "differs from the browser", "rejects": "rejects it"}
STATUS_ICON = {"same": "✓", "differs": "✗", "rejects": "–"}


def host_html(answer):
    if not answer["ok"]:
        return '<span class="none">error</span>'
    host = answer.get("host")
    if host is None:
        return '<span class="none">no host</span>'
    if host == "":
        return '<span class="none">empty host</span>'
    return f"<code>{shown(host)}</code>"


def names(recorded):
    out = {p["id"]: p["name"] for p in recorded["parsers"]}
    out["browser"] = "Browsers"
    out["hrefine"] = "Hrefine"
    return out


def hero(gallery, recorded):
    """The opening: one URL, and each parser's answer to "what host?"."""
    row = recorded["results"][0]
    assert row["input"] == gallery["hero"][0]["input"]
    answers = row["answers"]
    browser = answers["browser"]
    label = names(recorded)
    label["browser"] = "Your browser"
    label["hrefine"] = "Hrefine, in all seven languages"
    others = [p["id"] for p in recorded["parsers"] if p["id"] not in HERO_FIRST]
    order = {"differs": 0, "rejects": 1, "same": 2}
    others.sort(key=lambda id: order[status(answers[id], browser)])
    chips = []
    for id in HERO_FIRST + others:
        answer = answers[id]
        st = "browser" if id == "browser" else status(answer, browser)
        note = "the standard's answer" if id == "browser" else STATUS_TEXT[st]
        icon = "" if id == "browser" else f'<span class="icon" aria-hidden="true">{STATUS_ICON[st]}</span> '
        chips.append(
            f'<li class="answer {st}" data-parser="{id}">'
            f'<span class="who">{esc(label[id])}</span>'
            f'<span class="host">{host_html(answer)}</span>'
            f'<span class="verdict">{icon}<span class="verdict-text">{note}</span></span></li>'
        )
    return (
        f'<div class="hero-demo" data-input="{esc(row["input"])}" data-title="opening">'
        f'<p class="the-url"><code>{shown(row["input"])}</code></p>\n<ul class="answers">{"".join(chips)}</ul>'
        f'<details class="hero-details"><summary>How each parser reads it</summary>{card_table(row, recorded)}</details>'
        "</div>"
    )


def card_table(row, recorded):
    answers = row["answers"]
    browser = answers["browser"]
    label = names(recorded)
    ids = ["browser", "hrefine"] + [p["id"] for p in recorded["parsers"] if p["id"] not in HERO_FIRST]
    rows = []
    for id in ids:
        answer = answers[id]
        st = "browser" if id == "browser" else status(answer, browser)
        verdict = "" if id == "browser" else f'<span class="icon" aria-hidden="true">{STATUS_ICON[st]}</span> {STATUS_TEXT[st]}'
        reads = (
            f"<code>{shown(answer['href'])}</code>"
            if answer["ok"]
            else f'<span class="error">{esc(answer["error"])}</span>'
        )
        rows.append(
            f'<tr class="{st}" data-parser="{id}"><th scope="row">{esc(label[id])}</th>'
            f'<td class="host">{host_html(answer)}</td><td class="verdict">{verdict}</td>'
            f'<td class="reads">{reads}</td></tr>'
        )
    return (
        '<div class="table-scroll" tabindex="0"><table class="compare">'
        '<thead><tr><th scope="col">Parser</th><th scope="col">Host</th><th scope="col">Compared</th>'
        '<th scope="col">Reads the URL as</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def summary(row):
    answers = row["answers"]
    browser = answers["browser"]
    counts = {"differs": 0, "rejects": 0}
    for id, answer in answers.items():
        if id not in HERO_FIRST:
            st = status(answer, browser)
            if st in counts:
                counts[st] += 1
    parts = []
    if counts["differs"]:
        parts.append(f"{counts['differs']} {'parser differs' if counts['differs'] == 1 else 'parsers differ'} from the browser")
    if counts["rejects"]:
        parts.append(f"{counts['rejects']} {'rejects' if counts['rejects'] == 1 else 'reject'} it")
    if not parts:
        return '<p class="tally agree">Every parser here agrees. The trap is checking the text.</p>'
    return f'<p class="tally">{esc(", and ".join(parts))}.</p>'


def cards(gallery, recorded):
    rows = {(r["input"], r.get("base")): r for r in recorded["results"]}
    out = []
    for card in gallery["cards"]:
        row = rows[(card["input"], card.get("base"))]
        base = f'<p class="base">against <code>{shown(card["base"])}</code></p>' if card.get("base") else ""
        base_attr = f' data-base="{esc(card["base"])}"' if card.get("base") else ""
        out.append(
            f'<article class="card" id="trick-{card["id"]}" data-input="{esc(card["input"])}"{base_attr} data-title="{esc(card["title"])}">'
            f'<h3>{esc(card["title"])}</h3>'
            f'<p class="card-input"><code>{shown(card["input"])}</code></p>{base}'
            f'<p class="explain">{card["explain"]}</p>'
            f"{summary(row)}"
            f'<details><summary>Every parser\'s answer</summary>{card_table(row, recorded)}</details>'
            f'<button type="button" class="try" data-try="{card["id"]}">Try it above</button>'
            "</article>"
        )
    return "\n".join(out)


def href_proof(recorded):
    """How many inputs each parser reads as the browser does, as typed and as Hrefine's href."""
    ids = [p["id"] for p in recorded["parsers"] if p["id"] not in HERO_FIRST]
    label = names(recorded)
    total = len(recorded["results"])
    hrefs = {r["input"]: r for r in recorded["hrefs"]}
    lines = []
    for id in ids:
        raw = sum(status(r["answers"][id], r["answers"]["browser"]) == "same" for r in recorded["results"])
        fixed = 0
        refused = 0
        for r in recorded["results"]:
            h = r["answers"]["hrefine"]
            if not h["ok"]:
                continue
            got = hrefs[h["href"]]["answers"]
            st = status(got[id], got["browser"])
            fixed += st == "same"
            # Refusing a scheme it doesn't fetch, such as javascript:, isn't
            # reading another host.
            refused += st == "rejects"
        note = f", and refuses {refused}" if refused else ""
        lines.append(
            f'<tr><th scope="row">{esc(label[id])}</th><td>{raw} of {total}</td>'
            f"<td>{fixed} of {total}{note}</td></tr>"
        )
    return (
        '<div class="table-scroll" tabindex="0"><table class="proof-table">'
        '<thead><tr><th scope="col">Parser</th><th scope="col">Given the input</th>'
        "<th scope=\"col\">Given Hrefine's href</th></tr></thead>"
        f"<tbody>{''.join(lines)}</tbody></table></div>"
    )


def versions(recorded):
    items = [f"<li>{esc(p['name'])} (<code>{esc(p['calls'])}</code>): {esc(p['version'])}</li>" for p in recorded["parsers"]]
    items.insert(1, f"<li>Hrefine: {esc(recorded['hrefine'])}</li>")
    return "".join(items)


# The fix: each tour's check function, which CI runs in every language,
# with the allowed hosts before it.
CHECK_START = "The URL to fetch, or why not."


def fix_snippet(ext, source):
    lines = source.splitlines()
    at = next(i for i, line in enumerate(lines) if CHECK_START in line)
    # Python's docstring is inside the function; others' comments are before.
    start = at - 1 if ext == "py" else at
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    if ext == "py":
        while lines[end].strip():
            end += 1
    else:
        closer = "end" if ext == "lua" else "}"
        while not (lines[end].strip() == closer and len(lines[end]) - len(lines[end].lstrip()) == indent):
            end += 1
        end += 1
    body = [line[indent:] for line in lines[start:end]]
    allowed = [line.strip() for line in lines if re.search(r"allowed|ALLOWED", line) and '"api.example.com"' in line]
    if len(allowed) != 1:
        raise SystemExit(f"Can't find the allowed hosts in the {ext} tour.")
    return "\n".join([allowed[0], "", *body]) + "\n"


def copy(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)


def copy_module(source, dest):
    """A JS module without its source map comment, as the maps aren't copied."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8")
    dest.write_text(re.sub(r"\n//# sourceMappingURL=\S+\s*$", "\n", text), encoding="utf-8")


def sizes(name, files):
    data = b"".join(f.read_bytes() for f in files)
    return {"name": name, "raw": len(data), "gzip": len(gzip.compress(data, 9))}


def main():
    if not (JS / "hrefine" / "hrefine.internal.js").exists():
        raise SystemExit("Build the JS library first: temper build -b js")
    gallery = json.loads((SITE / "gallery.json").read_text(encoding="utf-8"))
    recorded = json.loads((SITE / "recorded.json").read_text(encoding="utf-8"))
    inputs = [(i["input"], i.get("base")) for i in gallery["hero"] + gallery["cards"]]
    if [(r["input"], r.get("base")) for r in recorded["results"]] != inputs:
        raise SystemExit("recorded.json is for other inputs; run: uv run site/record/record.py")

    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    # GitHub Pages serves files as they are, without Jekyll.
    (OUT / ".nojekyll").touch()
    for name in ["style.css", "app.js", "recorded.json"]:
        copy(SITE / name, OUT / name)

    lib = []
    for path in sorted((JS / "hrefine").glob("*.js")):
        copy_module(path, OUT / "lib" / "hrefine" / path.name)
        lib.append(OUT / "lib" / "hrefine" / path.name)
    for path in sorted((JS / "temper-core").glob("*.js")):
        copy_module(path, OUT / "lib" / "temper-core" / path.name)
        lib.append(OUT / "lib" / "temper-core" / path.name)
    measured = [sizes("Hrefine and Temper's JS runtime, as ES modules, unminified", lib)]
    (OUT / "sizes.json").write_text(json.dumps(measured, indent=2) + "\n")

    sources = {ext: (TOUR / path).read_text(encoding="utf-8") for ext, path in TOURS.items()}
    for ext, text in sources.items():
        copy(TOUR / TOURS[ext], OUT / "tour" / f"tour.{ext}")
    copy(TOUR / "expected.txt", OUT / "tour" / "expected.txt")
    fixes = "\n".join(
        f'<pre class="source fix-code" data-lang="{ext}" tabindex="0" hidden><code>{esc(fix_snippet(ext, text))}</code></pre>'
        for ext, text in sources.items()
    )

    page = (SITE / "index.html").read_text(encoding="utf-8")
    parts = {
        "HERO": hero(gallery, recorded),
        "CARDS": cards(gallery, recorded),
        "FIXES": fixes,
        "HREF_PROOF": href_proof(recorded),
        "VERSIONS": versions(recorded),
        "RECORDED_DATE": esc(recorded["date"]),
        "PLATFORM": esc(recorded["platform"]),
        "TRICK_COUNT": str(len(recorded["results"])),
    }
    for key, value in parts.items():
        page = page.replace(f"<!--{key}-->", value)
    left = re.findall(r"<!--[A-Z_]+-->", page)
    if left:
        raise SystemExit(f"Unfilled in index.html: {', '.join(left)}")
    # Each reference gets its file's hash, so browsers fetch changed files
    # instead of reusing cached ones.
    for ref in ["style.css", "app.js"]:
        digest = hashlib.sha256((OUT / ref).read_bytes()).hexdigest()[:10]
        page = page.replace(f'"{ref}"', f'"{ref}?v={digest}"')
    (OUT / "index.html").write_text(page, encoding="utf-8")
    for m in measured:
        print(f"{m['name']}: {m['raw']} bytes, {m['gzip']} gzipped")
    print(f"Built {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
