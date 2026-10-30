// A tour of Hrefine, from JavaScript.
//
// The same tour exists for each language Hrefine supports, and they all print
// the same text. See demos/README.md for how to run them.

import { HostKind, Url, checkUrl, domainToAscii, domainToUnicode, parseHost, parseUrl } from "hrefine";

function section(title) {
  console.log();
  console.log(`## ${title}`);
}

// Tabs and newlines made visible.
const shown = (text) => text.replaceAll("\t", "\\t").replaceAll("\n", "\\n");

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
// Typed parts, beside the standard's strings.
console.log(`scheme: ${url.scheme}`);
console.log(`port number: ${url.portNumber}`);
console.log(`host kind: ${url.hostKind}`);
// The standard's parts are strings, as in the built-in URL, so no port is
// "", and portNumber is null.
const plain = parseUrl("HTTPS://example.com:443");
console.log(`default port: ${plain.href}, port "${plain.port}", port number ${plain.portNumber ?? "none"}`);

section("2. Relative URLs");

// Parse the base once, then resolve against it.
const guide = parseUrl("https://example.com/docs/guide/intro.html");
console.log(`base: ${guide.href}`);
for (const relative of ["setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"]) {
  console.log(`${relative} -> ${guide.resolve(relative).href}`);
}
// Or give the base as a string, parsed on each call. (Unlike the built-in
// URL, a Url isn't taken as a base.)
console.log(`with a string base: ${parseUrl("faq.html", guide.href).href}`);

section("3. Failures");

// checkUrl says why input isn't a URL, with the standard's names for
// what's wrong and where, counted in code points. The last error is why it
// failed. Some errors don't stop a URL from parsing, as browsers accept it.
for (const input of [
  "https://exa mple.com",
  "http://[::1",
  "https://example.com:99999",
  "setup.html",
  "https:example.com/a b",
]) {
  const check = checkUrl(input);
  const errors = check.errors.map((error) => `${error}`).join(", ");
  console.log(`${input}: ${check.url?.href ?? "not a URL"} (${errors})`);
}
// As with the built-in URL: Url.parse gives null where parseUrl throws, and
// Url.canParse says only whether it would parse.
console.log(`nullable parse: ${Url.parse("setup.html") === null ? "nothing" : "a URL"}`);
console.log(`can parse: ${Url.canParse("setup.html")}`);
// parseUrl throws a plain Error, with no message, so checkUrl says why.
// (The built-in URL throws a TypeError.)
try {
  parseUrl("setup.html");
  console.log("throwing parse: parsed");
} catch {
  console.log("throwing parse: throws");
}

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
// eq compares hrefs; === compares objects.
console.log(`same URL: ${parseUrl("HTTP://EXAMPLE.COM/a/./b/../c").eq(parseUrl("http://example.com/a/c"))}`);

section("6. Using it safely");

// Decide with Hrefine, then hand on href, never the original string. fetch,
// undici, and axios parse with the runtime's own URL, which follows the same
// standard, but engines differ at the edges, and older code may still use
// the legacy url.parse, which doesn't.
const allowed = new Set(["example.com", "api.example.com"]);

// The URL to fetch, or why not.
function check(input) {
  const url = Url.parse(input);
  if (url === null) return "refuse: not a URL";
  if (url.scheme !== "https") return `refuse: scheme ${url.scheme}`;
  // An IP address isn't a name on the list, however it's written.
  if (url.hostKind !== HostKind.domain) return `refuse: ${url.hostKind} host ${url.hostname}`;
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

// Check hosts from configuration with parseHost, which domainToAscii isn't
// for: it passes all three.
for (const input of ["example.com", "0x7f.1", "exa mple.com"]) {
  try {
    const host = parseHost(input);
    console.log(`host ${input}: ${host.kind} ${host.serialized}`);
  } catch {
    console.log(`host ${input}: not a host`);
  }
}

// A server redirecting to a `next` parameter: resolve it against your own
// site, and redirect only to the same origin. In Express:
// res.redirect(url.href).
const site = parseUrl("https://example.com/");
for (const target of ["/account", "//evil.example/", "/\\evil.example", "//[::1"]) {
  const url = site.tryResolve(target);
  if (url !== null && url.sameOrigin(site)) {
    console.log(`next=${target}: redirect to ${url.href}`);
  } else {
    console.log(`next=${target}: refuse, ${url ? url.origin : "not a URL"}`);
  }
}
