// A tour of Hrefine, from JavaScript.
//
// The same tour exists for each language Hrefine supports, and they all print
// the same text. See demos/README.md for how to run them.

import { Pair } from "@temperlang/core";
import {
  HostKind, Url, UrlDisplay, UrlPolicy, UrlSearchParams, checkUrl, domainToAscii, domainToDisplay, domainToUnicode, parseHost, parseUrl,
  parseUrlSource,
} from "hrefine";

function section(title) {
  console.log();
  console.log(`## ${title}`);
}

// Tabs and newlines made visible.
const shown = (text) => text.replaceAll("\t", "\\t").replaceAll("\n", "\\n");

console.log("# Hrefine tour");

section("1. Parsing and reading parts");

const text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";  // snippet: hero
const url = parseUrl(text);  // snippet: hero, parts
console.log(`input: ${text}`);
// No username or password in href, by design (see section 5).
console.log(`href: ${url.href}`);  // snippet: parts
console.log(`origin: ${url.origin}`);  // snippet: parts
console.log(`protocol: ${url.protocol}`);  // snippet: parts
console.log(`username: ${url.username}`);  // snippet: parts
console.log(`password: ${url.password}`);  // snippet: parts
console.log(`host: ${url.host}`);  // snippet: parts
console.log(`hostname: ${url.hostname}`);  // snippet: parts, hero
console.log(`port: ${url.port}`);  // snippet: parts
console.log(`pathname: ${url.pathname}`);  // snippet: parts
console.log(`search: ${url.search}`);  // snippet: parts
console.log(`hash: ${url.hash}`);  // snippet: parts
// Typed parts, beside the standard's strings.
console.log(`scheme: ${url.scheme}`);  // snippet: parts
console.log(`port number: ${url.portNumber}`);  // snippet: parts
console.log(`host kind: ${url.hostKind}`);  // snippet: parts
// The standard's parts are strings, as in the built-in URL, so no port is
// "", and portNumber is null.
const plain = parseUrl("HTTPS://example.com:443");
console.log(`default port: ${plain.href}, port "${plain.port}", port number ${plain.portNumber ?? "none"}`);

section("2. Relative URLs");

// Parse the base once, then resolve against it.
const guide = parseUrl("https://example.com/docs/guide/intro.html");  // snippet: base
console.log(`base: ${guide.href}`);
for (const relative of ["setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"]) {  // snippet: base
  console.log(`${relative} -> ${guide.resolve(relative).href}`);  // snippet: base
}  // snippet: base
// Or give the base as a string, parsed on each call. (Unlike the built-in
// URL, a Url isn't taken as a base.)
console.log(`with a string base: ${parseUrl("faq.html", guide.href).href}`);  // snippet: base

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
  const check = checkUrl(input);  // snippet: errors
  const errors = check.errors.map((error) => `${error}`).join(", ");  // snippet: errors
  console.log(`${input}: ${check.url?.href ?? "not a URL"} (${errors})`);  // snippet: errors
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
// href has no credentials, by design, unlike JavaScript's URL.href, so it's
// the one to hand on, store, or compare as text. toString() masks them, for
// logs (templates and String() give it too), and withoutCredentials() gives
// a Url without them. Only to send them deliberately, there's
// hrefWithCredentials, which has the password: never log it.
console.log(`href, to hand on: ${url.href}`);
console.log(`as a string: ${url.toString()}`);
console.log(`without credentials: ${url.withoutCredentials().toString()}`);
// eq compares whole URLs, credentials included; === compares objects.
console.log(`same without credentials: ${url.eq(url.withoutCredentials())}`);
console.log(`same URL: ${parseUrl("HTTP://EXAMPLE.COM/a/./b/../c").eq(parseUrl("http://example.com/a/c"))}`);
// strictHref also escapes what RFC 3986 parsers reject, for those that
// follow it strictly.
const strict = parseUrl("https://example.com/a|b/%zz?q={x}#c^d");  // snippet: proof
console.log(`strict: ${strict.href} -> ${strict.strictHref}`);  // snippet: proof

section("6. Using it safely");

