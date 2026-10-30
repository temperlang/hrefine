// @ts-check

// Dev mode: a switch that shows the Hrefine code behind each part of the
// page, in any of its languages. Badges sit over the page, and each opens a
// card with a short snippet. The design and code follow Chromarite's and
// Ordable's sites.
//
// Snippets come from the tours: build.py collects lines marked
// `snippet: <name>` into snippets.json, and CI runs every tour, so each
// snippet is code that runs. The build fails if a spot here has no snippet.

/**
 * A part of the page with code behind it. `id` names its snippet.
 * @typedef {{ id: string, title: string, about: string, target: () => Element | null | undefined }} Spot
 *
 * In `about`, names in backticks are Hrefine's, as JavaScript spells them;
 * the card spells them as the chosen language does.
 */

/**
 * A language of the tours: its name, the tour file's extension, and its
 * line comment.
 * @typedef {{ name: string, file: string, comment: string }} Language
 */

/** @param {string} selector */
const find = (selector) => document.querySelector(selector);

/** @type {Spot[]} */
export const SPOTS = [
  {
    id: "hero",
    title: "Which host?",
    about: "`parseUrl` reads a URL as browsers do, and `hostname` gives its host, in ASCII. It throws where the standard fails; `Url.parse` gives null instead.",
    target: () => find(".hero-demo .the-url code"),
  },
  {
    id: "base",
    title: "Relative to a base",
    about: "Parse a base once, then `resolve` against it, or give `parseUrl` the base as a string.",
    target: () => find(".base-field"),
  },
  {
    id: "parts",
    title: "Each part",
    about: "A `Url` has the standard's parts as strings, as JavaScript's URL does, but `href` leaves out the credentials, by design; `hrefWithCredentials` has them. Typed parts sit beside them: `scheme`, `portNumber`, and `hostKind`.",
    target: () => find("#parts"),
  },
  {
    id: "display",
    title: "How people see it",
    about: "`UrlDisplay.addressBar` shows hosts in Unicode only where browsers would (not look-alikes such as Cyrillic а in xn--pple-43d.com), decodes escaped non-ASCII text where that's safe, and leaves out credentials (the username and password in the URL), as address bars do; methods such as `withRootSlash` change parts. Then `format` each URL. It's for people only: decide, and hand on, with `href`.",
    target: () => find("#hrefine-what .display-line"),
  },
  {
    id: "errors",
    title: "What's wrong with it",
    about: "`checkUrl` gives the URL, or null, and the standard's validation errors, each with its name, and its `position` and `length` in code points of the input as given. Where parsing fails, the last error says why.",
    target: () => find("#errors"),
  },
  {
    id: "card",
    title: "Check, then hand on href",
    about: "Decide with `Url.parse`, checking `scheme`, `hostKind`, and `hostname`, then give your HTTP client `href`, never the original string, so it can't read another host. `href` has no credentials, so it can't leak them; use `hrefWithCredentials` only to send them deliberately.",
    target: () => find(".cards .card"),
  },
  {
    id: "policy",
    title: "A policy, in one call",
    about: "Build a `UrlPolicy` once from `UrlPolicy.fetch` (https only, strict, no credentials or private addresses), adding a rule per method such as `withHosts`, then `check` each URL. It gives the `url` to hand on, or says which rule failed and why, never echoing credentials, all on the parsed URL, so 127.1 and [::ffff:127.0.0.1] are refused too.",
    target: () => find(".fix .policy-step"),
  },
  {
    id: "proof",
    title: "href and strictHref",
    about: "`href` is the standard's canonical form, without credentials, which other parsers read alike. `strictHref` also escapes what RFC 3986 doesn't allow, for strict parsers such as Java's URI.",
    target: () => find(".proof-table"),
  },
  {
    id: "scoreboard",
    title: "Running the test cases",
    about: "Each web-platform-tests case gives an input, a base, and the standard's href it must parse to (Hrefine's `hrefWithCredentials`, since its `href` leaves them out), or that parsing must fail, where `Url.parse` gives null. This scoreboard and Hrefine's own tests check every part too.",
    target: () => find("#score-hrefine"),
  },
];

