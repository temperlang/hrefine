"""A tour of Hrefine, from Python.

The same tour exists for each language Hrefine supports, and they all print
the same text. See demos/README.md for how to run them.
"""

from hrefine import Url, domain_to_ascii, domain_to_unicode, parse_url


def section(title):
    print()
    print(f"## {title}")


def shown(text):
    """Tabs and newlines made visible."""
    return text.replace("\t", "\\t").replace("\n", "\\n")


def try_parse(text, base=None):
    """The URL, or None if it isn't one."""
    try:
        return parse_url(text, base)
    except RuntimeError:
        return None


print("# Hrefine tour")

section("1. Parsing and reading parts")

text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top"
url = parse_url(text)
print(f"input: {text}")
print(f"href: {url.href}")
print(f"origin: {url.origin}")
print(f"protocol: {url.protocol}")
print(f"username: {url.username}")
print(f"password: {url.password}")
print(f"host: {url.host}")
print(f"hostname: {url.hostname}")
print(f"port: {url.port}")
print(f"pathname: {url.pathname}")
print(f"search: {url.search}")
print(f"hash: {url.hash}")
# Every part is a string, as in JavaScript's URL, so no port is "".
plain = parse_url("HTTPS://example.com:443")
print(f'default port: {plain.href}, port "{plain.port}"')

section("2. Relative URLs")

base = "https://example.com/docs/guide/intro.html"
print(f"base: {base}")
for relative in ["setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"]:
    # The base is a string, parsed again on each call.
    print(f"{relative} -> {parse_url(relative, base).href}")
# Url.parse is the same as parse_url, as in JavaScript's URL.parse.
print(f"Url.parse: {Url.parse('setup.html', base).href}")
# A Url can't be a base itself, so pass its href.
guide = parse_url(base)
print(f"from a Url: {parse_url('faq.html', guide.href).href}")

section("3. Failures")

# Input that isn't a URL raises RuntimeError, with no message, so it says
# nothing of why.
for text, against in [
    ("https://exa mple.com", None),
    ("http://[::1", None),
    ("https://example.com:99999", None),
    ("setup.html", None),
    ("setup.html", "not a base"),
]:
    label = f"{text} against {against}" if against else f"{text}, without a base"
    try:
        parse_url(text, against)
        print(f"{label}: parsed")
    except RuntimeError:
        print(f"{label}: not a URL")
# Or wrap it, as try_parse above does, for None in place of failure.
print(f"as an optional: {'nothing' if try_parse('https://exa mple.com') is None else 'a URL'}")

section("4. International domain names")

# Hosts go to ASCII, as browsers send them.
idn = parse_url("https://Bücher.example/straße?q=ü")
print(f"hostname: {idn.hostname}")
print(f"href: {idn.href}")
for domain in ["Bücher.Example", "faß.de", "☕.example", "xn--tešla"]:
    try:
        print(f"to ASCII: {domain} -> {domain_to_ascii(domain)}")
    except RuntimeError:
        print(f"to ASCII: {domain} fails")
# And back to Unicode, for showing; it never fails. Decide on the ASCII
# form: the second is a Cyrillic а, not apple.com.
for domain in ["xn--bcher-kva.example", "xn--pple-43d.com"]:
    print(f"to Unicode: {domain} -> {domain_to_unicode(domain)}")

section("5. Serializing with href")

# href is the standard's canonical form, which other parsers read alike.
for text in [
    "HTTP://EXAMPLE.COM/a/./b/../c",
    "https:\\\\example.com\\path",
    "http://0x7f.1/",
    "https://[0:0::1]:443/",
    "https://example.com/a b?c d#e f",
    " https://exa\tmple.com/\n",
]:
    print(f"{shown(text)} -> {parse_url(text).href}")
# to_string() is href too, but str() isn't.
print(f"as a string: {url.to_string()}")

section("6. Using it safely")

# Decide with Hrefine, then hand on href, never the original string.
# urllib, requests, and httpx parse URLs their own way: urllib reads the
# host of the second URL below as evil.example, but of its href as
# example.com, as Hrefine does.
ALLOWED = {"example.com", "api.example.com"}


def check(text):
    """The URL to fetch, or why not."""
    url = try_parse(text)
    if url is None:
        return "refuse: not a URL"
    if url.protocol != "https:":
        return f"refuse: protocol {url.protocol}"
    if url.hostname not in ALLOWED:
        return f"refuse: host {url.hostname}"
    # requests.get(url.href) or httpx.get(url.href), never text. Turn off
    # redirects (allow_redirects=False, follow_redirects=False) or check
    # each hop the same way. A hostname doesn't say where DNS sends it.
    return f"fetch {url.href}"


for text in [
    "https://api.example.com/v1/items",
    "https://example.com\\@evil.example/",
    "https://evil.example#@example.com",
    "https://0x7f.1/admin",
    "http://example.com/",
    "javascript:alert(1)",
    "https://exa mple.com",
]:
    print(f"{text}: {check(text)}")

# A server redirecting to a `next` parameter: resolve it against your own
# origin, and redirect only if the origin stays the same. In Flask or
# Django: return redirect(url.href).
SITE = "https://example.com/"
for target in ["/account", "//evil.example/", "/\\evil.example"]:
    url = try_parse(target, SITE)
    if url is not None and url.origin == "https://example.com":
        print(f"next={target}: redirect to {url.href}")
    else:
        print(f"next={target}: refuse, {url.origin if url else 'not a URL'}")
