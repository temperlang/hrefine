// A tour of Hrefine, from C++.
//
// The same tour exists for each language Hrefine supports, and they all print
// the same text. See demos/README.md for how to run them.

#include <iostream>
#include <memory>
#include <set>
#include <string>

#include "hrefine/init.hpp"

using hrefine::HostKind;
using hrefine::Url;
using hrefine::UrlSearchParams;
using hrefine::checkUrl;
using hrefine::domainToAscii;
using hrefine::domainToUnicode;
using hrefine::parseHost;
using hrefine::parseUrl;
using temper::core::TemperBubble;

void section(std::string const &title) { std::cout << "\n## " << title << "\n"; }

// Tabs and newlines made visible.
std::string shown(std::string const &text) {
  std::string out;
  for (char c : text) {
    out += c == '\t' ? "\\t" : c == '\n' ? "\\n" : std::string(1, c);
  }
  return out;
}

const std::set<std::string> allowed = {"example.com", "api.example.com"};

// The URL to fetch, or why not.
std::string check(std::string const &input) {  // snippet: card
  auto url = Url::parse(input);  // snippet: card
  if (!url) return "refuse: not a URL";  // snippet: card
  if (url->get_scheme() != "https") return "refuse: scheme " + url->get_scheme();  // snippet: card
  // An IP address isn't a name on the list, however it's written. Each
  // kind is one object, so == works.
  if (url->get_hostKind() != HostKind::domain) {  // snippet: card
    return "refuse: " + url->get_hostKind()->toString() + " host " + url->get_hostname();  // snippet: card
  }  // snippet: card
  if (!allowed.count(url->get_hostname())) return "refuse: host " + url->get_hostname();  // snippet: card
  // With libcurl: curl_easy_setopt(curl, CURLOPT_URL, url->get_href().c_str()),
  // never input, and leave CURLOPT_FOLLOWLOCATION off, or check each
  // redirect the same way. A hostname doesn't say where DNS sends it.
  return "fetch " + url->get_href();  // snippet: card
}  // snippet: card

