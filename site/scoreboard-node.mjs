// Runs the site's WPT scoreboard in Node, on Node's own `URL` and on
// Hrefine's JS build, with the same module the page uses. `build.py` runs
// it on the built site and prints its JSON into the page, as the known
// reference beside the visitor's live result.
//
//     node site/scoreboard-node.mjs site/build
//
// Loads Hrefine from the built site's `lib/`, the files the page loads,
// resolving the page's import map names the same way.

import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { pathToFileURL } from "node:url";
import { builtInParse, score, wptCases } from "./scoreboard.js";

const build = pathToFileURL(`${process.argv[2] ?? "site/build"}/`);
// As in index.html's import map.
const imports = {
  hrefine: new URL("lib/hrefine/index.js", build).href,
  "@temperlang/core": new URL("lib/temper-core/index.js", build).href,
};
registerHooks({
  resolve: (specifier, context, next) =>
    Object.hasOwn(imports, specifier)
      ? { url: imports[/** @type {keyof imports} */ (specifier)], shortCircuit: true }
      : next(specifier, context),
});

const { parseUrl } = await import("hrefine");
const data = JSON.parse(readFileSync(new URL("wpt/urltestdata.json", build), "utf8"));
const { cases, leftOut } = wptCases(data);
const result = {
  node: process.versions.node,
  ada: process.versions.ada ?? null,
  leftOut,
  builtIn: await score(cases, builtInParse),
  hrefine: await score(cases, parseUrl),
};
console.log(JSON.stringify(result, null, 1));
