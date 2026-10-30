// Hrefine's site: the live URL tester, the gallery's live Hrefine answers,
// the language tabs, and the tour. Hrefine comes from Temper's JS output,
// as plain ES modules named by the page's import map.

import * as hrefine from "hrefine";

const { checkUrl } = hrefine;

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
    .replaceAll("\n", '<span class="ctl" title="newline">\\n</span>');
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
// The opening's URL and the gallery's, which have recorded answers.
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
    what = `<span class="host-line">${hostHtml(hHost)}${kind}</span><code>${shown(h.url.href)}</code>`;
  } else {
    const last = h.errors.at(-1);
    what = `<span class="host-line">Not a URL</span>${last ? `<code>${escapeHtml(last.name)}</code>` : ""}`;
  }
  $("hrefine-what").innerHTML = what;

  const browserBox = $("browser-verdict");
  const same = b.url
    ? h.url !== null && b.url.href === h.url.href
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
  const rows = PARTS.map((part) => {
    const hv = h.url ? /** @type {any} */ (h.url)[part] : null;
    const bv = b.url ? /** @type {any} */ (b.url)[part] : null;
    const cell = (/** @type {string | null} */ v) => (v === null ? '<span class="none">—</span>' : v === "" ? '<span class="none">""</span>' : `<code>${shown(v)}</code>`);
    const diff = h.url !== null && b.url !== null && hv !== bv;
    return `<tr class="${diff ? "diff" : ""}"><th scope="row">${part}</th><td>${cell(hv)}</td><td>${cell(bv)}${diff ? ' <span aria-label="differs">≠</span>' : ""}</td></tr>`;
  });
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

  // Validation errors, marked in the input. Positions count code points.
  const points = [...input];
  const at = new Set(h.errors.map((e) => e.position));
  $("marked").innerHTML = h.errors.length
    ? points.map((c, i) => (at.has(i) ? `<mark>${shown(c)}</mark>` : shown(c))).join("") +
      (at.has(points.length) ? '<mark title="end"> </mark>' : "")
    : "";
  $("errors").innerHTML = h.errors.length
    ? h.errors.map((e) => `<li><code>${escapeHtml(e.name)}</code> at ${e.position}</li>`).join("")
    : `<li class="none">${h.baseFailed ? "The base isn't a URL." : "None: a clean URL."}</li>`;

  // Other parsers, where this input is one of the gallery's.
  const known = recordedInputs.find((c) => c.dataset.input === input && (c.dataset.base ?? null) === base);
  const table = known?.querySelector(".table-scroll");
  $("recorded-table").replaceChildren(...(table ? [table.cloneNode(true)] : []));
  const which = known?.dataset.title === "opening" ? "the opening's URL" : `the gallery's “${known?.dataset.title}” URL`;
  $("recorded-note").textContent = table
    ? `This is ${which}, so here are other parsers' answers, recorded ahead of time. The browser row is Node's URL, standing in for browsers.`
    : "Other languages' parsers can't run in your browser. For the gallery's URLs, this page shows their answers, recorded ahead of time; pick one above. For anything else, only Hrefine and your browser run live.";
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

/** @param {string} file */
async function selectLanguage(file) {
  selected = file;
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

// The JavaScript tour runs as the body of a function given Hrefine's
// exports, with console.log sent to the page, and its output is compared
// with the text every language's tour prints.

$("tour-run").addEventListener("click", async () => {
  const output = $("tour-output");
  const note = $("tour-run-note");
  output.hidden = false;
  output.textContent = "Running…";
  try {
    const code = (sources.get("js") ?? "").replace(/^import \{[^}]*\} from "hrefine";$/m, "");
    /** @type {string[]} */
    const lines = [];
    const log = (/** @type {unknown[]} */ ...args) => lines.push(args.map(String).join(" "));
    const names = Object.keys(hrefine);
    const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
    await new AsyncFunction(...names, "console", code)(
      ...names.map((n) => /** @type {any} */ (hrefine)[n]),
      { log },
    );
    const out = lines.map((line) => line + "\n").join("");
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
