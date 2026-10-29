// A tour of Hrefine, from JavaScript.
//
// The same tour exists for each language Hrefine supports, and they all print
// the same text. See demos/README.md for how to run them.

import { Url, domainToAscii, domainToUnicode, parseUrl } from "hrefine";

function section(title) {
  console.log();
  console.log(`## ${title}`);
}

// Tabs and newlines made visible.
const shown = (text) => text.replaceAll("\t", "\\t").replaceAll("\n", "\\n");

// The URL, or null if it isn't one.
function tryParse(text, base = null) {
  try {
    return parseUrl(text, base);
  } catch {
    return null;
  }
}

console.log("# Hrefine tour");

section("1. Parsing and reading parts");

const text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";
const url = parseUrl(text);
console.log(`input: ${text}`);
console.log(`href: ${url.href}`);
console.log(`origin: ${url.origin}`);
console.log(`protocol: ${url.protocol}`);
console.log(`username: ${url.username}`);
console.log(`password: ${url.password}`);
console.log(`host: ${url.host}`);
console.log(`hostname: ${url.hostname}`);
console.log(`port: ${url.port}`);
console.log(`pathname: ${url.pathname}`);
console.log(`search: ${url.search}`);
console.log(`hash: ${url.hash}`);
// Every part is a string, as in the built-in URL, so no port is "".
const plain = parseUrl("HTTPS://example.com:443");
console.log(`default port: ${plain.href}, port "${plain.port}"`);

section("2. Relative URLs");

const base = "https://example.com/docs/guide/intro.html";
console.log(`base: ${base}`);
for (const relative of ["setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"]) {
  // The base is a string, parsed again on each call.
  console.log(`${relative} -> ${parseUrl(relative, base).href}`);
}
// Url.parse is the same as parseUrl, but throws, unlike the built-in
// URL.parse, which gives null.
console.log(`Url.parse: ${Url.parse("setup.html", base).href}`);
// A Url can't be a base itself, so pass its href. (The built-in URL
// takes a URL as a base.)
const guide = parseUrl(base);
console.log(`from a Url: ${parseUrl("faq.html", guide.href).href}`);

section("3. Failures");

// Input that isn't a URL throws a plain Error, with no message, so it says
// nothing of why. (The built-in URL throws a TypeError.)
for (const [input, against] of [
  ["https://exa mple.com", null],
  ["http://[::1", null],
  ["https://example.com:99999", null],
  ["setup.html", null],
  ["setup.html", "not a base"],
]) {
  const label = against ? `${input} against ${against}` : `${input}, without a base`;
  try {
    parseUrl(input, against);
    console.log(`${label}: parsed`);
  } catch {
    console.log(`${label}: not a URL`);
  }
}
// Or wrap it, as tryParse above does, for null in place of failure.
console.log(`as an optional: ${tryParse("https://exa mple.com") === null ? "nothing" : "a URL"}`);

section("4. International domain names");

// Hosts go to ASCII, as browsers send them.
const idn = parseUrl("https://Bücher.example/straße?q=ü");
console.log(`hostname: ${idn.hostname}`);
console.log(`href: ${idn.href}`);
for (const domain of ["Bücher.Example", "faß.de", "☕.example", "xn--tešla"]) {
  try {
    console.log(`to ASCII: ${domain} -> ${domainToAscii(domain)}`);
  } catch {
    console.log(`to ASCII: ${domain} fails`);
  }
}
// And back to Unicode, for showing; it never fails. Decide on the ASCII
// form: the second is a Cyrillic а, not apple.com.
for (const domain of ["xn--bcher-kva.example", "xn--pple-43d.com"]) {
  console.log(`to Unicode: ${domain} -> ${domainToUnicode(domain)}`);
}

section("5. Serializing with href");

// href is the standard's canonical form, which other parsers read alike.
for (const input of [
  "HTTP://EXAMPLE.COM/a/./b/../c",
  "https:\\\\example.com\\path",
  "http://0x7f.1/",
  "https://[0:0::1]:443/",
  "https://example.com/a b?c d#e f",
  " https://exa\tmple.com/\n",
]) {
  console.log(`${shown(input)} -> ${parseUrl(input).href}`);
}
// toString() is href too, so templates and String() give it.
console.log(`as a string: ${url}`);

section("6. Using it safely");

// Decide with Hrefine, then hand on href, never the original string. fetch,
// undici, and axios parse with the runtime's own URL, which follows the same
// standard, but engines differ at the edges, and older code may still use
// the legacy url.parse, which doesn't.
const allowed = new Set(["example.com", "api.example.com"]);

// The URL to fetch, or why not.
function check(input) {
  const url = tryParse(input);
  if (url === null) return "refuse: not a URL";
  if (url.protocol !== "https:") return `refuse: protocol ${url.protocol}`;
  if (!allowed.has(url.hostname)) return `refuse: host ${url.hostname}`;
  // await fetch(url.href, { redirect: "manual" }), never input. Check each
  // redirect the same way. A hostname doesn't say where DNS sends it.
  return `fetch ${url.href}`;
}

for (const input of [
  "https://api.example.com/v1/items",
  "https://example.com\\@evil.example/",
  "https://evil.example#@example.com",
  "https://0x7f.1/admin",
  "http://example.com/",
  "javascript:alert(1)",
  "https://exa mple.com",
]) {
  console.log(`${input}: ${check(input)}`);
}

// A server redirecting to a `next` parameter: resolve it against your own
// origin, and redirect only if the origin stays the same. In Express:
// res.redirect(url.href).
const site = "https://example.com/";
for (const target of ["/account", "//evil.example/", "/\\evil.example"]) {
  const url = tryParse(target, site);
  if (url !== null && url.origin === "https://example.com") {
    console.log(`next=${target}: redirect to ${url.href}`);
  } else {
    console.log(`next=${target}: refuse, ${url ? url.origin : "not a URL"}`);
  }
}
