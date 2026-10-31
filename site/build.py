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

Renders the opening, the trick gallery, and the table of more
disagreements into the page from `site/gallery.json` and
`site/recorded.json` (other parsers' answers, which `site/record/record.py`
records), so they show before any script runs. A card of hosts shows each
as the tours print it with `domainToDisplay`, so every language agrees. Each of the table's rows
has its full answers in `tables.json`, which the tester fetches only when
one is tried. The
fix's code comes from each tour's "Using it safely" section, which CI runs
in every language, and the tours themselves go in `tour/`.

Lines in the tours ending in a comment like `# snippet: hero, parts` are
snippets for the page's dev mode: each snippet's lines, in order, for each
language, dedented, go into `snippets.json`, and the comments come off the
tours the page shows. Since CI runs every tour, the snippets are known to
work; every snippet must be in every language, and every spot in
`devmode.js` must have one. Each name on a spot's card, as that language
spells it, must be in its tour too (`spell-node.mjs`).

Runs the JavaScript tour in Node as the page's "Run in your browser" does
(`tour-node.mjs` and `tourrun.js`), against the built `lib/`, failing
unless it prints `demos/tour/expected.txt`.

Runs web-platform-tests' URL cases (`tests/wpt/urltestdata.json`, copied
into `wpt/` for the page's live scoreboard) in Node, through Node's `URL`
and Hrefine's built JS, with the page's own scoring module
(`scoreboard-node.mjs` and `scoreboard.js`). Node's score goes in the page
beside the visitor's, and the build fails unless Hrefine passes every case.
"""

import difflib
import gzip
import hashlib
import html
import ipaddress
import json
import re
import shutil
import subprocess
import textwrap
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "build"
JS = ROOT / "temper.out" / "js"
TOUR = ROOT / "demos" / "tour"
WPT = ROOT / "tests" / "wpt" / "urltestdata.json"

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

# A snippet line's marker: its comment and the snippets it's in.
MARKER = re.compile(r"\s+(?:#|//|--) snippet: ([\w, -]+)$")


def snippets(tours):
    """Each snippet's code by language, and each tour without markers."""
    found = {}
    stripped = {}
    for ext, text in tours.items():
        lines = []
        for line in text.splitlines():
            m = MARKER.search(line)
            if m:
                line = line[: m.start()]
                for name in m[1].split(","):
                    found.setdefault(name.strip(), {}).setdefault(ext, []).append(line)
            lines.append(line)
        stripped[ext] = "\n".join(lines) + "\n"
    for name, by_ext in found.items():
        missing = set(tours) - set(by_ext)
        if missing:
            raise SystemExit(f"Snippet {name!r} is missing from the {', '.join(sorted(missing))} tours.")
    spots = set(re.findall(r'^    id: "([\w-]+)",$', (SITE / "devmode.js").read_text(encoding="utf-8"), re.M))
    if not spots or spots - set(found):
        raise SystemExit(f"devmode.js has spots without snippets: {', '.join(sorted(spots - set(found))) or 'none found'}")
    return {
        name: {ext: textwrap.dedent("\n".join(code)) for ext, code in sorted(by_ext.items())} for name, by_ext in found.items()
    }, stripped


def check_tour_run(expected):
    """Fails unless the built JS tour, run as the page runs it, prints
    what every tour prints."""
    try:
        run = subprocess.run(
            ["node", str(SITE / "tour-node.mjs"), str(OUT)], capture_output=True, text=True, encoding="utf-8"
        )
    except FileNotFoundError:
        raise SystemExit("The build needs Node (24 or later), to run the JS tour.")
    if run.returncode:
        raise SystemExit(f"The JS tour doesn't run as the page runs it:\n{run.stderr}")
    if run.stdout != expected:
        diff = difflib.unified_diff(
            expected.splitlines(keepends=True), run.stdout.splitlines(keepends=True), "expected.txt", "in the page"
        )
        raise SystemExit(f"The JS tour, run as the page runs it, prints otherwise:\n{''.join(diff)}")


def check_card_names():
    """Fails unless every name on dev mode's cards, as each language spells
    it, is in that language's tour."""
    run = subprocess.run(
        ["node", str(SITE / "spell-node.mjs"), str(OUT)], capture_output=True, text=True, encoding="utf-8"
    )
    if run.returncode:
        raise SystemExit(run.stderr or run.stdout)


