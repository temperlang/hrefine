// Scores a URL parser on web-platform-tests' urltestdata.json, by the same
// rules as Hrefine's own test (scripts/wpt_tests.py): each case either must
// fail, or must give the expected href and every other part, with the
// origin checked where the case gives one. Cases whose strings hold
// unpaired surrogates are left out, and counted, as Hrefine's test leaves
// them out.
//
// The page runs this on the browser's `URL` and on Hrefine's JS build, and
// `scoreboard-node.mjs` runs it in Node at build time, so both count alike.
// It imports nothing, so it loads the same way in both.

/** The parts every case that parses must match, origin only where given. */
export const PARTS = ["href", "origin", "protocol", "username", "password", "host", "hostname", "port",
  "pathname", "search", "hash"];

/** @param {string} s */
const hasLoneSurrogate = (s) => /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/.test(s);

/**
 * @typedef {{ input: string, base?: string | null, failure?: boolean } & Record<string, any>} Case
 * @typedef {{ part: string, expected: string, got: string }} PartMiss
 * @typedef {{ input: string, base: string | null, mustFail: boolean, expected: string | null,
 *   got: string | null, parts: PartMiss[] }} Miss
 * @typedef {{ total: number, passed: number, misses: Miss[] }} Score
 */

/**
 * The cases to run, from the parsed JSON (which mixes in comment strings),
 * and how many were left out for unpaired surrogates.
 *
 * @param {unknown[]} data
 * @returns {{ cases: Case[], leftOut: number }}
 */
export function wptCases(data) {
  const all = /** @type {Case[]} */ (data.filter((c) => typeof c === "object" && c !== null));
  const cases = all.filter((c) =>
    ![c.input, c.base ?? "", ...PARTS.map((p) => c[p] ?? "")].some(hasLoneSurrogate));
  return { cases, leftOut: all.length - cases.length };
}

/**
 * How one parser does on one case: null if it passes, or what it missed.
 *
 * @param {Case} c
 * @param {(input: string, base: string | null) => any} parse Gives a URL
 *   with the standard's getters, or throws or gives null for a failure.
 * @returns {Miss | null}
 */
export function checkCase(c, parse) {
  const base = c.base ?? null;
  const mustFail = c.failure === true;
  let url = null;
  try {
    url = parse(c.input, base);
  } catch {
    url = null;
  }
  const got = url ? String(url.href) : null;
  const miss = { input: c.input, base, mustFail, expected: mustFail ? null : (c.href ?? ""), got, parts: [] };
  if (url === null) return mustFail ? null : miss;
  if (mustFail) return miss;
  for (const part of PARTS) {
    if (part === "origin" && !("origin" in c)) continue;
    const expected = c[part] ?? "";
    const actual = String(url[part]);
    if (actual !== expected) miss.parts.push({ part, expected, got: actual });
  }
  return miss.parts.length ? miss : null;
}

/**
 * Runs every case through a parser. `pause`, if given, is awaited every
 * `every` cases, so a page can stay responsive.
 *
 * @param {Case[]} cases
 * @param {(input: string, base: string | null) => any} parse
 * @param {(() => Promise<void>) | null} [pause]
 * @param {number} [every]
 * @returns {Promise<Score>}
 */
export async function score(cases, parse, pause = null, every = 100) {
  /** @type {Miss[]} */
  const misses = [];
  for (const [i, c] of cases.entries()) {
    if (pause && i && i % every === 0) await pause();
    const miss = checkCase(c, parse);
    if (miss) misses.push(miss);
  }
  return { total: cases.length, passed: cases.length - misses.length, misses };
}

/** The browser's or Node's own parser, as the cases call it. @param {string} input @param {string | null} base */
export const builtInParse = (input, base) => (base === null ? new URL(input) : new URL(input, base));
