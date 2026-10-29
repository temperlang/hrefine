// A tour of Hrefine, from C++.
//
// The same tour exists for each language Hrefine supports, and they all print
// the same text. See demos/README.md for how to run them.

#include <iostream>
#include <memory>
#include <set>
#include <string>

#include "hrefine/init.hpp"

using hrefine::Url;
using hrefine::domainToAscii;
using hrefine::domainToUnicode;
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

// The URL, or null if it isn't one. The optional base is Temper's own
// NullableParam, which takes a string or nullptr.
std::shared_ptr<Url> tryParse(std::string const &text,
                              temper::core::NullableParam<std::string> base = nullptr) {
  try {
    return parseUrl(text, base);
  } catch (TemperBubble const &) {
    return nullptr;
  }
}

const std::set<std::string> allowed = {"example.com", "api.example.com"};

// The URL to fetch, or why not.
std::string check(std::string const &input) {
  auto url = tryParse(input);
  if (!url) return "refuse: not a URL";
  if (url->get_protocol() != "https:") return "refuse: protocol " + url->get_protocol();
  if (!allowed.count(url->get_hostname())) return "refuse: host " + url->get_hostname();
  // With libcurl: curl_easy_setopt(curl, CURLOPT_URL, url->get_href().c_str()),
  // never input, and leave CURLOPT_FOLLOWLOCATION off, or check each
  // redirect the same way. A hostname doesn't say where DNS sends it.
  return "fetch " + url->get_href();
}

int main() {
  // Sets up Hrefine. Call it once before anything else.
  hrefine::global_init_init();

  std::cout << "# Hrefine tour\n";

  section("1. Parsing and reading parts");

  // A Url comes as a shared_ptr, with a getter for each part.
  std::string text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";
  auto url = parseUrl(text);
  std::cout << "input: " << text << "\n";
  std::cout << "href: " << url->get_href() << "\n";
  std::cout << "origin: " << url->get_origin() << "\n";
  std::cout << "protocol: " << url->get_protocol() << "\n";
  std::cout << "username: " << url->get_username() << "\n";
  std::cout << "password: " << url->get_password() << "\n";
  std::cout << "host: " << url->get_host() << "\n";
  std::cout << "hostname: " << url->get_hostname() << "\n";
  std::cout << "port: " << url->get_port() << "\n";
  std::cout << "pathname: " << url->get_pathname() << "\n";
  std::cout << "search: " << url->get_search() << "\n";
  std::cout << "hash: " << url->get_hash() << "\n";
  // Every part is a string, as in JavaScript's URL, so no port is "".
  auto plain = parseUrl("HTTPS://example.com:443");
  std::cout << "default port: " << plain->get_href() << ", port \"" << plain->get_port() << "\"\n";

  section("2. Relative URLs");

  std::string base = "https://example.com/docs/guide/intro.html";
  std::cout << "base: " << base << "\n";
  for (std::string relative : {"setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"}) {
    // The base is a string, parsed again on each call.
    std::cout << relative << " -> " << parseUrl(relative, base)->get_href() << "\n";
  }
  // Url::parse is the same as parseUrl, as in JavaScript's URL.parse.
  std::cout << "Url.parse: " << Url::parse("setup.html", base)->get_href() << "\n";
  // A Url can't be a base itself, so pass its href.
  auto guide = parseUrl(base);
  std::cout << "from a Url: " << parseUrl("faq.html", guide->get_href())->get_href() << "\n";

  section("3. Failures");

  // Input that isn't a URL throws temper::core::TemperBubble, whose what()
  // is only "bubble", so it says nothing of why.
  struct Case {
    std::string input;
    const char *against;
  };
  for (Case const &c : {Case{"https://exa mple.com", nullptr}, Case{"http://[::1", nullptr},
                        Case{"https://example.com:99999", nullptr}, Case{"setup.html", nullptr},
                        Case{"setup.html", "not a base"}}) {
    std::string label = c.against ? c.input + " against " + c.against : c.input + ", without a base";
    try {
      if (c.against) {
        parseUrl(c.input, std::string(c.against));
      } else {
        parseUrl(c.input);
      }
      std::cout << label << ": parsed\n";
    } catch (TemperBubble const &) {
      std::cout << label << ": not a URL\n";
    }
  }
  // Or wrap it, as tryParse above does, for null in place of failure.
  std::cout << "as an optional: " << (tryParse("https://exa mple.com") ? "a URL" : "nothing") << "\n";

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

  section("6. Using it safely");

  // Decide with Hrefine, then hand on href, never the original string.
  // libcurl, Boost.URL, and cpp-httplib parse URLs their own way, mostly
  // after RFC 3986.
  for (std::string input : {"https://api.example.com/v1/items", "https://example.com\\@evil.example/",
                            "https://evil.example#@example.com", "https://0x7f.1/admin", "http://example.com/",
                            "javascript:alert(1)", "https://exa mple.com"}) {
    std::cout << input << ": " << check(input) << "\n";
  }

  // A server redirecting to a `next` parameter: resolve it against your own
  // origin, and redirect only if the origin stays the same. In
  // cpp-httplib: res.set_redirect(next->get_href()).
  std::string site = "https://example.com/";
  for (std::string target : {"/account", "//evil.example/", "/\\evil.example"}) {
    auto next = tryParse(target, site);
    if (next && next->get_origin() == "https://example.com") {
      std::cout << "next=" << target << ": redirect to " << next->get_href() << "\n";
    } else {
      std::cout << "next=" << target << ": refuse, " << (next ? next->get_origin() : "not a URL") << "\n";
    }
  }
}
