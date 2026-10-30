//! A tour of Hrefine, from Rust.
//!
//! The same tour exists for each language Hrefine supports, and they all
//! print the same text. See demos/README.md for how to run them.

use hrefine::{
    check_url, domain_to_ascii, domain_to_unicode, parse_host, parse_url, HostKind, Url,
};

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
    let Some(url) = Url::parse(input, NO_BASE) else {
        return "refuse: not a URL".into();
    };
    if url.scheme().as_str() != "https" {
        return format!("refuse: scheme {}", url.scheme());
    }
    // An IP address isn't a name on the list, however it's written.
    // HostKind has no PartialEq, but eq compares kinds.
    match url.host_kind() {
        Some(kind) if kind.eq(HostKind::domain()) => {}
        Some(kind) => return format!("refuse: {} host {}", kind.to_string(), url.hostname()),
        None => return "refuse: no host".into(),
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
    // Typed parts, beside the standard's strings.
    println!("scheme: {}", url.scheme());
    println!("port number: {}", url.port_number().expect("a port"));
    println!("host kind: {}", url.host_kind().expect("a host").to_string());
    // The standard's parts are strings, as in JavaScript's URL, so no port is
    // "", and port_number is None.
    let plain = parse_url("HTTPS://example.com:443", NO_BASE).expect("a URL");
    let port_number = plain.port_number().map_or("none".to_string(), |n| n.to_string());
    println!("default port: {}, port \"{}\", port number {port_number}", plain.href(), plain.port());

    section("2. Relative URLs");

    // Parse the base once, then resolve against it.
    let guide = parse_url("https://example.com/docs/guide/intro.html", NO_BASE).expect("a URL");
    println!("base: {}", guide.href());
    for relative in ["setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"] {
        println!("{relative} -> {}", guide.resolve(relative).expect("a URL").href());
    }
    // Or give the base as a string, parsed on each call.
    let faq = parse_url("faq.html", Some(guide.href())).expect("a URL");
    println!("with a string base: {}", faq.href());

    section("3. Failures");

    // check_url says why input isn't a URL, with the standard's names for
    // what's wrong and where, counted in code points from 0. The last error
    // is why it failed. Some errors don't stop a URL from parsing, as
    // browsers accept it. It's an Err only for a base that isn't a URL.
    for input in [
        "https://exa mple.com",
        "http://[::1",
        "https://example.com:99999",
        "setup.html",
        "https:example.com/a b",
    ] {
        let check = check_url(input, NO_BASE).expect("no base to fail");
        let errors: Vec<String> = check.errors().iter().map(|error| error.to_string().to_string()).collect();
        let result = check.url().map_or("not a URL".to_string(), |url| url.href().to_string());
        println!("{input}: {result} ({})", errors.join(", "));
    }
    // Url::parse gives None where parse_url gives Err, and Url::can_parse
    // says only whether it would parse, as in JavaScript.
    let nothing = Url::parse("setup.html", NO_BASE).is_none();
    println!("nullable parse: {}", if nothing { "nothing" } else { "a URL" });
    println!("can parse: {}", Url::can_parse("setup.html", NO_BASE));
    // parse_url's Err(temper_core::Error) says nothing of why, and can't be
    // shown: its Display calls itself. So check_url says why.
    match parse_url("setup.html", NO_BASE) {
        Ok(_) => println!("throwing parse: parsed"),
        Err(_) => println!("throwing parse: throws"),
    }

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
    // eq compares hrefs; there's no PartialEq, so == doesn't compile.
    let a = parse_url("HTTP://EXAMPLE.COM/a/./b/../c", NO_BASE).expect("a URL");
    let b = parse_url("http://example.com/a/c", NO_BASE).expect("a URL");
    println!("same URL: {}", a.eq(b));

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

    // Check hosts from configuration with parse_host, which domain_to_ascii
    // isn't for: it passes all three.
    for input in ["example.com", "0x7f.1", "exa mple.com"] {
        match parse_host(input) {
            Ok(host) => println!("host {input}: {} {}", host.kind().to_string(), host.serialized()),
            Err(_) => println!("host {input}: not a host"),
        }
    }

    // A server redirecting to a `next` parameter: resolve it against your
    // own site, and redirect only to the same origin. In axum:
    // Redirect::to(url.href().as_str()).
    let site = parse_url("https://example.com/", NO_BASE).expect("a URL");
    for target in ["/account", "//evil.example/", "/\\evil.example", "//[::1"] {
        match site.try_resolve(target) {
            Some(url) if url.same_origin(site.clone()) => {
                println!("next={target}: redirect to {}", url.href())
            }
            Some(url) => println!("next={target}: refuse, {}", url.origin()),
            None => println!("next={target}: refuse, not a URL"),
        }
    }
}
