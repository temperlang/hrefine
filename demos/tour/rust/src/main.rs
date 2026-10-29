//! A tour of Hrefine, from Rust.
//!
//! The same tour exists for each language Hrefine supports, and they all
//! print the same text. See demos/README.md for how to run them.

use hrefine::{domain_to_ascii, domain_to_unicode, parse_url, Url};

/// No base. `None` alone can't say which string type it isn't.
const NO_BASE: Option<&str> = None;

fn section(title: &str) {
    println!();
    println!("## {title}");
}

/// Tabs and newlines made visible.
fn shown(text: &str) -> String {
    text.replace('\t', "\\t").replace('\n', "\\n")
}

/// Allowed hosts for fetching.
const ALLOWED: [&str; 2] = ["example.com", "api.example.com"];

/// The URL to fetch, or why not.
fn check(input: &str) -> String {
    let Ok(url) = parse_url(input, NO_BASE) else {
        return "refuse: not a URL".into();
    };
    if url.protocol().as_str() != "https:" {
        return format!("refuse: protocol {}", url.protocol());
    }
    if !ALLOWED.contains(&url.hostname().as_str()) {
        return format!("refuse: host {}", url.hostname());
    }
    // reqwest::get(url.href().as_str()), never input, with a client built
    // with .redirect(Policy::none()), or check each redirect the same way.
    // A hostname doesn't say where DNS sends it.
    format!("fetch {}", url.href())
}

fn main() {
    // Sets up Hrefine and Temper's runtime. Call it once before anything
    // else.
    hrefine::init(None).expect("hrefine::init");

    println!("# Hrefine tour");

    section("1. Parsing and reading parts");

    // Failure is an Err, so a URL known to be good can take expect.
    let text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";
    let url = parse_url(text, NO_BASE).expect("a URL");
    println!("input: {text}");
    // Each part is an Arc<String>.
    println!("href: {}", url.href());
    println!("origin: {}", url.origin());
    println!("protocol: {}", url.protocol());
    println!("username: {}", url.username());
    println!("password: {}", url.password());
    println!("host: {}", url.host());
    println!("hostname: {}", url.hostname());
    println!("port: {}", url.port());
    println!("pathname: {}", url.pathname());
    println!("search: {}", url.search());
    println!("hash: {}", url.hash());
    // Every part is a string, as in JavaScript's URL, so no port is "".
    let plain = parse_url("HTTPS://example.com:443", NO_BASE).expect("a URL");
    println!("default port: {}, port \"{}\"", plain.href(), plain.port());

    section("2. Relative URLs");

    let base = "https://example.com/docs/guide/intro.html";
    println!("base: {base}");
    for relative in ["setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"] {
        // The base is a string, parsed again on each call.
        let url = parse_url(relative, Some(base)).expect("a URL");
        println!("{relative} -> {}", url.href());
    }
    // Url::parse is the same as parse_url, as in JavaScript's URL.parse.
    println!("Url.parse: {}", Url::parse("setup.html", Some(base)).expect("a URL").href());
    // A Url can't be a base itself, so pass its href.
    let guide = parse_url(base, NO_BASE).expect("a URL");
    println!("from a Url: {}", parse_url("faq.html", Some(guide.href())).expect("a URL").href());

    section("3. Failures");

    // Input that isn't a URL gives Err(temper_core::Error), which says
    // nothing of why, and can't be shown: its Display calls itself.
    let cases = [
        ("https://exa mple.com", None),
        ("http://[::1", None),
        ("https://example.com:99999", None),
        ("setup.html", None),
        ("setup.html", Some("not a base")),
    ];
    for (input, against) in cases {
        let label = match against {
            Some(against) => format!("{input} against {against}"),
            None => format!("{input}, without a base"),
        };
        match parse_url(input, against) {
            Ok(_) => println!("{label}: parsed"),
            Err(_) => println!("{label}: not a URL"),
        }
    }
    // Or .ok(), for None in place of failure.
    let maybe: Option<Url> = parse_url("https://exa mple.com", NO_BASE).ok();
    println!("as an optional: {}", if maybe.is_none() { "nothing" } else { "a URL" });

    section("4. International domain names");

    // Hosts go to ASCII, as browsers send them.
    let idn = parse_url("https://Bücher.example/straße?q=ü", NO_BASE).expect("a URL");
    println!("hostname: {}", idn.hostname());
    println!("href: {}", idn.href());
    for domain in ["Bücher.Example", "faß.de", "☕.example", "xn--tešla"] {
        match domain_to_ascii(domain) {
            Ok(ascii) => println!("to ASCII: {domain} -> {ascii}"),
            Err(_) => println!("to ASCII: {domain} fails"),
        }
    }
    // And back to Unicode, for showing; it never fails. Decide on the ASCII
    // form: the second is a Cyrillic а, not apple.com.
    for domain in ["xn--bcher-kva.example", "xn--pple-43d.com"] {
        println!("to Unicode: {domain} -> {}", domain_to_unicode(domain));
    }

    section("5. Serializing with href");

    // href is the standard's canonical form, which other parsers read alike.
    for input in [
        "HTTP://EXAMPLE.COM/a/./b/../c",
        "https:\\\\example.com\\path",
        "http://0x7f.1/",
        "https://[0:0::1]:443/",
        "https://example.com/a b?c d#e f",
        " https://exa\tmple.com/\n",
    ] {
        let url = parse_url(input, NO_BASE).expect("a URL");
        println!("{} -> {}", shown(input), url.href());
    }
    // url.to_string() is href too, but Url has no Display, so format!("{url}")
    // doesn't compile.
    println!("as a string: {}", url.to_string());

    section("6. Using it safely");

    // Decide with Hrefine, then hand on href, never the original string.
    // reqwest, ureq, and hyper parse with the url crate, which follows the
    // same standard, but not always the same version of it, and http::Uri
    // follows RFC 3986.
    for input in [
        "https://api.example.com/v1/items",
        "https://example.com\\@evil.example/",
        "https://evil.example#@example.com",
        "https://0x7f.1/admin",
        "http://example.com/",
        "javascript:alert(1)",
        "https://exa mple.com",
    ] {
        println!("{input}: {}", check(input));
    }

    // A server redirecting to a `next` parameter: resolve it against your
    // own origin, and redirect only if the origin stays the same. In axum:
    // Redirect::to(url.href().as_str()).
    let site = "https://example.com/";
    for target in ["/account", "//evil.example/", "/\\evil.example"] {
        match parse_url(target, Some(site)) {
            Ok(url) if url.origin().as_str() == "https://example.com" => {
                println!("next={target}: redirect to {}", url.href())
            }
            Ok(url) => println!("next={target}: refuse, {}", url.origin()),
            Err(_) => println!("next={target}: refuse, not a URL"),
        }
    }
}