def link_modules(name):
    """Gives each `./x.js` that a built module imports its file's hash, as
    the page's references get theirs."""
    path = OUT / name
    text = path.read_text(encoding="utf-8")

    def hashed(m):
        digest = hashlib.sha256((OUT / m[2]).read_bytes()).hexdigest()[:10]
        return f'{m[1]}"./{m[2]}?v={digest}";'

    path.write_text(re.sub(r'^(import .* from )"\./([\w-]+\.js)";$', hashed, text, flags=re.M), encoding="utf-8")


# Parsers in the order the opening shows them, after the browser and
# Hrefine: those that differ from the browser first.
HERO_FIRST = ["browser", "hrefine"]


def esc(text):
    return html.escape(text, quote=True)


def shown(text):
    """Text as HTML, with tabs, newlines, and other controls shown as symbols."""
    out = esc(text)
    out = out.replace("\t", '<span class="ctl" title="tab">\\t</span>')
    out = out.replace("\n", '<span class="ctl" title="newline">\\n</span>')
    return re.sub(
        r"[\x00-\x08\x0b-\x1f\x7f\u00ad\u200b]",
        lambda m: f'<span class="ctl" title="invisible">\\u{ord(m[0]):04x}</span>',
        out,
    )


def host_key(host):
    """A host as compared: case and IPv6 brackets aside, and an IPv6 address
    however it's written, so only another host counts as different."""
    if host is None:
        return None
    host = host.lower()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return str(ipaddress.IPv6Address(host))
    except ValueError:
        return host


def status(answer, browser, compare="host"):
    """How an answer compares with the browser's, by host or by path: same,
    differs, or rejects."""
    if not answer["ok"]:
        return "same" if not browser["ok"] else "rejects"
    if not browser["ok"]:
        return "differs"
    if compare == "path":
        return "same" if answer.get("path") == browser.get("path") else "differs"
    return "same" if host_key(answer.get("host")) == host_key(browser.get("host")) else "differs"


STATUS_TEXT = {"same": "same as the browser", "differs": "differs from the browser", "rejects": "rejects it"}
STATUS_ICON = {"same": "✓", "differs": "✗", "rejects": "–"}


def host_html(answer, compare="host"):
    if not answer["ok"]:
        return '<span class="none">error</span>'
    if compare == "path":
        path = answer.get("path")
        return '<span class="none">no path</span>' if path is None else f"<code>{shown(path) or '&nbsp;'}</code>"
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


