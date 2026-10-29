// A tour of Hrefine, from C#.
//
// The same tour exists for each language Hrefine supports, and they all print
// the same text. See demos/README.md for how to run them.

using System;
using System.Collections.Generic;
using Hrefine;
using static Hrefine.HrefineGlobal;

static void Section(string title)
{
    Console.WriteLine();
    Console.WriteLine($"## {title}");
}

// Tabs and newlines made visible.
static string Shown(string text) => text.Replace("\t", "\\t").Replace("\n", "\\n");

// The URL, or null if it isn't one.
static Url? TryParse(string text, string? @base = null)
{
    try
    {
        return ParseUrl(text, @base);
    }
    catch (Exception)
    {
        return null;
    }
}

Console.WriteLine("# Hrefine tour");

Section("1. Parsing and reading parts");

var text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";
var url = ParseUrl(text);
Console.WriteLine($"input: {text}");
Console.WriteLine($"href: {url.Href}");
Console.WriteLine($"origin: {url.Origin}");
Console.WriteLine($"protocol: {url.Protocol}");
Console.WriteLine($"username: {url.Username}");
Console.WriteLine($"password: {url.Password}");
Console.WriteLine($"host: {url.Host}");
Console.WriteLine($"hostname: {url.Hostname}");
Console.WriteLine($"port: {url.Port}");
Console.WriteLine($"pathname: {url.Pathname}");
Console.WriteLine($"search: {url.Search}");
Console.WriteLine($"hash: {url.Hash}");
// Every part is a string, as in JavaScript's URL, so no port is "".
var plain = ParseUrl("HTTPS://example.com:443");
Console.WriteLine($"default port: {plain.Href}, port \"{plain.Port}\"");

Section("2. Relative URLs");

var baseUrl = "https://example.com/docs/guide/intro.html";
Console.WriteLine($"base: {baseUrl}");
foreach (var relative in new[] { "setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js" })
{
    // The base is a string, parsed again on each call.
    Console.WriteLine($"{relative} -> {ParseUrl(relative, baseUrl).Href}");
}
// Url.Parse is the same as ParseUrl, as in JavaScript's URL.parse.
Console.WriteLine($"Url.parse: {Url.Parse("setup.html", baseUrl).Href}");
// A Url can't be a base itself, so pass its Href.
var guide = ParseUrl(baseUrl);
Console.WriteLine($"from a Url: {ParseUrl("faq.html", guide.Href).Href}");

Section("3. Failures");

// Input that isn't a URL throws a plain System.Exception, so it says nothing
// of why, and catching it catches everything else too. (Uri throws
// UriFormatException, and has TryCreate.)
var cases = new (string Input, string? Against)[]
{
    ("https://exa mple.com", null),
    ("http://[::1", null),
    ("https://example.com:99999", null),
    ("setup.html", null),
    ("setup.html", "not a base"),
};
foreach (var (input, against) in cases)
{
    var label = against != null ? $"{input} against {against}" : $"{input}, without a base";
    try
    {
        ParseUrl(input, against);
        Console.WriteLine($"{label}: parsed");
    }
    catch (Exception)
    {
        Console.WriteLine($"{label}: not a URL");
    }
}
// Or wrap it, as TryParse above does, for null in place of failure.
Console.WriteLine($"as an optional: {(TryParse("https://exa mple.com") is null ? "nothing" : "a URL")}");

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

Section("6. Using it safely");

// Decide with Hrefine, then hand on Href, never the original string.
// HttpClient and ASP.NET read URLs with System.Uri, which follows RFC 3986
// and its own rules, not the URL Standard.
var allowed = new HashSet<string> { "example.com", "api.example.com" };

// The URL to fetch, or why not.
string Check(string input)
{
    var url = TryParse(input);
    if (url is null) return "refuse: not a URL";
    if (url.Protocol != "https:") return $"refuse: protocol {url.Protocol}";
    if (!allowed.Contains(url.Hostname)) return $"refuse: host {url.Hostname}";
    // await client.GetAsync(url.Href), never input, with a client whose
    // handler has AllowAutoRedirect = false, or check each redirect the
    // same way. A hostname doesn't say where DNS sends it.
    return $"fetch {url.Href}";
}

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

// A server redirecting to a `next` parameter: resolve it against your own
// origin, and redirect only if the origin stays the same. In ASP.NET Core:
// return Redirect(url.Href).
var site = "https://example.com/";
foreach (var target in new[] { "/account", "//evil.example/", "/\\evil.example" })
{
    var next = TryParse(target, site);
    if (next is not null && next.Origin == "https://example.com")
    {
        Console.WriteLine($"next={target}: redirect to {next.Href}");
    }
    else
    {
        Console.WriteLine($"next={target}: refuse, {next?.Origin ?? "not a URL"}");
    }
}
