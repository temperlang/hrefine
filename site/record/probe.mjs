// Reads URLs with Node's URL (the browser stand-in, since browsers implement
// the same standard) and Hrefine's JavaScript build, for site/record/record.py.
//
// Each input line is base64 of the input, a space, and base64 of the base
// (or "-" for none). Prints one JSON line per input line.
// Run: node probe.mjs, after temper build -b js.

import { createInterface } from "node:readline";

const { Url, checkUrl } = await import(new URL("../../temper.out/js/hrefine/index.js", import.meta.url));

if (process.argv[2] === "--version") {
  console.log(`Node ${process.version}`);
  process.exit(0);
}

const decode = (text) => Buffer.from(text, "base64").toString("utf8");

function node(input, base) {
  try {
    const url = new URL(input, base ?? undefined);
    // A URL without a host, such as javascript:alert(1), has hostname "".
    const host = url.host === "" && !url.href.startsWith(`${url.protocol}//`) ? null : url.hostname;
    return { ok: true, scheme: url.protocol.slice(0, -1), host, path: url.pathname, href: url.href };
  } catch (error) {
    return { ok: false, error: String(error.code ?? error.message) };
  }
}

function hrefine(input, base) {
  const check = checkUrl(input, base);
  const errors = check.errors.map((e) => e.toString());
  const url = check.url;
  if (url === null) return { ok: false, error: errors.at(-1) ?? "failure", errors };
  const host = url.hostKind === null ? null : url.hostname;
  return { ok: true, scheme: url.scheme, host, path: url.pathname, href: url.href, strictHref: url.strictHref, hostKind: url.hostKind?.toString() ?? null, errors };
}

for await (const line of createInterface({ input: process.stdin })) {
  const [inputText, baseText] = line.split(" ");
  const input = decode(inputText);
  const base = baseText === "-" ? null : decode(baseText);
  console.log(JSON.stringify({ node: node(input, base), hrefine: hrefine(input, base) }));
}