def card_table(row, recorded, compare="host"):
    answers = row["answers"]
    browser = answers["browser"]
    label = names(recorded)
    ids = ["browser", "hrefine"] + [p["id"] for p in recorded["parsers"] if p["id"] not in HERO_FIRST]
    rows = []
    for id in ids:
        answer = answers[id]
        st = "browser" if id == "browser" else status(answer, browser, compare)
        verdict = "" if id == "browser" else f'<span class="icon" aria-hidden="true">{STATUS_ICON[st]}</span> {STATUS_TEXT[st]}'
        reads = (
            f"<code>{shown(answer['href'])}</code>"
            if answer["ok"]
            else f'<span class="error">{esc(answer["error"])}</span>'
        )
        rows.append(
            f'<tr class="{st}" data-parser="{id}"><th scope="row">{esc(label[id])}</th>'
            f'<td class="host" data-label="{compare.capitalize()}">{host_html(answer, compare)}</td>'
            f'<td class="verdict">{verdict}</td><td class="reads" data-label="Reads it as">{reads}</td></tr>'
        )
    return (
        '<div class="table-scroll" tabindex="0"><table class="compare">'
        f'<thead><tr><th scope="col">Parser</th><th scope="col">{compare.capitalize()}</th><th scope="col">Compared</th>'
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


def recorded_items(gallery):
    """The inputs with other parsers' answers recorded, in order: all but
    the cards that show hosts, which no other parser displays."""
    cards = [c for c in gallery["cards"] if "hosts" not in c]
    return gallery["hero"] + cards + [i for group in gallery["corpus"] for i in group["items"]]


def shown_hosts(card, expected):
    """A card of hosts, each as Hrefine displays it: the line every tour
    prints for it, `host: shown`, so all seven languages agree. The first
    host heads the card; all of them, with why, go in its details."""
    rows = []
    shown_first = None
    for item in card["hosts"]:
        host = item["host"]
        found = [line[len(host) + 2 :] for line in expected.splitlines() if line.startswith(f"{host}: ")]
        if len(found) != 1:
            raise SystemExit(f"The tours don't print {host!r} with domainToDisplay, for the {card['id']!r} card.")
        shown_as = found[0]
        shown_first = shown_first or shown_as
        kept = shown_as.startswith("xn--") or ".xn--" in shown_as
        tag = "kept as <code>xn--</code>" if kept else "shown in Unicode"
        rows.append(
            f'<li class="{"kept" if kept else "unicode"}" data-host="{esc(host)}">'
            f'<span class="pair"><code class="typed">{esc(host)}</code><span class="to" aria-hidden="true">→</span>'
            f'<code class="shown-as">{esc(shown_as)}</code></span>'
            f'<span class="tag">{tag}</span><span class="note">{item["note"]}</span></li>'
        )
    first = card["hosts"][0]["host"]
    return (
        f'<article class="card hosts-card" id="trick-{card["id"]}" data-input="{esc(card["try"])}" data-title="{esc(card["title"])}">'
        f'<h3>{esc(card["title"])}</h3>'
        f'<p class="card-input" data-host="{esc(first)}"><code>{esc(first)}</code>'
        f' <span class="to">shows as</span> <code class="shown-as">{esc(shown_first)}</code></p>'
        f'<p class="explain">{card["explain"]}</p>'
        f'<details><summary>Other hosts, and why</summary><ul class="shown-hosts">{"".join(rows)}</ul>'
        f'<p class="why">{card["why"]}</p></details>'
        f'<button type="button" class="try" data-try="{card["id"]}">Try it above</button>'
        "</article>"
    )


def cards(gallery, recorded, expected):
    rows = {(r["input"], r.get("base")): r for r in recorded["results"]}
    out = []
    for card in gallery["cards"]:
        if "hosts" in card:
            out.append(shown_hosts(card, expected))
            continue
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


def href_proof(recorded, compares):
    """How many inputs each parser reads as the browser does: as typed, and,
    for those Hrefine accepts, as Hrefine's href and as its strict RFC 3986
    form, by host or by path."""
    ids = [p["id"] for p in recorded["parsers"] if p["id"] not in HERO_FIRST]
    label = names(recorded)
    total = len(recorded["results"])
    given = {"href": {r["input"]: r for r in recorded["hrefs"]}, "strictHref": {r["input"]: r for r in recorded["stricts"]}}
    accepted = [r for r in recorded["results"] if r["answers"]["hrefine"]["ok"]]
    check_strict_means_the_same(accepted, given)
    lines = []
    for id in ids:
        raw = sum(
            status(r["answers"][id], r["answers"]["browser"], compares[row_key(r)]) == "same" for r in recorded["results"]
        )
        cells = []
        for form in ["href", "strictHref"]:
            fixed = 0
            refused = 0
            for r in accepted:
                got = given[form][r["answers"]["hrefine"][form]]["answers"]
                st = status(got[id], got["browser"], compares[row_key(r)])
                fixed += st == "same"
                # Refusing a scheme it doesn't fetch, such as javascript:,
                # isn't reading another host.
                refused += st == "rejects"
            note = f', <span class="n">{refused} refused</span>' if refused else ""
            cells.append(f'<td><span class="n">{fixed} of {len(accepted)}</span>{note}</td>')
        lines.append(f'<tr><th scope="row">{esc(label[id])}</th><td><span class="n">{raw} of {total}</span></td>{"".join(cells)}</tr>')
    return (
        '<div class="table-scroll" tabindex="0"><table class="proof-table">'
        '<thead><tr><th scope="col">Parser</th><th scope="col">Given the input</th>'
        "<th scope=\"col\">Given Hrefine's <code>href</code></th>"
        "<th scope=\"col\">Given its <code>strictHref</code></th></tr></thead>"
        f"<tbody>{''.join(lines)}</tbody></table></div>"
    )


def check_strict_means_the_same(accepted, given):
    """Fails the build unless browsers read each strict form as they read
    its href: the same host, and a path with the same bytes once decoded."""
    for r in accepted:
        hrefine = r["answers"]["hrefine"]
        a = given["href"][hrefine["href"]]["answers"]["browser"]
        b = given["strictHref"][hrefine["strictHref"]]["answers"]["browser"]
        same = (
            a["ok"]
            and b["ok"]
            and host_key(a.get("host")) == host_key(b.get("host"))
            and urllib.parse.unquote_to_bytes(a["path"]) == urllib.parse.unquote_to_bytes(b["path"])
        )
        if not same:
            raise SystemExit(f"Browsers read the strict form of {r['input']!r} otherwise: {a} and {b}")


def row_key(row):
    return (row["input"], row.get("base"))


STATUS_SHORT = {"same": "✓", "differs": "✗", "rejects": "–", "browser": ""}


def corpus(gallery, recorded):
    """The table of more disagreements: each input, what browsers read, and
    whether each other parser agrees, by group. Each row's full answers go
    in `tables.json`, by row id, for the tester."""
    rows = {row_key(r): r for r in recorded["results"]}
    label = names(recorded)
    ids = [p["id"] for p in recorded["parsers"] if p["id"] not in HERO_FIRST]
    head = "".join(f'<th scope="col" class="who-col">{esc(label[id])}</th>' for id in ids)
    body = []
    tables = {}
    n = 0
    for group in gallery["corpus"]:
        body.append(
            f'<tbody id="more-{group["id"]}"><tr class="group"><th scope="rowgroup" colspan="{len(ids) + 2}">'
            f'{group["title"]}</th></tr>'
        )
        for item in group["items"]:
            n += 1
            row = rows[row_key(item)]
            compare = item.get("compare", "host")
            answers = row["answers"]
            browser = answers["browser"]
            cells = []
            for id in ids:
                st = status(answers[id], browser, compare)
                cells.append(
                    f'<td class="mark {st}" data-who="{esc(label[id])}" title="{esc(label[id])}: {STATUS_TEXT[st]}">'
                    f"{STATUS_SHORT[st]}</td>"
                )
            base = f'<span class="base">against <code>{shown(item["base"])}</code></span>' if item.get("base") else ""
            base_attr = f' data-base="{esc(item["base"])}"' if item.get("base") else ""
            reads = f'{"path" if compare == "path" else "host"} {host_html(browser, compare)}' if browser["ok"] else host_html(browser)
            row_id = f"m{n}"
            tables[row_id] = card_table(row, recorded, compare)
            body.append(
                f'<tr class="more-row" data-row="{row_id}" data-input="{esc(item["input"])}"{base_attr}'
                f' data-title="{esc(item["input"])}">'
                f'<th scope="row"><button type="button" class="more-try" title="Try it in the tester">'
                f"<code>{shown(item['input'])}</code></button>{base}"
                f'<span class="more-note">{item["note"]}</span></th>'
                f'<td class="browser-reads" data-label="Browsers read">{reads}</td>{"".join(cells)}</tr>'
            )
        body.append("</tbody>")
    table = (
        '<div class="table-scroll" tabindex="0"><table class="more-table">'
        f'<thead><tr><th scope="col">Input</th><th scope="col">Browsers read</th>{head}</tr></thead>'
        f"{''.join(body)}</table></div>"
    )
    return table, tables, n


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


def node_scores():
    """Node's and Hrefine's WPT scores, run in Node on the built site."""
    try:
        run = subprocess.run(
            ["node", str(SITE / "scoreboard-node.mjs"), str(OUT)], capture_output=True, text=True, encoding="utf-8"
        )
    except FileNotFoundError:
        raise SystemExit("The build needs Node (24 or later), to score the WPT cases.")
    if run.returncode:
        raise SystemExit(f"scoreboard-node.mjs failed:\n{run.stderr}")
    scores = json.loads(run.stdout)
    hrefine = scores["hrefine"]
    if hrefine["passed"] != hrefine["total"]:
        shown = "\n".join(
            f"  {m['input']!r} (base {m['base']!r}): expected {m['expected']!r}, got {m['got']!r} {m['parts']}"
            for m in hrefine["misses"][:10]
        )
        raise SystemExit(f"Hrefine misses {len(hrefine['misses'])} of {hrefine['total']} WPT cases in Node:\n{shown}")
    return scores


def node_line(scores):
    """Node's score, as the page shows it before the live run."""
    ada = f" (Ada {esc(scores['ada'])})" if scores["ada"] else ""
    built_in = scores["builtIn"]
    return (
        f'<span class="who">Node {esc(scores["node"])}{ada}, at build time</span>'
        f'<span class="tally-num">{built_in["passed"]} of {built_in["total"]}</span>'
    )


def main():
    if not (JS / "hrefine" / "hrefine.internal.js").exists():
        raise SystemExit("Build the JS library first: temper build -b js")
    gallery = json.loads((SITE / "gallery.json").read_text(encoding="utf-8"))
    recorded = json.loads((SITE / "recorded.json").read_text(encoding="utf-8"))
    expected = (TOUR / "expected.txt").read_text(encoding="utf-8")
    items = recorded_items(gallery)
    if [row_key(r) for r in recorded["results"]] != [row_key(i) for i in items]:
        raise SystemExit("recorded.json is for other inputs; run: uv run site/record/record.py")

    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    # GitHub Pages serves files as they are, without Jekyll.
    (OUT / ".nojekyll").touch()
    for name in ["style.css", "app.js", "devmode.js", "tourrun.js", "recorded.json"]:
        copy(SITE / name, OUT / name)
    link_modules("app.js")

    lib = []
    for path in sorted((JS / "hrefine").glob("*.js")):
        copy_module(path, OUT / "lib" / "hrefine" / path.name)
        lib.append(OUT / "lib" / "hrefine" / path.name)
    for path in sorted((JS / "temper-core").glob("*.js")):
        copy_module(path, OUT / "lib" / "temper-core" / path.name)
        lib.append(OUT / "lib" / "temper-core" / path.name)
    measured = [sizes("Hrefine and Temper's JS runtime, as ES modules, unminified", lib)]
    (OUT / "sizes.json").write_text(json.dumps(measured, indent=2) + "\n")
    copy(WPT, OUT / "wpt" / "urltestdata.json")
    copy(SITE / "scoreboard.js", OUT / "scoreboard.js")
    scores = node_scores()

    more, tables, more_count = corpus(gallery, recorded)
    (OUT / "tables.json").write_text(json.dumps(tables, ensure_ascii=False) + "\n", encoding="utf-8")
    compares = {row_key(i): i.get("compare", "host") for i in items}

    found, sources = snippets({ext: (TOUR / path).read_text(encoding="utf-8") for ext, path in TOURS.items()})
    (OUT / "snippets.json").write_text(json.dumps(found, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "tour").mkdir(parents=True, exist_ok=True)
    for ext, text in sources.items():
        (OUT / "tour" / f"tour.{ext}").write_text(text, encoding="utf-8")
    copy(TOUR / "expected.txt", OUT / "tour" / "expected.txt")
    check_tour_run(expected)
    check_card_names()
    fixes = "\n".join(
        f'<pre class="source fix-code" data-lang="{ext}" tabindex="0" hidden><code>{esc(fix_snippet(ext, text))}</code></pre>'
        for ext, text in sources.items()
    )

    page = (SITE / "index.html").read_text(encoding="utf-8")
    parts = {
        "HERO": hero(gallery, recorded),
        "CARDS": cards(gallery, recorded, expected),
        "FIXES": fixes,
        "MORE": more,
        "MORE_COUNT": str(more_count),
        "HREF_PROOF": href_proof(recorded, compares),
        "VERSIONS": versions(recorded),
        "RECORDED_DATE": esc(recorded["date"]),
        "PLATFORM": esc(recorded["platform"]),
        "TRICK_COUNT": str(len(recorded["results"])),
        "WPT_COUNT": f'{scores["hrefine"]["total"]:,}',
        "WPT_NODE": node_line(scores),
        # Safe inside a script element, with no "<" in it.
        "WPT_NODE_JSON": json.dumps(scores, ensure_ascii=True).replace("<", "\\u003c"),
    }
    for key, value in parts.items():
        page = page.replace(f"<!--{key}-->", value)
    left = re.findall(r"<!--[A-Z_]+-->", page)
    if left:
        raise SystemExit(f"Unfilled in index.html: {', '.join(left)}")
    # Each reference gets its file's hash, so browsers fetch changed files
    # instead of reusing cached ones.
    for ref in ["style.css", "app.js", "scoreboard.js", "tables.json", "wpt/urltestdata.json"]:
        digest = hashlib.sha256((OUT / ref).read_bytes()).hexdigest()[:10]
        page = page.replace(f'"{ref}"', f'"{ref}?v={digest}"')
    (OUT / "index.html").write_text(page, encoding="utf-8")
    for m in measured:
        print(f"{m['name']}: {m['raw']} bytes, {m['gzip']} gzipped")
    for name, s in [(f"Node {scores['node']}", scores["builtIn"]), ("Hrefine, in Node", scores["hrefine"])]:
        print(f"WPT URL cases: {name}: {s['passed']} of {s['total']}")
    print(f"Built {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
