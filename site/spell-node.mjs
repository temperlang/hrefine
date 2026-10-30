// Checks dev mode's cards: each name in backticks in a card's text, as
// `spell` writes it for each language, must be in that language's tour, as
// a whole name, and called with `()` there only if it's spelled so, so the
// card never shows a name the language doesn't have, or a call as a field. `build.py` runs it
// on the built site.
//
//     node site/spell-node.mjs site/build

import { readFileSync } from "node:fs";

// devmode.js reads the page's width on load; Node has no page.
globalThis.matchMedia = () => /** @type {MediaQueryList} */ ({ matches: false });
const { SPOTS, spell } = await import("./devmode.js");

const build = `${process.argv[2] ?? "site/build"}/`;
const files = ["cpp", "cs", "java", "js", "lua", "py", "rs"];
const missing = [];
for (const file of files) {
  const tour = readFileSync(`${build}tour/tour.${file}`, "utf8");
  for (const spot of SPOTS) {
    for (const [, name] of spot.about.matchAll(/`([^`]+)`/g)) {
      const spelled = spell(name, file);
      const escaped = spelled.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const call = spelled.endsWith("()") ? "" : "(?!\\(\\))";
      if (!new RegExp(`(?<![\\w$])${escaped}(?![\\w$])${call}`).test(tour)) missing.push(`${spot.id}: ${name} as ${spelled} in tour.${file}`);
    }
  }
}
if (missing.length) {
  console.error(`Dev mode's cards name what the tours don't have:\n${missing.join("\n")}`);
  process.exit(1);
}
