// Hrefine's site: the live URL tester, the gallery's live Hrefine answers,
// the table of more disagreements, the language tabs, and the tour. Hrefine comes from Temper's JS output,
// as plain ES modules named by the page's import map.

import * as hrefine from "hrefine";
import * as temperCore from "@temperlang/core";
import { initDevMode } from "./devmode.js";
import { runTour } from "./tourrun.js";

const { checkUrl, UrlDisplay } = hrefine;

// How browsers' address bars would show a URL: hosts in Unicode where
// they'd show it, escapes of non-ASCII text decoded, and no credentials or
// lone "/" path. For people only, never for decisions.
const display = UrlDisplay.addressBar.withRootSlash(false);

/** @param {string} id */
const $ = (id) => /** @type {HTMLElement} */ (document.getElementById(id));

/** @param {string} s */
function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] ?? c);
}

// Tabs and newlines, shown as symbols, and typed as them in the fields.
const TAB = "␉";
const NEWLINE = "␊";

/** @param {string} s */
function shown(s) {
  return escapeHtml(s)
    .replaceAll("\t", '<span class="ctl" title="tab">\\t</span>')
    .replaceAll("\n", '<span class="ctl" title="newline">\\n</span>')
    .replace(/[\u0000-\u0008\u000B-\u001F\u007F\u00AD\u200B]/g, (c) =>
      `<span class="ctl" title="invisible">\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}</span>`);
}

/** A field's text with its stand-ins turned back into tabs and newlines. @param {string} s */
const fromField = (s) => s.replaceAll(TAB, "\t").replaceAll(NEWLINE, "\n");
/** @param {string} s */
const toField = (s) => s.replaceAll("\t", TAB).replaceAll("\n", NEWLINE);

/**
 * Hrefine's reading of a URL: the URL or null, and the validation errors.
 *
 * @param {string} input
 * @param {string | null} base
 */
function readHrefine(input, base) {
  try {
    const check = checkUrl(input, base);
    return { url: check.url, errors: check.errors, baseFailed: false };
  } catch {
    // checkUrl fails only for a base that isn't a URL.
    return { url: null, errors: [], baseFailed: true };
  }
}

/**
 * The browser's own reading, with its host, or null where it has none.
 *
 * @param {string} input
 * @param {string | null} base
 */
function readBrowser(input, base) {
  try {
    const url = new URL(input, base ?? undefined);
    const host = url.host === "" && !url.href.startsWith(`${url.protocol}//`) ? null : url.hostname;
    return { url, host };
  } catch {
    return { url: null, host: null };
  }
}

/** @param {any} url Hrefine's URL, which has a host where hostKind isn't null. */
const hrefineHost = (url) => (url.hostKind === null ? null : url.hostname);

/** @param {string | null} host */
function hostHtml(host) {
  if (host === null) return '<span class="none">no host</span>';
  if (host === "") return '<span class="none">empty host</span>';
  return `<code>${shown(host)}</code>`;
}

// The opening and the gallery: their Hrefine answers, live, in place of
// the recorded ones, and the browser's in the opening.

for (const row of document.querySelectorAll("[data-parser=hrefine]")) {
  const holder = /** @type {HTMLElement} */ (row.closest("[data-input]"));
  const { url } = readHrefine(holder.dataset.input ?? "", holder.dataset.base ?? null);
  const cell = row.querySelector(".host");
  if (cell && url) {
    const live = hostHtml(hrefineHost(url));
    if (cell.innerHTML !== live) {
      // The library changed since the answers were recorded.
      cell.innerHTML = live;
      cell.setAttribute("title", "Live; differs from the recorded answer.");
    }
  }
}

{
  const chip = document.querySelector('.answer[data-parser="browser"]');
  const input = /** @type {HTMLElement} */ (document.querySelector(".hero-demo")).dataset.input ?? "";
  const host = chip?.querySelector(".host");
  if (host) {
    const live = readBrowser(fromField(input), null);
    const html = live.url ? hostHtml(live.host) : '<span class="none">error</span>';
    if (host.innerHTML !== html) {
      host.innerHTML = html;
      const verdict = chip?.querySelector(".verdict-text");
      if (verdict) verdict.textContent = "this browser's answer, which differs from the standard's";
    }
  }
}

// The tester.