// Properties, which some languages read with getters.
const PROPERTIES = new Set([
  "href", "hrefWithCredentials", "strictHref", "strictHrefWithCredentials", "hostname", "scheme", "portNumber", "hostKind", "url", "errors", "strictErrors",
  "asWritten", "hostSpan", "position", "length",
]);
// Static properties, such as `UrlPolicy.any`, which Rust reads with a call.
const STATICS = new Set(["any", "fetch", "addressBar", "domain", "ipv4", "ipv6", "opaque", "empty"]);

/**
 * A Hrefine name, like `Url.parse` or `hostKind`, as `file`'s language
 * spells it: snake_case in Python and Rust, PascalCase in C#, `::` after a
 * type in C++ and Rust, properties as getters in C++, Java, and Rust, and
 * static properties as calls in Rust (`UrlPolicy::any()`). The build checks
 * each card's names against the tours (`spell-node.mjs`).
 *
 * @param {string} name
 * @param {string} file
 * @returns {string}
 */
export function spell(name, file) {
  const parts = name.split(".").map((part, k, all) => {
    if (/^[A-Z]/.test(part)) return part;
    const isStatic = k > 0 && /^[A-Z]/.test(all[k - 1]) && STATICS.has(part);
    const property = !isStatic && PROPERTIES.has(part);
    const snake = part.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
    const pascal = part[0].toUpperCase() + part.slice(1);
    if (file === "py") return snake;
    if (file === "rs") return property || isStatic ? `${snake}()` : snake;
    if (file === "cs") return pascal;
    if (file === "java" && property) return `get${pascal}()`;
    if (file === "cpp" && property) return `get_${part}()`;
    return part;
  });
  return parts.join(file === "rs" || file === "cpp" ? "::" : ".");
}

/** @param {string} s */
const escapeHtml = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c] ?? c);

// Phones get the card as a sheet along the bottom instead.
const narrow = matchMedia("(max-width: 640px)");

/**
 * Sets up dev mode.
 *
 * @param {{
 *   toggle: HTMLButtonElement,
 *   languages: Language[],
 *   language: string,
 *   highlight: (code: string, comment: string) => string,
 *   showTour: (file: string) => void,
 * }} options
 * @returns {{ setLanguage: (file: string) => void }}
 */