// Decide with Hrefine, then hand on href, never the original string. fetch,
// undici, and axios parse with the runtime's own URL, which follows the same
// standard, but engines differ at the edges, and older code may still use
// the legacy url.parse, which doesn't.
const allowed = new Set(["example.com", "api.example.com"]);

// The URL to fetch, or why not.
function check(input) {  // snippet: card
  const url = Url.parse(input);  // snippet: card
  if (url === null) return "refuse: not a URL";  // snippet: card
  if (url.scheme !== "https") return `refuse: scheme ${url.scheme}`;  // snippet: card
  // An IP address isn't a name on the list, however it's written.
  if (url.hostKind !== HostKind.domain) return `refuse: ${url.hostKind} host ${url.hostname}`;  // snippet: card
  if (!allowed.has(url.hostname)) return `refuse: host ${url.hostname}`;  // snippet: card
  // await fetch(url.href, { redirect: "manual" }), never input. Check each
  // redirect the same way. A hostname doesn't say where DNS sends it.
  return `fetch ${url.href}`;  // snippet: card
}  // snippet: card

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

section("7. Changing parts");

// The standard's setters, as methods that give a new URL, so a URL that
// passed a check can't change after. A value that can't be set is ignored,
// as when assigning to JavaScript's URL.
const page = parseUrl("https://example.com/docs?lang=en&q=a+b");
console.log(`page: ${page.href}`);
console.log(`with host: ${page.withHost("example.org:8443").href}`);
console.log(`with pathname and hash: ${page.withPathname("/a b").withHash("top").href}`);
console.log(`with protocol: ${page.withProtocol("http").href}`);
console.log(`port "http", ignored: ${page.withPort("http").href}`);
console.log(`with port number: ${page.withPortNumber(8443).href}`);
console.log(`unchanged: ${page.href}`);
// Search parameters: a copy of the query, changed in place, then put back.
const params = page.searchParams;
console.log(`q: ${params.get("q")}`);
params.append("lang", "fr");
params.set("q", "café & more");
params.remove("missing");
params.sort();
console.log(`lang: ${params.getAll("lang").join(", ")}`);
for (const entry of params.entries()) {
  console.log(`${entry.key} = ${entry.value}`);
}
console.log(`with search params: ${page.withSearchParams(params).href}`);
// Or from pairs of names and values.
console.log(`from pairs: ${UrlSearchParams.fromEntries([new Pair("q", "a b"), new Pair("page", "2")])}`);

section("8. Test cases");

// Each of web-platform-tests' URL cases gives an input, a base, and the
// standard's href it must parse to (the full form, with credentials), or
// "" where parsing must fail. Hrefine's tests run them all, checking
// every part, and so does the site, in the browser.
const cases = [
  ["http:\\\\foo.com\\", "http://example.org/foo/bar", "http://foo.com/"],
  ["../aaa/test.txt", "http://www.example.com/test", "http://www.example.com/aaa/test.txt"],
  ["http://999999999", "http://other.com/", "http://59.154.201.255/"],
  ["http://192.168.0.257", "http://other.com/", ""],
];
for (const [input, base, href] of cases) {  // snippet: scoreboard
  const url = Url.parse(input, base);  // snippet: scoreboard
  const got = url === null ? "" : url.hrefWithCredentials;  // snippet: scoreboard
  console.log(`${input} against ${base}: ${got === href ? "pass" : "fail"}`);  // snippet: scoreboard
}  // snippet: scoreboard

section("9. Policies");

// A policy does the checks of section 6 in one call, on the parsed URL. Build
// it once, a rule at a time, and use it for every URL. UrlPolicy.fetch, for
// URLs a server fetches, is https only, strict, with no credentials and no
// private, loopback, or other special addresses or names; this one adds
// example.com or its subdomains. Reasons never show credentials.
const policy = UrlPolicy.fetch.withHosts(["example.com"], true);  // snippet: policy
const inputs = [
  "https://api.example.com/v1/items",
  "http://example.com/",
  "https://example.com@evil.example/",
  "https://127.1/",
  "https://169.254.169.254/latest/meta-data/",
  "https://[::ffff:127.0.0.1]/",
  "https://localhost./",
  "https://ex\u0430mple.com/",
];
for (const input of inputs) {  // snippet: policy
  const result = policy.check(input);  // snippet: policy
  if (result.url !== null) {  // snippet: policy
    console.log(`${input}: fetch ${result.url.href}`);  // snippet: policy
  } else {  // snippet: policy
    console.log(`${input}: refuse, ${result.toString()}`);  // snippet: policy
  }  // snippet: policy
}  // snippet: policy