const urlInput = /** @type {HTMLInputElement} */ ($("url-input"));
const baseInput = /** @type {HTMLInputElement} */ ($("base-input"));
const cards = [.../** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".card"))];
// The opening's URL, the gallery's, and the table's, which have recorded
// answers.
const recordedInputs = [.../** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll("[data-title]"))];

const PARTS = ["href", "origin", "protocol", "username", "password", "host", "hostname", "port", "pathname", "search", "hash"];

function update() {
  const input = fromField(urlInput.value);
  const baseText = fromField(baseInput.value);
  const base = baseText.trim() === "" ? null : baseText;
  const h = readHrefine(input, base);
  const b = readBrowser(input, base);
  const hHost = h.url ? hrefineHost(h.url) : null;

  // The two answers.
  let what;
  if (h.baseFailed) {
    what = "The base isn't a URL.";
  } else if (h.url) {
    const kind = h.url.hostKind === null ? "" : ` <span class="small-note">(${h.url.hostKind} host)</span>`;
    what = `<span class="host-line">${hostHtml(hHost)}${kind}</span><code>${shown(h.url.href)}</code>` +
      `<span class="display-line">Shown to people as <code>${shown(display.format(h.url))}</code></span>` +
      (h.url.username !== "" || h.url.password !== ""
        ? `<span class="display-line">Logged, by <code>toString()</code>, as <code>${shown(h.url.toString())}</code></span>` +
          '<span class="display-line"><code>href</code> leaves out the credentials, by design; <code>hrefWithCredentials</code> keeps them, only to send them.</span>'
        : "");
  } else {
    const last = h.errors.at(-1);
    what = `<span class="host-line">Not a URL</span>${last ? `<code>${escapeHtml(last.name)}</code>` : ""}`;
  }
  $("hrefine-what").innerHTML = what;

  const browserBox = $("browser-verdict");
  const same = b.url
    ? h.url !== null && b.url.href === h.url.hrefWithCredentials
    : h.url === null;
  if (b.url) {
    $("browser-what").innerHTML = `<span class="host-line">${hostHtml(b.host)}</span><code>${shown(b.url.href)}</code>`;
  } else {
    $("browser-what").innerHTML = `<span class="host-line">Not a URL</span>`;
  }
  $("browser-what").insertAdjacentHTML(
    "beforeend",
    `<span class="agree-note">${same ? "✓ The same as Hrefine." : "✗ Not the same as Hrefine. Browsers can lag the standard; please tell us."}</span>`,
  );
  browserBox.className = `verdict-box ${same ? "same" : "differs"}`;

  // Parts, side by side.
  const cell = (/** @type {string | null} */ v) => (v === null ? '<span class="none">—</span>' : v === "" ? '<span class="none">""</span>' : `<code>${shown(v)}</code>`);
  // Hrefine's href leaves out credentials, by design, so its
  // hrefWithCredentials is what's compared with the browser's href.
  const full = h.url ? h.url.hrefWithCredentials : null;
  const rows = PARTS.map((part) => {
    const hv = h.url ? /** @type {any} */ (h.url)[part] : null;
    const bv = b.url ? /** @type {any} */ (b.url)[part] : null;
    const diff = h.url !== null && b.url !== null && (part === "href" ? full : hv) !== bv;
    const note = part === "href" && full !== hv ? ' <span class="small-note">(no credentials, by design)</span>' : "";
    return `<tr class="${diff ? "diff" : ""}"><th scope="row">${part}</th><td>${cell(hv)}${note}</td><td>${cell(bv)}${diff ? ' <span aria-label="differs">≠</span>' : ""}</td></tr>`;
  });
  if (h.url && full !== h.url.href) {
    rows.splice(1, 0, `<tr class="typed"><th scope="row">hrefWithCredentials</th><td>${cell(full)}</td><td><span class="none">its href, above</span></td></tr>`);
  }
  if (h.url) {
    const typed = [
      ["scheme", h.url.scheme],
      ["portNumber", h.url.portNumber === null ? "null" : String(h.url.portNumber)],
      ["hostKind", h.url.hostKind === null ? "null" : `HostKind.${h.url.hostKind}`],
    ];
    for (const [name, value] of typed) {
      rows.push(`<tr class="typed"><th scope="row">${name}</th><td><code>${escapeHtml(value)}</code></td><td><span class="none">Hrefine only</span></td></tr>`);
    }
  }
  /** @type {HTMLElement} */ ($("parts").querySelector("tbody")).innerHTML = rows.join("");

  // Validation errors, marked in the input: each covers `length` code
  // points from `position` (a whole host, say), or none at the end.
  const points = [...input];
  const marked = new Set();
  for (const e of h.errors) {
    for (let i = e.position; i < e.position + Math.max(e.length, 1); i++) marked.add(i);
  }
  $("marked").innerHTML = h.errors.length
    ? points.map((c, i) => (marked.has(i) ? `<mark>${shown(c)}</mark>` : shown(c))).join("") +
      (marked.has(points.length) ? '<mark title="end"> </mark>' : "")
    : "";
  /** @param {{ position: number, length: number }} e */
  const where = (e) =>
    e.length > 1
      ? `${e.position} to ${e.position + e.length - 1}, <code>${shown(points.slice(e.position, e.position + e.length).join(""))}</code>`
      : `${e.position}`;
  $("errors").innerHTML = h.errors.length
    ? h.errors.map((e) => `<li><code>${escapeHtml(e.name)}</code> at ${where(e)}</li>`).join("")
    : `<li class="none">${h.baseFailed ? "The base isn't a URL." : "None: a clean URL."}</li>`;

  // Other parsers, where this input is one of the recorded ones. The
  // table's rows have their answers in tables.json, fetched when needed.
  const known = recordedInputs.find((c) => c.dataset.input === input && (c.dataset.base ?? null) === base);
  /** @type {Element | null | undefined} */
  let table = known?.querySelector(".table-scroll");
  const row = known?.dataset.row;
  if (row) {
    if (moreTables) {
      const holder = document.createElement("template");
      holder.innerHTML = moreTables[row] ?? "";
      table = holder.content.firstElementChild;
    } else {
      loadMoreTables();
    }
  }
  $("recorded-table").replaceChildren(...(table ? [table.cloneNode(true)] : []));
  const which = known?.dataset.title === "opening"
    ? "the opening's URL"
    : row
      ? "one of the more disagreements below"
      : `the gallery's “${known?.dataset.title}” URL`;
  $("recorded-note").textContent = table
    ? `This is ${which}, so here are other parsers' answers, recorded ahead of time. The browser row is Node's URL, standing in for browsers.`
    : "Other languages' parsers can't run in your browser. For the gallery's URLs and the more disagreements below, this page shows their answers, recorded ahead of time; pick one. For anything else, only Hrefine and your browser run live.";
}