export function initDevMode({ toggle, languages, language, highlight, showTour }) {
  /** @type {Record<string, Record<string, string>> | null} */
  let snippets = null;
  /** @type {Spot | null} */
  let open = null;
  let frame = 0;

  const layer = document.createElement("div");
  layer.className = "dev-layer";
  layer.hidden = true;
  const badges = new Map(
    SPOTS.map((spot) => {
      const badge = document.createElement("button");
      badge.type = "button";
      badge.className = "dev-badge";
      badge.textContent = "</>";
      badge.setAttribute("aria-label", `Code: ${spot.title}`);
      badge.setAttribute("aria-expanded", "false");
      badge.setAttribute("aria-controls", "dev-card");
      badge.addEventListener("click", () => (open === spot ? close() : show(spot)));
      layer.append(badge);
      return [spot, badge];
    }),
  );

  const card = document.createElement("div");
  card.id = "dev-card";
  card.className = "dev-card";
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-labelledby", "dev-card-title");
  card.tabIndex = -1;
  card.hidden = true;
  card.innerHTML = `
    <div class="dev-card-head">
      <h3 id="dev-card-title"></h3>
      <button type="button" class="dev-close" aria-label="Close">×</button>
    </div>
    <p class="dev-about"></p>
    <div class="dev-languages" role="group" aria-label="Language"></div>
    <pre class="dev-code"><code></code></pre>
    <p class="dev-foot"><span>From the <span class="dev-lang"></span> tour, which runs in CI.</span>
      <button type="button" class="dev-tour">See it in the full tour</button></p>`;
  const $ = (/** @type {string} */ selector) => /** @type {HTMLElement} */ (card.querySelector(selector));
  for (const { name, file } of languages) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.textContent = name;
    chip.dataset.file = file;
    chip.addEventListener("click", () => setLanguage(file));
    $(".dev-languages").append(chip);
  }
  $(".dev-close").addEventListener("click", () => close());
  $(".dev-tour").addEventListener("click", () => {
    close(false);
    showTour(language);
  });
  document.body.append(layer, card);

  /** Fills the card with the open spot's snippet in the chosen language. */
  function render() {
    if (!open) return;
    const lang = languages.find((l) => l.file === language) ?? languages[0];
    $("#dev-card-title").textContent = open.title;
    $(".dev-about").innerHTML = escapeHtml(open.about).replace(/`([^`]+)`/g, (_, name) => `<code>${spell(name, lang.file)}</code>`);
    $(".dev-lang").textContent = lang.name;
    for (const chip of $(".dev-languages").children) {
      chip.setAttribute("aria-pressed", String(/** @type {HTMLElement} */ (chip).dataset.file === lang.file));
    }
    const code = snippets?.[open.id]?.[lang.file];
    $(".dev-code code").innerHTML = code
      ? highlight(code, lang.comment)
      : snippets
        ? "This snippet is missing."
        : "Loading…";
  }

  /** @param {Spot} spot */
  async function show(spot) {
    if (open) badges.get(open)?.setAttribute("aria-expanded", "false");
    open = spot;
    badges.get(spot)?.setAttribute("aria-expanded", "true");
    card.hidden = false;
    render();
    place();
    card.focus({ preventScroll: true });
    card.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function close(refocus = true) {
    if (!open) return;
    const badge = badges.get(open);
    badge?.setAttribute("aria-expanded", "false");
    open = null;
    card.hidden = true;
    if (refocus) badge?.focus({ preventScroll: true });
  }

  /** @param {string} file */
  function setLanguage(file) {
    if (!languages.some((l) => l.file === file)) return;
    language = file;
    render();
    // The card's height may change with the language, so keep it in view.
    place();
    if (open) card.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  // Badges go at their parts' top right corners, in page coordinates, so
  // they scroll with the page; layout changes move them.
  function place() {
    frame = 0;
    if (layer.hidden) return;
    const width = document.documentElement.clientWidth;
    for (const [spot, badge] of badges) {
      const target = spot.target();
      const rect = target?.getBoundingClientRect();
      const shown = !!rect && rect.width > 0 && rect.height > 0;
      badge.hidden = !shown;
      if (!shown || !rect) continue;
      badge.style.left = `${Math.min(rect.right - 14, width - 40) + scrollX}px`;
      badge.style.top = `${rect.top - 14 + scrollY}px`;
    }
    if (!open) return;
    const badge = badges.get(open);
    if (!badge || badge.hidden) return close(false);
    if (narrow.matches) {
      card.style.left = card.style.top = "";
      return;
    }
    // Below the badge if it fits on screen, else above it.
    const b = badge.getBoundingClientRect();
    const w = card.offsetWidth;
    const h = card.offsetHeight;
    const below = b.bottom + 10 + h <= innerHeight || b.top - 10 - h < 0;
    card.style.left = `${Math.max(16, Math.min(b.right - w + 12, width - w - 16)) + scrollX}px`;
    card.style.top = `${(below ? b.bottom + 10 : b.top - 10 - h) + scrollY}px`;
  }
  const schedule = () => {
    if (!frame && !layer.hidden) frame = requestAnimationFrame(place);
  };

  addEventListener("resize", schedule);
  new ResizeObserver(schedule).observe(document.body);
  // Clicks and input can show, hide, or move parts, like the tester does.
  document.addEventListener("click", schedule, true);
  document.addEventListener("input", schedule, true);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && open) close();
  });
  document.addEventListener("pointerdown", (event) => {
    const t = /** @type {Node} */ (event.target);
    if (open && !card.contains(t) && !layer.contains(t)) close(false);
  });

  toggle.addEventListener("click", async () => {
    const on = toggle.getAttribute("aria-pressed") !== "true";
    toggle.setAttribute("aria-pressed", String(on));
    toggle.querySelector(".dev-label").textContent = on ? "Hide the code" : "Show the code";
    layer.hidden = !on;
    if (!on) return close(false);
    place();
    if (!snippets) {
      try {
        const response = await fetch("snippets.json", { cache: "no-cache" });
        snippets = response.ok ? await response.json() : {};
      } catch {
        snippets = {};
      }
      render();
    }
  });

  return { setLanguage };
}
