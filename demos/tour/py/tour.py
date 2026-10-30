"""A tour of Hrefine, from Python.

The same tour exists for each language Hrefine supports, and they all print
the same text. See demos/README.md for how to run them.
"""

from temper_core import Pair

from hrefine import (
    HostKind,
    Url,
    UrlPolicy,
    UrlSearchParams,
    check_url,
    domain_to_ascii,
    domain_to_unicode,
    parse_host,
    parse_url,
)


def section(title):
    print()
    print(f"## {title}")


def shown(text):
    """Tabs and newlines made visible."""
    return text.replace("\t", "\\t").replace("\n", "\\n")


print("# Hrefine tour")

section("1. Parsing and reading parts")

text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top"  # snippet: hero
url = parse_url(text)  # snippet: hero, parts
print(f"input: {text}")
print(f"href: {url.href}")  # snippet: parts
print(f"origin: {url.origin}")  # snippet: parts
print(f"protocol: {url.protocol}")  # snippet: parts
print(f"username: {url.username}")  # snippet: parts
print(f"password: {url.password}")  # snippet: parts
print(f"host: {url.host}")  # snippet: parts
print(f"hostname: {url.hostname}")  # snippet: hero, parts
print(f"port: {url.port}")  # snippet: parts
print(f"pathname: {url.pathname}")  # snippet: parts
print(f"search: {url.search}")  # snippet: parts
print(f"hash: {url.hash}")  # snippet: parts
# Typed parts, beside the standard's strings.
print(f"scheme: {url.scheme}")  # snippet: parts
print(f"port number: {url.port_number}")  # snippet: parts
print(f"host kind: {url.host_kind.to_string()}")  # snippet: parts
# The standard's parts are strings, as in JavaScript's URL, so no port is
# "", and port_number is None.
plain = parse_url("HTTPS://example.com:443")
print(f'default port: {plain.href}, port "{plain.port}", port number {plain.port_number or "none"}')

section("2. Relative URLs")

# Parse the base once, then resolve against it.
guide = parse_url("https://example.com/docs/guide/intro.html")  # snippet: base
print(f"base: {guide.href}")
for relative in ["setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"]:  # snippet: base
    print(f"{relative} -> {guide.resolve(relative).href}")  # snippet: base
# Or give the base as a string, parsed on each call.
print(f"with a string base: {parse_url('faq.html', guide.href).href}")  # snippet: base

section("3. Failures")

# check_url says why input isn't a URL, with the standard's names for
# what's wrong and where, counted in code points. The last error is why it
# failed. Some errors don't stop a URL from parsing, as browsers accept it.
for text in [
    "https://exa mple.com",
    "http://[::1",
    "https://example.com:99999",
    "setup.html",
    "https:example.com/a b",
]:
    check = check_url(text)  # snippet: errors
    errors = ", ".join(error.to_string() for error in check.errors)  # snippet: errors
    result = check.url.href if check.url else "not a URL"  # snippet: errors
    print(f"{text}: {result} ({errors})")  # snippet: errors
# Url.parse gives None where parse_url raises, and Url.can_parse says only
# whether it would parse, as in JavaScript.
print(f"nullable parse: {'nothing' if Url.parse('setup.html') is None else 'a URL'}")
print(f"can parse: {str(Url.can_parse('setup.html')).lower()}")
# parse_url raises RuntimeError, with no message, so check_url says why.
try:
    parse_url("setup.html")
    print("throwing parse: parsed")
except RuntimeError:
    print("throwing parse: throws")

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
# eq compares hrefs; == compares objects.
print(f"same URL: {str(parse_url('HTTP://EXAMPLE.COM/a/./b/../c').eq(parse_url('http://example.com/a/c'))).lower()}")
# strict_href also escapes what RFC 3986 parsers reject, for those that
# follow it strictly.
strict = parse_url("https://example.com/a|b/%zz?q={x}#c^d")  # snippet: proof
print(f"strict: {strict.href} -> {strict.strict_href}")  # snippet: proof

section("6. Using it safely")

# Decide with Hrefine, then hand on href, never the original string.
# urllib, requests, and httpx parse URLs their own way: urllib reads the
# host of the second URL below as evil.example, but of its href as
# example.com, as Hrefine does.
ALLOWED = {"example.com", "api.example.com"}


def check(text):  # snippet: card
    """The URL to fetch, or why not."""
    url = Url.parse(text)  # snippet: card
    if url is None:  # snippet: card
        return "refuse: not a URL"  # snippet: card
    if url.scheme != "https":  # snippet: card
        return f"refuse: scheme {url.scheme}"  # snippet: card
    # An IP address isn't a name on the list, however it's written.
    if url.host_kind != HostKind.domain:  # snippet: card
        return f"refuse: {url.host_kind.to_string()} host {url.hostname}"  # snippet: card
    if url.hostname not in ALLOWED:  # snippet: card
        return f"refuse: host {url.hostname}"  # snippet: card
    # requests.get(url.href) or httpx.get(url.href), never text. Turn off
    # redirects (allow_redirects=False, follow_redirects=False) or check
    # each hop the same way. A hostname doesn't say where DNS sends it.
    return f"fetch {url.href}"  # snippet: card


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

