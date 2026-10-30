//! A tour of Hrefine, from Rust.
//!
//! The same tour exists for each language Hrefine supports, and they all
//! print the same text. See demos/README.md for how to run them.

use hrefine::{
    check_url, domain_to_ascii, domain_to_unicode, parse_host, parse_url, parse_url_source,
    HostKind, Url, UrlDisplay, UrlPolicy, UrlSearchParams,
};
use std::sync::Arc;

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
fn check(input: &str) -> String {  // snippet: card
    let Some(url) = Url::parse(input, NO_BASE) else {  // snippet: card
        return "refuse: not a URL".into();  // snippet: card
    };  // snippet: card
    if url.scheme().as_str() != "https" {  // snippet: card
        return format!("refuse: scheme {}", url.scheme());  // snippet: card
    }  // snippet: card
    // An IP address isn't a name on the list, however it's written.
    // HostKind has no PartialEq, but eq compares kinds.
    match url.host_kind() {  // snippet: card
        Some(kind) if kind.eq(HostKind::domain()) => {}  // snippet: card
        Some(kind) => return format!("refuse: {} host {}", kind.to_string(), url.hostname()),  // snippet: card
        None => return "refuse: no host".into(),  // snippet: card
    }  // snippet: card
    if !ALLOWED.contains(&url.hostname().as_str()) {  // snippet: card
        return format!("refuse: host {}", url.hostname());  // snippet: card
    }  // snippet: card
    // reqwest::get(url.href().as_str()), never input, with a client built
    // with .redirect(Policy::none()), or check each redirect the same way.
    // A hostname doesn't say where DNS sends it.
    format!("fetch {}", url.href())  // snippet: card
}  // snippet: card