/** @type {Record<string, string> | null} */
let moreTables = null;
/** @type {Promise<void> | null} */
let moreLoading = null;

function loadMoreTables() {
  moreLoading ??= fetch($("more").dataset.tables ?? "")
    .then((response) => response.json())
    .then((tables) => {
      moreTables = tables;
      update();
    })
    .catch(() => {});
}

/**
 * @param {string} input
 * @param {string | null} base
 */
function load(input, base) {
  urlInput.value = toField(input);
  baseInput.value = toField(base ?? "");
  update();
}

for (const card of cards) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = toField(card.dataset.input ?? "");
  button.title = card.querySelector("h3")?.textContent ?? "";
  button.addEventListener("click", () => load(card.dataset.input ?? "", card.dataset.base ?? null));
  $("examples").append(button);
  card.querySelector(".try")?.addEventListener("click", () => {
    load(card.dataset.input ?? "", card.dataset.base ?? null);
    $("try").scrollIntoView({ behavior: "smooth" });
    urlInput.focus({ preventScroll: true });
  });
  // Open the card ourselves (mouse or keyboard), so it can be kept in place
  // before the browser paints it moved.
  const details = card.querySelector("details");
  card.querySelector("summary")?.addEventListener("click", (event) => {
    if (!details || details.open) return;
    event.preventDefault();
    const before = card.getBoundingClientRect();
    details.open = true;
    revealCard(card, before);
  });
}

/**
 * Brings a card just opened into view. First it's held where it was on
 * screen, though an open card spans its grid row and so may have moved.
 * Then, if it was only partly visible before or doesn't fit now, it
 * scrolls from there until its top is near the window's top.
 * @param {HTMLElement} card
 * @param {DOMRect} before where the card was before opening
 */
function revealCard(card, before) {
  const margin = 16;
  window.scrollBy({ top: card.getBoundingClientRect().top - before.top, behavior: "instant" });
  const now = card.getBoundingClientRect();
  const wasVisible = before.top >= 0 && before.bottom <= window.innerHeight;
  if (wasVisible && now.bottom <= window.innerHeight) return;
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  window.scrollBy({ top: now.top - margin, behavior: still ? "instant" : "smooth" });
}