# Check hosts from configuration with parse_host, which domain_to_ascii
# isn't for: it passes all three.
for text in ["example.com", "0x7f.1", "exa mple.com"]:
    try:
        host = parse_host(text)
        print(f"host {text}: {host.kind.to_string()} {host.serialized}")
    except RuntimeError:
        print(f"host {text}: not a host")

# A server redirecting to a `next` parameter: resolve it against your own
# site, and redirect only to the same origin. In Flask or Django:
# return redirect(url.href).
site = parse_url("https://example.com/")
for target in ["/account", "//evil.example/", "/\\evil.example", "//[::1"]:
    url = site.try_resolve(target)
    if url is not None and url.same_origin(site):
        print(f"next={target}: redirect to {url.href}")
    else:
        print(f"next={target}: refuse, {url.origin if url else 'not a URL'}")

section("7. Changing parts")

# The standard's setters, as methods that give a new URL, so a URL that
# passed a check can't change after. A value that can't be set is ignored,
# as in JavaScript.
page = parse_url("https://example.com/docs?lang=en&q=a+b")
print(f"page: {page.href}")
print(f"with host: {page.with_host('example.org:8443').href}")
print(f"with pathname and hash: {page.with_pathname('/a b').with_hash('top').href}")
print(f"with protocol: {page.with_protocol('http').href}")
print(f'port "http", ignored: {page.with_port("http").href}')
print(f"with port number: {page.with_port_number(8443).href}")
print(f"unchanged: {page.href}")
# Search parameters: a copy of the query, changed in place, then put back.
params = page.search_params
print(f"q: {params.get('q')}")
params.append("lang", "fr")
params.set("q", "café & more")
params.remove("missing")
params.sort()
print(f"lang: {', '.join(params.get_all('lang'))}")
for entry in params.entries():
    print(f"{entry.key} = {entry.value}")
print(f"with search params: {page.with_search_params(params).href}")
# Or from pairs of names and values.
print(f"from pairs: {UrlSearchParams.from_entries([Pair('q', 'a b'), Pair('page', '2')]).to_string()}")

section("8. Test cases")

# Each of web-platform-tests' URL cases gives an input, a base, and the
# href it must parse to, or "" where parsing must fail. Hrefine's tests
# run them all, checking every part, and so does the site, in the browser.
cases = [
    ["http:\\\\foo.com\\", "http://example.org/foo/bar", "http://foo.com/"],
    ["../aaa/test.txt", "http://www.example.com/test", "http://www.example.com/aaa/test.txt"],
    ["http://999999999", "http://other.com/", "http://59.154.201.255/"],
    ["http://192.168.0.257", "http://other.com/", ""],
]
for text, base, href in cases:  # snippet: scoreboard
    url = Url.parse(text, base)  # snippet: scoreboard
    got = "" if url is None else url.href  # snippet: scoreboard
    print(f"{text} against {base}: {'pass' if got == href else 'fail'}")  # snippet: scoreboard

section("9. Policies")

# A policy does the checks of section 6 in one call, on the parsed URL. Build
# it once, a rule at a time, and use it for every URL: https only, no
# credentials, no private, loopback, or other special addresses or names,
# and example.com or its subdomains.
policy = (  # snippet: policy
    UrlPolicy.any.with_schemes(["https"]).with_credentials(False)  # snippet: policy
    .with_special_hosts(False).with_hosts(["example.com"], True)  # snippet: policy
)  # snippet: policy
inputs = [
    "https://api.example.com/v1/items",
    "http://example.com/",
    "https://example.com@evil.example/",
    "https://127.1/",
    "https://[::ffff:127.0.0.1]/",
    "https://localhost./",
    "https://ex\u0430mple.com/",
]
for text in inputs:  # snippet: policy
    result = policy.check(text)  # snippet: policy
    if result.url is not None:  # snippet: policy
        print(f"{text}: fetch {result.url.href}")  # snippet: policy
    else:  # snippet: policy
        print(f"{text}: refuse, {result.to_string()}")  # snippet: policy

# Strict mode refuses what the standard accepts but notes as an error, as
# cautious parsers do: backslashes, tabs, odd IPv4 forms, and the like.
# with_strict(True) adds it to a policy.
for text in ["https://example.com/a b", "http://0x7f.1/", "https://example.com\\a", " https://example.com/"]:
    check = check_url(text)
    strict = check.strict_url
    if strict is not None:
        print(f"strict {shown(text)}: {strict.href}")
    else:
        errors = ", ".join(error.to_string() for error in check.strict_errors)
        print(f"strict {shown(text)}: refuse, {errors}")

# Redirect targets: with_path_only takes only a path, query, or fragment on
# the base, never another host, however it's written.
redirects = UrlPolicy.any.with_base(site).with_path_only(True)
for target in ["/account?tab=2", "//evil.example/", "/\\evil.example", "/\t/evil.example", "https://example.com/"]:
    result = redirects.check(target)
    print(f"next={shown(target)}: {'redirect to ' + result.url.href if result.url is not None else 'refuse, ' + result.to_string()}")
