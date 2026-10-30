// A tour of Hrefine, from C#.
//
// The same tour exists for each language Hrefine supports, and they all print
// the same text. See demos/README.md for how to run them.

using System;
using System.Collections.Generic;
using System.Linq;
using Hrefine;
using static Hrefine.HrefineGlobal;

static void Section(string title)
{
    Console.WriteLine();
    Console.WriteLine($"## {title}");
}

// Tabs and newlines made visible.
static string Shown(string text) => text.Replace("\t", "\\t").Replace("\n", "\\n");

Console.WriteLine("# Hrefine tour");

Section("1. Parsing and reading parts");

var text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";  // snippet: hero
var url = ParseUrl(text);  // snippet: hero, parts
Console.WriteLine($"input: {text}");
Console.WriteLine($"href: {url.Href}");  // snippet: parts
Console.WriteLine($"origin: {url.Origin}");  // snippet: parts
Console.WriteLine($"protocol: {url.Protocol}");  // snippet: parts
Console.WriteLine($"username: {url.Username}");  // snippet: parts
Console.WriteLine($"password: {url.Password}");  // snippet: parts
Console.WriteLine($"host: {url.Host}");  // snippet: parts
Console.WriteLine($"hostname: {url.Hostname}");  // snippet: parts, hero
Console.WriteLine($"port: {url.Port}");  // snippet: parts
Console.WriteLine($"pathname: {url.Pathname}");  // snippet: parts
Console.WriteLine($"search: {url.Search}");  // snippet: parts
Console.WriteLine($"hash: {url.Hash}");  // snippet: parts
// Typed parts, beside the standard's strings.
Console.WriteLine($"scheme: {url.Scheme}");  // snippet: parts
Console.WriteLine($"port number: {url.PortNumber}");  // snippet: parts
Console.WriteLine($"host kind: {url.HostKind!.ToString()}");  // snippet: parts
// The standard's parts are strings, as in JavaScript's URL, so no port is
// "", and PortNumber is null.
var plain = ParseUrl("HTTPS://example.com:443");
Console.WriteLine($"default port: {plain.Href}, port \"{plain.Port}\", port number {plain.PortNumber?.ToString() ?? "none"}");

Section("2. Relative URLs");

// Parse the base once, then resolve against it.
var guide = ParseUrl("https://example.com/docs/guide/intro.html");  // snippet: base
Console.WriteLine($"base: {guide.Href}");
foreach (var relative in new[] { "setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js" })  // snippet: base
{  // snippet: base
    Console.WriteLine($"{relative} -> {guide.Resolve(relative).Href}");  // snippet: base
}  // snippet: base
// Or give the base as a string, parsed on each call.
Console.WriteLine($"with a string base: {ParseUrl("faq.html", guide.Href).Href}");  // snippet: base

Section("3. Failures");

// CheckUrl says why input isn't a URL, with the standard's names for
// what's wrong and where, counted in code points from 0. The last error is
// why it failed. Some errors don't stop a URL from parsing, as browsers
// accept it.
foreach (var input in new[] {
    "https://exa mple.com",
    "http://[::1",
    "https://example.com:99999",
    "setup.html",
    "https:example.com/a b",
})
{
    var check = CheckUrl(input);  // snippet: errors
    var errors = string.Join(", ", check.Errors.Select(error => error.ToString()));  // snippet: errors
    Console.WriteLine($"{input}: {check.Url?.Href ?? "not a URL"} ({errors})");  // snippet: errors
}
// Url.Parse gives null where ParseUrl throws, and Url.CanParse says only
// whether it would parse, as in JavaScript.
Console.WriteLine($"nullable parse: {(Url.Parse("setup.html") is null ? "nothing" : "a URL")}");
Console.WriteLine($"can parse: {(Url.CanParse("setup.html") ? "true" : "false")}");
// ParseUrl throws a plain System.Exception, so catching it catches
// everything else too, and CheckUrl says why. (Uri throws
// UriFormatException, and has TryCreate.)
try
{
    ParseUrl("setup.html");
    Console.WriteLine("throwing parse: parsed");
}
catch (Exception)
{
    Console.WriteLine("throwing parse: throws");
}