int main() {
  // Sets up Hrefine. Call it once before anything else.
  hrefine::global_init_init();

  std::cout << "# Hrefine tour\n";

  section("1. Parsing and reading parts");

  // A Url comes as a shared_ptr, with a getter for each part.
  std::string text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";  // snippet: hero
  auto url = parseUrl(text);  // snippet: hero, parts
  std::cout << "input: " << text << "\n";
  std::cout << "href: " << url->get_href() << "\n";  // snippet: parts
  std::cout << "origin: " << url->get_origin() << "\n";  // snippet: parts
  std::cout << "protocol: " << url->get_protocol() << "\n";  // snippet: parts
  std::cout << "username: " << url->get_username() << "\n";  // snippet: parts
  std::cout << "password: " << url->get_password() << "\n";  // snippet: parts
  std::cout << "host: " << url->get_host() << "\n";  // snippet: parts
  std::cout << "hostname: " << url->get_hostname() << "\n";  // snippet: parts, hero
  std::cout << "port: " << url->get_port() << "\n";  // snippet: parts
  std::cout << "pathname: " << url->get_pathname() << "\n";  // snippet: parts
  std::cout << "search: " << url->get_search() << "\n";  // snippet: parts
  std::cout << "hash: " << url->get_hash() << "\n";  // snippet: parts
  // Typed parts, beside the standard's strings. A missing value is Temper's
  // NullableParam, with has_value and value.
  std::cout << "scheme: " << url->get_scheme() << "\n";  // snippet: parts
  std::cout << "port number: " << url->get_portNumber().value << "\n";  // snippet: parts
  std::cout << "host kind: " << url->get_hostKind()->toString() << "\n";  // snippet: parts
  // The standard's parts are strings, as in JavaScript's URL, so no port is
  // "", and get_portNumber() has no value.
  auto plain = parseUrl("HTTPS://example.com:443");
  auto portNumber = plain->get_portNumber();
  std::cout << "default port: " << plain->get_href() << ", port \"" << plain->get_port() << "\", port number "
            << (portNumber.has_value ? std::to_string(portNumber.value) : "none") << "\n";

  section("2. Relative URLs");

  // Parse the base once, then resolve against it.
  auto guide = parseUrl("https://example.com/docs/guide/intro.html");  // snippet: base
  std::cout << "base: " << guide->get_href() << "\n";
  for (std::string relative : {"setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"}) {  // snippet: base
    std::cout << relative << " -> " << guide->resolve(relative)->get_href() << "\n";  // snippet: base
  }  // snippet: base
  // Or give the base as a string, parsed on each call.
  std::cout << "with a string base: " << parseUrl("faq.html", guide->get_href())->get_href() << "\n";  // snippet: base

  section("3. Failures");

  // checkUrl says why input isn't a URL, with the standard's names for
  // what's wrong and where, counted in code points from 0. The last error is
  // why it failed. Some errors don't stop a URL from parsing, as browsers
  // accept it.
  for (std::string input : {"https://exa mple.com", "http://[::1", "https://example.com:99999", "setup.html",
                            "https:example.com/a b"}) {
    auto check = checkUrl(input);  // snippet: errors
    std::string errors;  // snippet: errors
    for (auto const &error : *check->get_errors()) {  // snippet: errors
      errors += (errors.empty() ? "" : ", ") + error->toString();  // snippet: errors
    }  // snippet: errors
    auto parsed = check->get_url();  // snippet: errors
    std::cout << input << ": " << (parsed ? parsed->get_href() : "not a URL") << " (" << errors << ")\n";  // snippet: errors
  }
  // Url::parse gives nullptr where parseUrl throws, and Url::canParse says
  // only whether it would parse, as in JavaScript.
  std::cout << "nullable parse: " << (Url::parse("setup.html") ? "a URL" : "nothing") << "\n";
  std::cout << "can parse: " << (Url::canParse("setup.html") ? "true" : "false") << "\n";
  // parseUrl throws temper::core::TemperBubble, whose what() is only
  // "bubble", so checkUrl says why.
  try {
    parseUrl("setup.html");
    std::cout << "throwing parse: parsed\n";
  } catch (TemperBubble const &) {
    std::cout << "throwing parse: throws\n";
  }

  section("4. International domain names");

  // Hosts go to ASCII, as browsers send them. Strings are UTF-8.
  auto idn = parseUrl("https://Bücher.example/straße?q=ü");
  std::cout << "hostname: " << idn->get_hostname() << "\n";
  std::cout << "href: " << idn->get_href() << "\n";
  for (std::string domain : {"Bücher.Example", "faß.de", "☕.example", "xn--tešla"}) {
    try {
      // Converted before printing, so a failure prints nothing.
      std::string ascii = domainToAscii(domain);
      std::cout << "to ASCII: " << domain << " -> " << ascii << "\n";
    } catch (TemperBubble const &) {
      std::cout << "to ASCII: " << domain << " fails\n";
    }
  }
  // And back to Unicode, for showing; it never fails. Decide on the ASCII
  // form: the second is a Cyrillic а, not apple.com.
  for (std::string domain : {"xn--bcher-kva.example", "xn--pple-43d.com"}) {
    std::cout << "to Unicode: " << domain << " -> " << domainToUnicode(domain) << "\n";
  }

  section("5. Serializing with href");

  // href is the standard's canonical form, which other parsers read alike.
  for (std::string input : {"HTTP://EXAMPLE.COM/a/./b/../c", "https:\\\\example.com\\path", "http://0x7f.1/",
                            "https://[0:0::1]:443/", "https://example.com/a b?c d#e f",
                            " https://exa\tmple.com/\n"}) {
    std::cout << shown(input) << " -> " << parseUrl(input)->get_href() << "\n";
  }
  // toString() is href too, but there's no operator<<.
  std::cout << "as a string: " << url->toString() << "\n";
  // eq compares hrefs; == compares pointers.
  std::cout << "same URL: "
            << (parseUrl("HTTP://EXAMPLE.COM/a/./b/../c")->eq(parseUrl("http://example.com/a/c")) ? "true" : "false")
            << "\n";
  // get_strictHref() also escapes what RFC 3986 parsers reject, for those
  // that follow it strictly.
  auto strict = parseUrl("https://example.com/a|b/%zz?q={x}#c^d");  // snippet: proof
  std::cout << "strict: " << strict->get_href() << " -> " << strict->get_strictHref() << "\n";  // snippet: proof

  section("6. Using it safely");

  // Decide with Hrefine, then hand on href, never the original string.
  // libcurl, Boost.URL, and cpp-httplib parse URLs their own way, mostly
  // after RFC 3986.
  for (std::string input : {"https://api.example.com/v1/items", "https://example.com\\@evil.example/",
                            "https://evil.example#@example.com", "https://0x7f.1/admin", "http://example.com/",
                            "javascript:alert(1)", "https://exa mple.com"}) {
    std::cout << input << ": " << check(input) << "\n";
  }

  // Check hosts from configuration with parseHost, which domainToAscii isn't
  // for: it passes all three.
  for (std::string input : {"example.com", "0x7f.1", "exa mple.com"}) {
    try {
      auto host = parseHost(input);
      std::cout << "host " << input << ": " << host->get_kind()->toString() << " " << host->get_serialized() << "\n";
    } catch (TemperBubble const &) {
      std::cout << "host " << input << ": not a host\n";
    }
  }

  // A server redirecting to a `next` parameter: resolve it against your own
  // site, and redirect only to the same origin. In cpp-httplib:
  // res.set_redirect(next->get_href()).
  auto site = parseUrl("https://example.com/");
  for (std::string target : {"/account", "//evil.example/", "/\\evil.example", "//[::1"}) {
    auto next = site->tryResolve(target);
    if (next && next->sameOrigin(site)) {
      std::cout << "next=" << target << ": redirect to " << next->get_href() << "\n";
    } else {
      std::cout << "next=" << target << ": refuse, " << (next ? next->get_origin() : "not a URL") << "\n";
    }
  }

  section("7. Changing parts");

  // The standard's setters, as methods that give a new URL, so a URL that
  // passed a check can't change after. A value that can't be set is ignored,
  // as in JavaScript.
  auto page = parseUrl("https://example.com/docs?lang=en&q=a+b");
  std::cout << "page: " << page->get_href() << "\n";
  std::cout << "with host: " << page->withHost("example.org:8443")->get_href() << "\n";
  std::cout << "with pathname and hash: " << page->withPathname("/a b")->withHash("top")->get_href() << "\n";
  std::cout << "with protocol: " << page->withProtocol("http")->get_href() << "\n";
  std::cout << "port \"http\", ignored: " << page->withPort("http")->get_href() << "\n";
  std::cout << "with port number: " << page->withPortNumber(8443)->get_href() << "\n";
  std::cout << "unchanged: " << page->get_href() << "\n";
  // Search parameters: a copy of the query, changed in place, then put back.
  auto params = page->get_searchParams();
  std::cout << "q: " << params->get("q").value << "\n";
  params->append("lang", "fr");
  params->set("q", "café & more");
  params->remove("missing");
  params->sort();
  // Lists come as shared pointers; keep each alive while looping over it.
  auto langList = params->getAll("lang");
  std::string langs;
  for (auto const &lang : *langList) {
    langs += (langs.empty() ? "" : ", ") + lang;
  }
  std::cout << "lang: " << langs << "\n";
  auto entries = params->entries();
  for (auto const &entry : *entries) {
    std::cout << entry->key << " = " << entry->value << "\n";
  }
  std::cout << "with search params: " << page->withSearchParams(params)->get_href() << "\n";
  // Or from pairs of names and values.
  using StringPair = temper::core::Pair<std::string, std::string>;
  auto pairs = std::make_shared<std::vector<std::shared_ptr<StringPair>>>();
  pairs->push_back(std::make_shared<StringPair>("q", "a b"));
  pairs->push_back(std::make_shared<StringPair>("page", "2"));
  std::cout << "from pairs: " << UrlSearchParams::fromEntries(pairs)->toString() << "\n";

  section("8. Test cases");

  // Each of web-platform-tests' URL cases gives an input, a base, and the
  // href it must parse to, or "" where parsing must fail. Hrefine's tests
  // run them all, checking every part, and so does the site, in the browser.
  std::string cases[][3] = {
      {"http:\\\\foo.com\\", "http://example.org/foo/bar", "http://foo.com/"},
      {"../aaa/test.txt", "http://www.example.com/test", "http://www.example.com/aaa/test.txt"},
      {"http://999999999", "http://other.com/", "http://59.154.201.255/"},
      {"http://192.168.0.257", "http://other.com/", ""},
  };
  for (auto const &[input, base, href] : cases) {  // snippet: scoreboard
    auto url = Url::parse(input, base);  // snippet: scoreboard
    std::string got = url ? url->get_href() : "";  // snippet: scoreboard
    std::cout << input << " against " << base << ": " << (got == href ? "pass" : "fail") << "\n";  // snippet: scoreboard
  }  // snippet: scoreboard
}