// Strict mode refuses what the standard accepts but notes as an error, as
// cautious parsers do: backslashes, tabs, odd IPv4 forms, and the like.
// withStrict(true) adds it to a policy.
for (const input of ["https://example.com/a b", "http://0x7f.1/", "https://example.com\\a", " https://example.com/"]) {
  const check = checkUrl(input);
  const strict = check.strictUrl;
  if (strict !== null) {
    console.log(`strict ${shown(input)}: ${strict.href}`);
  } else {
    const errors = check.strictErrors.map((error) => error.toString()).join(", ");
    console.log(`strict ${shown(input)}: refuse, ${errors}`);
  }
}

// Redirect targets: withPathOnly takes only a path, query, or fragment on
// the base, never another host, however it's written.
const redirects = UrlPolicy.any.withBase(site).withPathOnly(true);
for (const target of ["/account?tab=2", "//evil.example/", "/\\evil.example", "/\t/evil.example", "https://example.com/"]) {
  const result = redirects.check(target);
  console.log(`next=${shown(target)}: ${result.url !== null ? `redirect to ${result.url.href}` : `refuse, ${result.toString()}`}`);
}

section("10. Showing, comparing, and spans");

// To show people a URL, as browsers' address bars do: hosts in Unicode
// where browsers would show them (not look-alikes such as Cyrillic а in
// xn--pple-43d.com), and escapes of non-ASCII text decoded. Never for
// security decisions, nor for handing on: use href for those.
const display = UrlDisplay.addressBar.withRootSlash(false);  // snippet: display
for (const input of [  // snippet: display
  "https://user@xn--bcher-kva.example/caf%C3%A9?q=%E6%97%A5%E6%9C%AC",  // snippet: display
  "https://xn--pple-43d.com/",  // snippet: display
  "https://пример.рф/",  // snippet: display
  "https://аррӏе.com/",  // snippet: display
]) {  // snippet: display
  console.log(`display: ${display.format(parseUrl(input))}`);  // snippet: display
}  // snippet: display
// href stays ASCII, to hand on.
console.log(`to hand on: ${parseUrl("https://пример.рф/").href}`);
// Hosts alone, as Chrome shows them, by Unicode's script and look-alike
// data: all Cyrillic, but every letter like a Latin one, keeps xn--,
// unless the top-level domain is Cyrillic too; Cyrillic а among Latin
// letters always does. The rest show in Unicode.
for (const host of ["аррӏе.com", "аррӏе.рф", "аpple.com", "пример.рф", "日本語.jp"]) {  // snippet: lookalike
  console.log(`${host}: ${domainToDisplay(host)}`);  // snippet: lookalike
}  // snippet: lookalike
// Credentials are left out, as address bars leave them out. Asked for, the
// username shows, but a password only as ***.
console.log(`with credentials: ${display.withCredentials(true).format(parseUrl("https://user:pass@example.com/"))}`);

// The same URL, the same but for the fragment, or the same origin. All
// compare canonical forms, so case and a default port don't matter.
const intro = parseUrl("https://EXAMPLE.com:443/a/../guide#intro");
const setup = parseUrl("https://example.com/guide#setup");
console.log(`same URL: ${intro.eq(setup)}`);
console.log(`same document: ${intro.sameDocument(setup)}`);
console.log(`same origin: ${intro.sameOrigin(parseUrl("https://example.com/about"))}`);

// Where each part was written, for editors and linters: never for security
// decisions, which use source.url. Spans count code points.
const source = parseUrlSource(" https://EXAMPLE.com:443/a/../b?q=1");
console.log(`href: ${source.url.href}`);
console.log(`host as written: ${source.hostSpan.asWritten}, at ${source.hostSpan.toString()}`);
console.log(`path as written: ${source.pathSpan.asWritten}`);
for (const error of checkUrl("https://exa mple.com").errors) {
  console.log(`${error.name}: from ${error.position}, ${error.length} long`);
}