Section("4. International domain names");

// Hosts go to ASCII, as browsers send them.
var idn = ParseUrl("https://Bücher.example/straße?q=ü");
Console.WriteLine($"hostname: {idn.Hostname}");
Console.WriteLine($"href: {idn.Href}");
foreach (var domain in new[] { "Bücher.Example", "faß.de", "☕.example", "xn--tešla" })
{
    try
    {
        Console.WriteLine($"to ASCII: {domain} -> {DomainToAscii(domain)}");
    }
    catch (Exception)
    {
        Console.WriteLine($"to ASCII: {domain} fails");
    }
}
// And back to Unicode, for showing; it never fails. Decide on the ASCII
// form: the second is a Cyrillic а, not apple.com.
foreach (var domain in new[] { "xn--bcher-kva.example", "xn--pple-43d.com" })
{
    Console.WriteLine($"to Unicode: {domain} -> {DomainToUnicode(domain)}");
}

Section("5. Serializing with href");

// Href is the standard's canonical form, which other parsers read alike.
foreach (var input in new[] {
    "HTTP://EXAMPLE.COM/a/./b/../c",
    "https:\\\\example.com\\path",
    "http://0x7f.1/",
    "https://[0:0::1]:443/",
    "https://example.com/a b?c d#e f",
    " https://exa\tmple.com/\n",
})
{
    Console.WriteLine($"{Shown(input)} -> {ParseUrl(input).Href}");
}
// url.ToString() is Href too, but it hides object.ToString rather than
// overriding it, so $"{url}" gives "Hrefine.Url".
Console.WriteLine($"as a string: {url.ToString()}");
// Eq compares hrefs; == compares objects.
Console.WriteLine($"same URL: {(ParseUrl("HTTP://EXAMPLE.COM/a/./b/../c").Eq(ParseUrl("http://example.com/a/c")) ? "true" : "false")}");
// StrictHref also escapes what RFC 3986 parsers reject, for those that
// follow it strictly.
var strict = ParseUrl("https://example.com/a|b/%zz?q={x}#c^d");  // snippet: proof
Console.WriteLine($"strict: {strict.Href} -> {strict.StrictHref}");  // snippet: proof

Section("6. Using it safely");

// Decide with Hrefine, then hand on Href, never the original string.
// HttpClient and ASP.NET read URLs with System.Uri, which follows RFC 3986
// and its own rules, not the URL Standard.
var allowed = new HashSet<string> { "example.com", "api.example.com" };

// The URL to fetch, or why not.
string Check(string input)  // snippet: card
{  // snippet: card
    var url = Url.Parse(input);  // snippet: card
    if (url is null) return "refuse: not a URL";  // snippet: card
    if (url.Scheme != "https") return $"refuse: scheme {url.Scheme}";  // snippet: card
    // An IP address isn't a name on the list, however it's written. Each
    // kind is one object, so == works.
    if (url.HostKind != HostKind.Domain) return $"refuse: {url.HostKind!.ToString()} host {url.Hostname}";  // snippet: card
    if (!allowed.Contains(url.Hostname)) return $"refuse: host {url.Hostname}";  // snippet: card
    // await client.GetAsync(url.Href), never input, with a client whose
    // handler has AllowAutoRedirect = false, or check each redirect the
    // same way. A hostname doesn't say where DNS sends it.
    return $"fetch {url.Href}";  // snippet: card
}  // snippet: card

foreach (var input in new[] {
    "https://api.example.com/v1/items",
    "https://example.com\\@evil.example/",
    "https://evil.example#@example.com",
    "https://0x7f.1/admin",
    "http://example.com/",
    "javascript:alert(1)",
    "https://exa mple.com",
})
{
    Console.WriteLine($"{input}: {Check(input)}");
}

// Check hosts from configuration with ParseHost, which DomainToAscii isn't
// for: it passes all three.
foreach (var input in new[] { "example.com", "0x7f.1", "exa mple.com" })
{
    try
    {
        var host = ParseHost(input);
        Console.WriteLine($"host {input}: {host.Kind.ToString()} {host.Serialized}");
    }
    catch (Exception)
    {
        Console.WriteLine($"host {input}: not a host");
    }
}

// A server redirecting to a `next` parameter: resolve it against your own
// site, and redirect only to the same origin. In ASP.NET Core:
// return Redirect(url.Href).
var site = ParseUrl("https://example.com/");
foreach (var target in new[] { "/account", "//evil.example/", "/\\evil.example", "//[::1" })
{
    var next = site.TryResolve(target);
    if (next is not null && next.SameOrigin(site))
    {
        Console.WriteLine($"next={target}: redirect to {next.Href}");
    }
    else
    {
        Console.WriteLine($"next={target}: refuse, {next?.Origin ?? "not a URL"}");
    }
}

Section("7. Changing parts");

// The standard's setters, as methods that give a new URL, so a URL that
// passed a check can't change after. A value that can't be set is ignored,
// as in JavaScript.
var page = ParseUrl("https://example.com/docs?lang=en&q=a+b");
Console.WriteLine($"page: {page.Href}");
Console.WriteLine($"with host: {page.WithHost("example.org:8443").Href}");
Console.WriteLine($"with pathname and hash: {page.WithPathname("/a b").WithHash("top").Href}");
Console.WriteLine($"with protocol: {page.WithProtocol("http").Href}");
Console.WriteLine($"port \"http\", ignored: {page.WithPort("http").Href}");
Console.WriteLine($"with port number: {page.WithPortNumber(8443).Href}");
Console.WriteLine($"unchanged: {page.Href}");
// Search parameters: a copy of the query, changed in place, then put back.
var searchParams = page.SearchParams;
Console.WriteLine($"q: {searchParams.Get("q")}");
searchParams.Append("lang", "fr");
searchParams.Set("q", "café & more");
searchParams.Remove("missing");
searchParams.Sort();
Console.WriteLine($"lang: {string.Join(", ", searchParams.GetAll("lang"))}");
foreach (var entry in searchParams.Entries())
{
    Console.WriteLine($"{entry.Key} = {entry.Value}");
}
Console.WriteLine($"with search params: {page.WithSearchParams(searchParams).Href}");
// Or from pairs of names and values.
var fromPairs = UrlSearchParams.FromEntries(new List<KeyValuePair<string, string>> { new("q", "a b"), new("page", "2") });
Console.WriteLine($"from pairs: {fromPairs.ToString()}");

Section("8. Test cases");

// Each of web-platform-tests' URL cases gives an input, a base, and the
// href it must parse to, or "" where parsing must fail. Hrefine's tests run
// them all, checking every part, and so does the site, in the browser.
var cases = new[] {
    ("http:\\\\foo.com\\", "http://example.org/foo/bar", "http://foo.com/"),
    ("../aaa/test.txt", "http://www.example.com/test", "http://www.example.com/aaa/test.txt"),
    ("http://999999999", "http://other.com/", "http://59.154.201.255/"),
    ("http://192.168.0.257", "http://other.com/", ""),
};
foreach (var (input, baseUrl, href) in cases)  // snippet: scoreboard
{  // snippet: scoreboard
    var parsed = Url.Parse(input, baseUrl);  // snippet: scoreboard
    var got = parsed?.Href ?? "";  // snippet: scoreboard
    Console.WriteLine($"{input} against {baseUrl}: {(got == href ? "pass" : "fail")}");  // snippet: scoreboard
}  // snippet: scoreboard

Section("9. Policies");

// A policy does the checks of section 6 in one call, on the parsed URL. Build
// it once, a rule at a time, and use it for every URL: https only, no
// credentials, no private, loopback, or other special addresses or names,
// and example.com or its subdomains.
var policy = UrlPolicy.Any.WithSchemes(new[] { "https" }).WithCredentials(false)  // snippet: policy
    .WithSpecialHosts(false).WithHosts(new[] { "example.com" }, true);  // snippet: policy
var inputs = new[] {
    "https://api.example.com/v1/items",
    "http://example.com/",
    "https://example.com@evil.example/",
    "https://127.1/",
    "https://[::ffff:127.0.0.1]/",
    "https://localhost./",
    "https://exаmple.com/",
};
foreach (var input in inputs)  // snippet: policy
{  // snippet: policy
    var result = policy.Check(input);  // snippet: policy
    if (result.Url is Url fetched)  // snippet: policy
    {  // snippet: policy
        Console.WriteLine($"{input}: fetch {fetched.Href}");  // snippet: policy
    }  // snippet: policy
    else  // snippet: policy
    {  // snippet: policy
        Console.WriteLine($"{input}: refuse, {result.ToString()}");  // snippet: policy
    }  // snippet: policy
}  // snippet: policy

// Strict mode refuses what the standard accepts but notes as an error, as
// cautious parsers do: backslashes, tabs, odd IPv4 forms, and the like.
// WithStrict(true) adds it to a policy.
foreach (var input in new[] { "https://example.com/a b", "http://0x7f.1/", "https://example.com\\a", " https://example.com/" })
{
    var check = CheckUrl(input);
    if (check.StrictUrl is Url strictUrl)
    {
        Console.WriteLine($"strict {Shown(input)}: {strictUrl.Href}");
    }
    else
    {
        var errors = string.Join(", ", check.StrictErrors.Select(error => error.ToString()));
        Console.WriteLine($"strict {Shown(input)}: refuse, {errors}");
    }
}

// Redirect targets: WithPathOnly takes only a path, query, or fragment on
// the base, never another host, however it's written.
var redirects = UrlPolicy.Any.WithBase(site).WithPathOnly(true);
foreach (var target in new[] { "/account?tab=2", "//evil.example/", "/\\evil.example", "/\t/evil.example", "https://example.com/" })
{
    var result = redirects.Check(target);
    Console.WriteLine($"next={Shown(target)}: {(result.Url is Url next ? "redirect to " + next.Href : "refuse, " + result.ToString())}");
}

Section("10. Showing, comparing, and spans");

// To show people a URL, as browsers' address bars do: hosts in Unicode
// where browsers would show them (not look-alikes such as Cyrillic а in
// xn--pple-43d.com), and escapes of non-ASCII text decoded. Never for
// security decisions, nor for handing on: use Href for those.
var display = UrlDisplay.Full.WithCredentials(false).WithRootSlash(false);  // snippet: display
foreach (var input in new[] {  // snippet: display
    "https://user@xn--bcher-kva.example/caf%C3%A9?q=%E6%97%A5%E6%9C%AC",  // snippet: display
    "https://xn--pple-43d.com/",  // snippet: display
})  // snippet: display
{  // snippet: display
    Console.WriteLine($"display: {display.Format(ParseUrl(input))}");  // snippet: display
}  // snippet: display

// The same URL, the same but for the fragment, or the same origin. All
// compare canonical forms, so case and a default port don't matter.
var intro = ParseUrl("https://EXAMPLE.com:443/a/../guide#intro");
var setup = ParseUrl("https://example.com/guide#setup");
Console.WriteLine($"same URL: {(intro.Eq(setup) ? "true" : "false")}");
Console.WriteLine($"same document: {(intro.SameDocument(setup) ? "true" : "false")}");
Console.WriteLine($"same origin: {(intro.SameOrigin(ParseUrl("https://example.com/about")) ? "true" : "false")}");

// Where each part was written, for editors and linters: never for security
// decisions, which use source.Url. Spans count code points.
var source = ParseUrlSource(" https://EXAMPLE.com:443/a/../b?q=1");
Console.WriteLine($"href: {source.Url.Href}");
Console.WriteLine($"host as written: {source.HostSpan!.AsWritten}, at {source.HostSpan.ToString()}");
Console.WriteLine($"path as written: {source.PathSpan!.AsWritten}");
foreach (var error in CheckUrl("https://exa mple.com").Errors)
{
    Console.WriteLine($"{error.Name}: from {error.Position}, {error.Length} long");
}