fn main() {
    // Sets up Hrefine and Temper's runtime. Call it once before anything
    // else.
    hrefine::init(None).expect("hrefine::init");

    println!("# Hrefine tour");

    section("1. Parsing and reading parts");

    // Failure is an Err, so a URL known to be good can take expect.
    let text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";  // snippet: hero
    let url = parse_url(text, NO_BASE).expect("a URL");  // snippet: hero, parts
    println!("input: {text}");
    // Each part is an Arc<String>.
    // No username or password in href, by design (see section 5).
    println!("href: {}", url.href());  // snippet: parts
    println!("origin: {}", url.origin());  // snippet: parts
    println!("protocol: {}", url.protocol());  // snippet: parts
    println!("username: {}", url.username());  // snippet: parts
    println!("password: {}", url.password());  // snippet: parts
    println!("host: {}", url.host());  // snippet: parts
    println!("hostname: {}", url.hostname());  // snippet: parts, hero
    println!("port: {}", url.port());  // snippet: parts
    println!("pathname: {}", url.pathname());  // snippet: parts
    println!("search: {}", url.search());  // snippet: parts
    println!("hash: {}", url.hash());  // snippet: parts
    // Typed parts, beside the standard's strings.
    println!("scheme: {}", url.scheme());  // snippet: parts
    println!("port number: {}", url.port_number().expect("a port"));  // snippet: parts
    println!("host kind: {}", url.host_kind().expect("a host").to_string());  // snippet: parts
    // The standard's parts are strings, as in JavaScript's URL, so no port is
    // "", and port_number is None.
    let plain = parse_url("HTTPS://example.com:443", NO_BASE).expect("a URL");
    let port_number = plain.port_number().map_or("none".to_string(), |n| n.to_string());
    println!("default port: {}, port \"{}\", port number {port_number}", plain.href(), plain.port());

    section("2. Relative URLs");

    // Parse the base once, then resolve against it.
    let guide = parse_url("https://example.com/docs/guide/intro.html", NO_BASE).expect("a URL");  // snippet: base
    println!("base: {}", guide.href());
    for relative in ["setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js"] {  // snippet: base
        println!("{relative} -> {}", guide.resolve(relative).expect("a URL").href());  // snippet: base
    }  // snippet: base
    // Or give the base as a string, parsed on each call.
    let faq = parse_url("faq.html", Some(guide.href())).expect("a URL");  // snippet: base
    println!("with a string base: {}", faq.href());  // snippet: base

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
        let check = check_url(input, NO_BASE).expect("no base to fail");  // snippet: errors
        let errors: Vec<String> = check.errors().iter().map(|error| error.to_string().to_string()).collect();  // snippet: errors
        let result = check.url().map_or("not a URL".to_string(), |url| url.href().to_string());  // snippet: errors
        println!("{input}: {result} ({})", errors.join(", "));  // snippet: errors
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
    // href() has no credentials, by design, unlike JavaScript's URL.href, so
    // it's the one to hand on, store, or compare as text. url.to_string()
    // masks them, for logs, but Url has no Display, so format!("{url}")
    // doesn't compile. without_credentials() gives a Url without them. Only
    // to send them deliberately, there's href_with_credentials(), which has
    // the password: never log it.
    println!("href, to hand on: {}", url.href());
    println!("as a string: {}", url.to_string());
    println!("without credentials: {}", url.without_credentials().to_string());
    // eq compares whole URLs, credentials included; there's no PartialEq, so
    // == doesn't compile.
    println!("same without credentials: {}", url.eq(url.without_credentials()));
    let a = parse_url("HTTP://EXAMPLE.COM/a/./b/../c", NO_BASE).expect("a URL");
    let b = parse_url("http://example.com/a/c", NO_BASE).expect("a URL");
    println!("same URL: {}", a.eq(b));
    // strict_href also escapes what RFC 3986 parsers reject, for those that
    // follow it strictly.
    let strict = parse_url("https://example.com/a|b/%zz?q={x}#c^d", NO_BASE).expect("a URL");  // snippet: proof
    println!("strict: {} -> {}", strict.href(), strict.strict_href());  // snippet: proof

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

    section("7. Changing parts");

    // The standard's setters, as methods that give a new URL, so a URL that
    // passed a check can't change after. A value that can't be set is
    // ignored, as in JavaScript.
    let page = parse_url("https://example.com/docs?lang=en&q=a+b", NO_BASE).expect("a URL");
    println!("page: {}", page.href());
    println!("with host: {}", page.with_host("example.org:8443").href());
    println!("with pathname and hash: {}", page.with_pathname("/a b").with_hash("top").href());
    println!("with protocol: {}", page.with_protocol("http").href());
    println!("port \"http\", ignored: {}", page.with_port("http").href());
    println!("with port number: {}", page.with_port_number(Some(8443)).href());
    println!("unchanged: {}", page.href());
    // Search parameters: a copy of the query, changed in place, then put
    // back. Its methods take &self, as Temper's Rust classes do.
    let params = page.search_params();
    println!("q: {}", params.get("q").expect("a value"));
    params.append("lang", "fr");
    params.set("q", "café & more");
    params.remove("missing", NO_BASE);
    params.sort();
    let langs: Vec<String> = params.get_all("lang").iter().map(|lang| lang.to_string()).collect();
    println!("lang: {}", langs.join(", "));
    for (name, value) in params.entries().iter() {
        println!("{name} = {value}");
    }
    println!("with search params: {}", page.with_search_params(params.clone()).href());
    // Or from pairs of names and values.
    let pairs = [("q", "a b"), ("page", "2")].map(|(name, value)| (Arc::new(name.to_string()), Arc::new(value.to_string())));
    println!("from pairs: {}", UrlSearchParams::from_entries(pairs).to_string());

    section("8. Test cases");

    // Each of web-platform-tests' URL cases gives an input, a base, and the
    // standard's href it must parse to (the full form, with credentials), or
    // "" where parsing must fail. Hrefine's tests run them all, checking
    // every part, and so does the site, in the browser.
    let cases = [
        ["http:\\\\foo.com\\", "http://example.org/foo/bar", "http://foo.com/"],
        ["../aaa/test.txt", "http://www.example.com/test", "http://www.example.com/aaa/test.txt"],
        ["http://999999999", "http://other.com/", "http://59.154.201.255/"],
        ["http://192.168.0.257", "http://other.com/", ""],
    ];
    for [input, base, href] in cases {  // snippet: scoreboard
        let url = Url::parse(input, Some(base));  // snippet: scoreboard
        let got = url.map_or(String::new(), |url| url.href_with_credentials().to_string());  // snippet: scoreboard
        println!("{input} against {base}: {}", if got == href { "pass" } else { "fail" });  // snippet: scoreboard
    }  // snippet: scoreboard

    section("9. Policies");

    // A policy does the checks of section 6 in one call, on the parsed URL.
    // Build it once, a rule at a time, and use it for every URL.
    // UrlPolicy::fetch(), for URLs a server fetches, is https only, strict,
    // with no credentials and no private, loopback, or other special
    // addresses or names; this one adds example.com or its subdomains.
    // Reasons never show credentials.
    let policy = UrlPolicy::fetch().with_hosts([Arc::new("example.com".to_string())], true);  // snippet: policy
    let inputs = [
        "https://api.example.com/v1/items",
        "http://example.com/",
        "https://example.com@evil.example/",
        "https://127.1/",
        "https://169.254.169.254/latest/meta-data/",
        "https://[::ffff:127.0.0.1]/",
        "https://localhost./",
        "https://ex\u{430}mple.com/",
    ];
    for input in inputs {  // snippet: policy
        let result = policy.check(input);  // snippet: policy
        match result.url() {  // snippet: policy
            Some(url) => println!("{input}: fetch {}", url.href()),  // snippet: policy
            None => println!("{input}: refuse, {}", result.to_string()),  // snippet: policy
        }  // snippet: policy
    }  // snippet: policy

    // Strict mode refuses what the standard accepts but notes as an error,
    // as cautious parsers do: backslashes, tabs, odd IPv4 forms, and the
    // like. with_strict(true) adds it to a policy.
    for input in ["https://example.com/a b", "http://0x7f.1/", "https://example.com\\a", " https://example.com/"] {
        let check = check_url(input, NO_BASE).expect("no base to fail");
        match check.strict_url() {
            Some(strict) => println!("strict {}: {}", shown(input), strict.href()),
            None => {
                let errors: Vec<String> = check.strict_errors().iter().map(|error| error.to_string().to_string()).collect();
                println!("strict {}: refuse, {}", shown(input), errors.join(", "));
            }
        }
    }

    // Redirect targets: with_path_only takes only a path, query, or fragment
    // on the base, never another host, however it's written.
    let redirects = UrlPolicy::any().with_base(site.clone()).with_path_only(true);
    for target in ["/account?tab=2", "//evil.example/", "/\\evil.example", "/\t/evil.example", "https://example.com/"] {
        let result = redirects.check(target);
        match result.url() {
            Some(url) => println!("next={}: redirect to {}", shown(target), url.href()),
            None => println!("next={}: refuse, {}", shown(target), result.to_string()),
        }
    }

    section("10. Showing, comparing, and spans");

    // To show people a URL, as browsers' address bars do: hosts in Unicode
    // where browsers would show them (not look-alikes such as Cyrillic а in
    // xn--pple-43d.com), and escapes of non-ASCII text decoded. Never for
    // security decisions, nor for handing on: use href() for those.
    let display = UrlDisplay::address_bar().with_root_slash(false);  // snippet: display
    for input in [  // snippet: display
        "https://user@xn--bcher-kva.example/caf%C3%A9?q=%E6%97%A5%E6%9C%AC",  // snippet: display
        "https://xn--pple-43d.com/",  // snippet: display
    ] {  // snippet: display
        let url = parse_url(input, NO_BASE).expect("a URL");  // snippet: display
        println!("display: {}", display.format(url));  // snippet: display
    }  // snippet: display
    // Credentials are left out, as address bars leave them out. Asked for, the
    // username shows, but a password only as ***.
    let login = parse_url("https://user:pass@example.com/", NO_BASE).expect("a URL");
    println!("with credentials: {}", display.with_credentials(true).format(login));

    // The same URL, the same but for the fragment, or the same origin. All
    // compare canonical forms, so case and a default port don't matter.
    let intro = parse_url("https://EXAMPLE.com:443/a/../guide#intro", NO_BASE).expect("a URL");
    let setup = parse_url("https://example.com/guide#setup", NO_BASE).expect("a URL");
    let about = parse_url("https://example.com/about", NO_BASE).expect("a URL");
    println!("same URL: {}", intro.eq(setup.clone()));
    println!("same document: {}", intro.same_document(setup));
    println!("same origin: {}", intro.same_origin(about));

    // Where each part was written, for editors and linters: never for
    // security decisions, which use url(). Spans count code points.
    let source = parse_url_source(" https://EXAMPLE.com:443/a/../b?q=1", NO_BASE).expect("a URL");
    println!("href: {}", source.url().href());
    let host = source.host_span().expect("a host");
    println!("host as written: {}, at {}", host.as_written(), host.to_string());
    println!("path as written: {}", source.path_span().expect("a path").as_written());
    let check = check_url("https://exa mple.com", NO_BASE).expect("no base to fail");
    for error in check.errors().iter() {
        println!("{}: from {}, {} long", error.name(), error.position(), error.length());
    }
}