for (const row of /** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".more-row"))) {
  row.querySelector(".more-try")?.addEventListener("click", () => {
    load(row.dataset.input ?? "", row.dataset.base ?? null);
    $("try").scrollIntoView({ behavior: "smooth" });
    urlInput.focus({ preventScroll: true });
  });
}

for (const button of /** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll("[data-insert]"))) {
  // The last field focused gets the character.
  button.addEventListener("click", () => {
    const field = lastField;
    const text = toField(button.dataset.insert ?? "");
    const start = field.selectionStart ?? field.value.length;
    const end = field.selectionEnd ?? start;
    field.setRangeText(text, start, end, "end");
    field.focus();
    update();
  });
}
let lastField = urlInput;
for (const field of [urlInput, baseInput]) {
  field.addEventListener("input", update);
  field.addEventListener("focus", () => (lastField = field));
}
update();

// Code tabs: the fix and the tour, in each language, with a small
// highlighter, as on Ordable's site. Both tab rows follow one choice.

/** Name, tour file extension, run command, line comment. */
const LANGUAGES = [
  ["C++", "cpp", "cmake -B build && cmake --build build && ./build/tour", "//"],
  ["C#", "cs", "dotnet run", "//"],
  ["Java", "java", "./gradlew run", "//"],
  ["JavaScript", "js", "npm ci && npm start", "//"],
  ["Lua", "lua", "lua -l paths tour.lua", "--"],
  ["Python", "py", "uv run tour.py", "#"],
  ["Rust", "rs", "cargo run", "//"],
];
const DEFAULT_LANGUAGE = "py";

const KEYWORDS = new Set(
  ("and as async auto await bool break case catch class const continue def do double else elif end except export " +
    "false fn for foreach from function if import in int let local match mut new None nil not null " +
    "of or private public record return self static string struct template then this throw true True False try " +
    "type typename typeof use using var void while is Some")
    .split(" "),
);

/**
 * Source as HTML, with comments, strings, numbers, keywords, and type-like
 * names in spans.
 *
 * @param {string} source
 * @param {string} comment
 */
function highlight(source, comment) {
  const commentPattern = comment === "#" ? "#[^\\n]*" : comment === "--" ? "--[^\\n]*" : "//[^\\n]*|/\\*[\\s\\S]*?\\*/";
  const token = new RegExp(
    `(${commentPattern})|("""[\\s\\S]*?"""|'''[\\s\\S]*?'''|"(?:[^"\\\\\\n]|\\\\.)*"|'(?:[^'\\\\\\n]|\\\\.)*'|\`[^\`]*\`)|` +
      `\\b(0x[0-9a-fA-F]+|\\d+(?:\\.\\d+)?)\\b|([A-Za-z_]\\w*)`,
    "g",
  );
  let out = "";
  let last = 0;
  for (const m of source.matchAll(token)) {
    out += escapeHtml(source.slice(last, m.index));
    const [text, isComment, isString, isNumber, word] = m;
    const cls = isComment
      ? "comment"
      : isString
        ? "string"
        : isNumber
          ? "number"
          : KEYWORDS.has(word)
            ? "keyword"
            : /^[A-Z][a-z]/.test(word)
              ? "type"
              : null;
    out += cls ? `<span class="tok-${cls}">${escapeHtml(text)}</span>` : escapeHtml(text);
    last = (m.index ?? 0) + text.length;
  }
  return out + escapeHtml(source.slice(last));
}

// The fix's code is in the page already; highlight it once.
for (const pre of /** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".fix-code"))) {
  const lang = LANGUAGES.find(([, file]) => file === pre.dataset.lang);
  const code = /** @type {HTMLElement} */ (pre.querySelector("code"));
  code.innerHTML = highlight(code.textContent ?? "", lang?.[3] ?? "//");
}

/** @type {Map<string, string>} */
const sources = new Map();
let selected = DEFAULT_LANGUAGE;
const tabRows = [.../** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll("[data-tabs]"))];
// Dev mode follows the chosen language; set up below.
/** @type {{ setLanguage: (file: string) => void } | null} */
let devMode = null;

/** @param {string} file */
async function selectLanguage(file) {
  selected = file;
  devMode?.setLanguage(file);
  const [name, , run, comment] = /** @type {string[]} */ (LANGUAGES.find(([, f]) => f === file));
  for (const row of tabRows) {
    for (const button of /** @type {NodeListOf<HTMLElement>} */ (row.querySelectorAll("button"))) {
      const on = button.dataset.file === file;
      button.setAttribute("aria-selected", String(on));
      button.tabIndex = on ? 0 : -1;
    }
  }
  for (const pre of /** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".fix-code"))) {
    pre.hidden = pre.dataset.lang !== file;
  }
  for (const span of document.querySelectorAll(".lang-name")) span.textContent = name;
  $("run-command").textContent = run;
  /** @type {HTMLButtonElement} */ ($("tour-run")).disabled = file !== "js";
  $("tour-output").hidden = true;
  $("tour-run-note").textContent =
    file === "js"
      ? "Runs the JavaScript tour in this page."
      : "Only JavaScript runs in this page. Every language runs in CI; run this one locally with the command above.";
  if (!sources.has(file)) {
    const response = await fetch(`tour/tour.${file}`);
    sources.set(file, response.ok ? await response.text() : "// Couldn't load this tour.");
  }
  if (selected === file) $("tour-source").innerHTML = highlight(sources.get(file) ?? "", comment);
}

for (const row of tabRows) {
  for (const [i, [name, file]] of LANGUAGES.entries()) {
    const button = document.createElement("button");
    button.type = "button";
    button.setAttribute("role", "tab");
    button.dataset.file = file;
    button.textContent = name;
    button.addEventListener("click", () => selectLanguage(file));
    button.addEventListener("keydown", (event) => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
      if (step) {
        const next = (i + step + LANGUAGES.length) % LANGUAGES.length;
        selectLanguage(LANGUAGES[next][1]);
        /** @type {HTMLElement} */ (row.children[next]).focus();
      }
    });
    row.append(button);
  }
}
selectLanguage(DEFAULT_LANGUAGE);

// Dev mode shows the code behind each part of the page, in the code tabs'
// language, and can open the full tour.
devMode = initDevMode({
  toggle: /** @type {HTMLButtonElement} */ ($("dev-toggle")),
  languages: LANGUAGES.map(([name, file, , comment]) => ({ name, file, comment })),
  language: DEFAULT_LANGUAGE,
  highlight,
  showTour: (file) => {
    selectLanguage(file);
    $("tour").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  },
});

// The JavaScript tour runs in the page (tourrun.js, which the build also
// runs in Node), with what it imports from this page's copies of Hrefine
// and Temper's runtime, and its output is compared with the text every
// language's tour prints.

$("tour-run").addEventListener("click", async () => {
  const output = $("tour-output");
  const note = $("tour-run-note");
  output.hidden = false;
  output.textContent = "Running…";
  try {
    const out = await runTour(sources.get("js") ?? "", { hrefine, "@temperlang/core": temperCore });
    output.textContent = out;
    const expected = await (await fetch("tour/expected.txt")).text();
    note.textContent =
      out === expected ? "✓ The same output as every other language." : "✗ The output differs from the other languages.";
  } catch (error) {
    output.textContent = String(error);
    note.textContent = "";
  }
});

// What the page loads for Hrefine, measured when the site was built.

fetch("sizes.json")
  .then((response) => response.json())
  .then((/** @type {{ name: string, raw: number, gzip: number }[]} */ sizes) => {
    const kb = (/** @type {number} */ n) => `${(n / 1024).toFixed(0)} KB`;
    $("sizes").textContent = sizes
      .map(({ name, raw, gzip }) => `This page loads ${name}: ${kb(raw)}, or ${kb(gzip)} gzipped.`)
      .join(" ");
  })
  .catch(() => {});

// The WPT scoreboard: web-platform-tests' URL cases, run in this page on
// the browser's URL and on Hrefine, with the module build.py runs in Node.
// It loads and runs only once the section is near, or on its button.

{
  const board = $("scoreboard");
  const runButton = /** @type {HTMLButtonElement} */ ($("score-run"));
  const status = $("score-status");

  /** A case's string as HTML, with control characters shown. @param {string} s */
  const caseText = (s) =>
    shown(s).replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g, (c) =>
      `<span class="ctl" title="control character">\\x${c.charCodeAt(0).toString(16).padStart(2, "0")}</span>`);
  /** @param {string | null} s */
  const value = (s) => (s === null ? '<span class="none">fails</span>' : s === "" ? '<span class="none">""</span>' : `<code>${caseText(s)}</code>`);

  /**
   * One parser's misses, each expandable.
   *
   * @param {string} who
   * @param {import("./scoreboard.js").Miss[]} misses
   */
  function missesHtml(who, misses) {
    if (!misses.length) return "";
    const items = misses.map((m) => {
      const base = m.base === null ? "" : `<span class="miss-base">against <code>${caseText(m.base)}</code></span>`;
      const parts = m.parts.length
        ? `<dt>Parts that differ</dt><dd><ul>${m.parts
            .map((p) => `<li>${p.part}: ${value(p.got)}, not ${value(p.expected)}</li>`)
            .join("")}</ul></dd>`
        : "";
      return (
        `<li><details><summary><code>${caseText(m.input)}</code>${base}</summary><dl>` +
        `<dt>Base</dt><dd>${m.base === null ? '<span class="none">none</span>' : value(m.base)}</dd>` +
        `<dt>Expected</dt><dd>${m.mustFail ? '<span class="none">fails to parse</span>' : value(m.expected)}</dd>` +
        `<dt>${escapeHtml(who)} gave</dt><dd>${value(m.got)}</dd>${parts}</dl></details></li>`
      );
    });
    const count = `${misses.length} ${misses.length === 1 ? "case" : "cases"}`;
    return `<details class="misses"><summary>${escapeHtml(who)}'s misses: ${count}</summary><ol>${items.join("")}</ol></details>`;
  }

  /** The browser's name and major version, from its brand, or null. */
  function browserName() {
    const brands = /** @type {any} */ (navigator).userAgentData?.brands;
    if (!Array.isArray(brands)) return null;
    const real = brands.filter((b) => !/not.?a.?brand/i.test(b.brand));
    const brand = real.find((b) => b.brand !== "Chromium") ?? real[0];
    return brand ? `${brand.brand} ${brand.version}` : null;
  }

  const node = JSON.parse($("score-node-data").textContent ?? "{}");
  const nodeName = `Node ${node.node}`;
  $("score-misses").innerHTML = missesHtml(nodeName, node.builtIn.misses);
  $("score-left-out").textContent = node.leftOut
    ? `${node.leftOut} cases with unpaired surrogates are left out, as in Hrefine's tests, since Temper strings can't hold them.`
    : "None of these cases has unpaired surrogates, which Hrefine's tests leave out, since Temper strings can't hold them.";

  let started = false;
  async function run() {
    if (started) return;
    started = true;
    runButton.disabled = true;
    status.textContent = "Running…";
    try {
      const [scoreboard, data] = await Promise.all([
        import(new URL(board.dataset.module ?? "", document.baseURI).href),
        fetch(board.dataset.cases ?? "").then((r) => r.json()),
      ]);
      const { cases } = scoreboard.wptCases(data);
      const pause = () => new Promise((resolve) => setTimeout(resolve));
      const name = browserName();
      const who = name ? `Your browser (${name})` : "Your browser";
      const t0 = performance.now();
      const browser = await scoreboard.score(cases, scoreboard.builtInParse, pause);
      const ours = await scoreboard.score(cases, hrefine.parseUrl, pause);
      const ms = performance.now() - t0;
      for (const [id, label, s] of [["browser", who, browser], ["hrefine", "Hrefine, in this page", ours]]) {
        const row = $(`score-${id}`);
        row.querySelector(".who")?.firstChild?.replaceWith(`${label} `);
        $(`score-${id}-num`).textContent = `${s.passed} of ${s.total}`;
        row.classList.add(s.passed === s.total ? "all" : "some");
      }
      $("score-misses").innerHTML =
        missesHtml(name ?? "Your browser", browser.misses) +
        missesHtml("Hrefine", ours.misses) +
        missesHtml(nodeName, node.builtIn.misses);
      status.textContent = `Ran in ${Math.round(ms)} ms.`;
    } catch (error) {
      status.textContent = `Couldn't run the tests: ${error}`;
      started = false;
      runButton.disabled = false;
    }
  }

  runButton.addEventListener("click", run);
  if ("IntersectionObserver" in window) {
    const watch = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        watch.disconnect();
        run();
      }
    }, { rootMargin: "400px 0px" });
    // Only after the page has loaded, so the tests never slow the opening.
    const start = () => watch.observe(board);
    if (document.readyState === "complete") start();
    else addEventListener("load", start, { once: true });
  }
}
