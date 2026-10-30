// A tour of Hrefine, from Java.
//
// The same tour exists for each language Hrefine supports, and they all print
// the same text. See demos/README.md for how to run them.

import static hrefine.HrefineGlobal.checkUrl;
import static hrefine.HrefineGlobal.domainToAscii;
import static hrefine.HrefineGlobal.domainToUnicode;
import static hrefine.HrefineGlobal.parseHost;
import static hrefine.HrefineGlobal.parseUrl;

import hrefine.Host;
import hrefine.HostKind;
import hrefine.Url;
import hrefine.UrlPolicy;
import hrefine.PolicyCheck;
import hrefine.UrlSearchParams;
import hrefine.UrlCheck;
import hrefine.ValidationError;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

public final class Tour {
    private Tour() {}

    static void section(String title) {
        System.out.println();
        System.out.println("## " + title);
    }

    /** Tabs and newlines made visible. */
    static String shown(String text) {
        return text.replace("\t", "\\t").replace("\n", "\\n");
    }

    static final Set<String> ALLOWED = Set.of("example.com", "api.example.com");

    /** The URL to fetch, or why not. */
    static String check(String input) {  // snippet: card
        Url url = Url.parse(input);  // snippet: card
        if (url == null) return "refuse: not a URL";  // snippet: card
        if (!url.getScheme().equals("https")) return "refuse: scheme " + url.getScheme();  // snippet: card
        // An IP address isn't a name on the list, however it's written.
        // Each kind is one object, so == works.
        if (url.getHostKind() != HostKind.domain) {  // snippet: card
            return "refuse: " + url.getHostKind() + " host " + url.getHostname();  // snippet: card
        }  // snippet: card
        if (!ALLOWED.contains(url.getHostname())) return "refuse: host " + url.getHostname();  // snippet: card
        // client.send(HttpRequest.newBuilder(URI.create(url.getHref())).build(), ...),
        // never input, with a client built with
        // .followRedirects(HttpClient.Redirect.NEVER), or check each redirect
        // the same way. URI.create follows RFC 3986, which rejects a few
        // characters href leaves as they are, such as | and ^. A hostname
        // doesn't say where DNS sends it.
        return "fetch " + url.getHref();  // snippet: card
    }  // snippet: card

    public static void main(String[] args) {
        System.out.println("# Hrefine tour");

        section("1. Parsing and reading parts");

        String text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";  // snippet: hero
        Url url = parseUrl(text);  // snippet: hero, parts
        System.out.println("input: " + text);
        System.out.println("href: " + url.getHref());  // snippet: parts
        System.out.println("origin: " + url.getOrigin());  // snippet: parts
        System.out.println("protocol: " + url.getProtocol());  // snippet: parts
        System.out.println("username: " + url.getUsername());  // snippet: parts
        System.out.println("password: " + url.getPassword());  // snippet: parts
        System.out.println("host: " + url.getHost());  // snippet: parts
        System.out.println("hostname: " + url.getHostname());  // snippet: parts, hero
        System.out.println("port: " + url.getPort());  // snippet: parts
        System.out.println("pathname: " + url.getPathname());  // snippet: parts
        System.out.println("search: " + url.getSearch());  // snippet: parts
        System.out.println("hash: " + url.getHash());  // snippet: parts
        // Typed parts, beside the standard's strings.
        System.out.println("scheme: " + url.getScheme());  // snippet: parts
        System.out.println("port number: " + url.getPortNumber());  // snippet: parts
        System.out.println("host kind: " + url.getHostKind());  // snippet: parts
        // The standard's parts are strings, as in JavaScript's URL, so no
        // port is "", and getPortNumber() is null.
        Url plain = parseUrl("HTTPS://example.com:443");
        System.out.println("default port: " + plain.getHref() + ", port \"" + plain.getPort()
            + "\", port number " + Objects.toString(plain.getPortNumber(), "none"));

        section("2. Relative URLs");

        // Parse the base once, then resolve against it.
        Url guide = parseUrl("https://example.com/docs/guide/intro.html");  // snippet: base
        System.out.println("base: " + guide.getHref());
        for (String relative : List.of("setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js")) {  // snippet: base
            System.out.println(relative + " -> " + guide.resolve(relative).getHref());  // snippet: base
        }  // snippet: base
        // Or give the base as a string, parsed on each call.
        System.out.println("with a string base: " + parseUrl("faq.html", guide.getHref()).getHref());  // snippet: base

        section("3. Failures");

        // checkUrl says why input isn't a URL, with the standard's names for
        // what's wrong and where, counted in code points from 0. The last
        // error is why it failed. Some errors don't stop a URL from
        // parsing, as browsers accept it.
        for (String input : List.of(
            "https://exa mple.com",
            "http://[::1",
            "https://example.com:99999",
            "setup.html",
            "https:example.com/a b"
        )) {
            UrlCheck check = checkUrl(input);  // snippet: errors
            String errors = check.getErrors().stream().map(ValidationError::toString).collect(Collectors.joining(", "));  // snippet: errors
            String result = check.getUrl() != null ? check.getUrl().getHref() : "not a URL";  // snippet: errors
            System.out.println(input + ": " + result + " (" + errors + ")");  // snippet: errors
        }
        // Url.parse gives null where parseUrl throws, and Url.canParse says
        // only whether it would parse, as in JavaScript.
        System.out.println("nullable parse: " + (Url.parse("setup.html") == null ? "nothing" : "a URL"));
        System.out.println("can parse: " + Url.canParse("setup.html"));
        // parseUrl throws a plain RuntimeException, with no message, and
        // catching it catches every other unchecked exception too, so
        // checkUrl says why. (java.net.URI throws URISyntaxException, with a
        // reason and an index.)
        try {
            parseUrl("setup.html");
            System.out.println("throwing parse: parsed");
        } catch (RuntimeException e) {
            System.out.println("throwing parse: throws");
        }

        section("4. International domain names");

        // Hosts go to ASCII, as browsers send them.
        Url idn = parseUrl("https://Bücher.example/straße?q=ü");
        System.out.println("hostname: " + idn.getHostname());
        System.out.println("href: " + idn.getHref());
        for (String domain : List.of("Bücher.Example", "faß.de", "☕.example", "xn--tešla")) {
            try {
                System.out.println("to ASCII: " + domain + " -> " + domainToAscii(domain));
            } catch (RuntimeException e) {
                System.out.println("to ASCII: " + domain + " fails");
            }
        }
        // And back to Unicode, for showing; it never fails. Decide on the
        // ASCII form: the second is a Cyrillic а, not apple.com.
        for (String domain : List.of("xn--bcher-kva.example", "xn--pple-43d.com")) {
            System.out.println("to Unicode: " + domain + " -> " + domainToUnicode(domain));
        }

        section("5. Serializing with href");

        // href is the standard's canonical form, which other parsers read
        // alike.
        for (String input : List.of(
            "HTTP://EXAMPLE.COM/a/./b/../c",
            "https:\\\\example.com\\path",
            "http://0x7f.1/",
            "https://[0:0::1]:443/",
            "https://example.com/a b?c d#e f",
            " https://exa\tmple.com/\n"
        )) {
            System.out.println(shown(input) + " -> " + parseUrl(input).getHref());
        }
        // toString() is href too, so string concatenation gives it.
        System.out.println("as a string: " + url);
        // eq compares hrefs; equals, not overridden, compares objects.
        System.out.println("same URL: " + parseUrl("HTTP://EXAMPLE.COM/a/./b/../c").eq(parseUrl("http://example.com/a/c")));
        // getStrictHref() also escapes what RFC 3986 parsers reject, such as
        // java.net.URI, which refuses the href below.
        Url strict = parseUrl("https://example.com/a|b/%zz?q={x}#c^d");  // snippet: proof
        System.out.println("strict: " + strict.getHref() + " -> " + strict.getStrictHref());  // snippet: proof

        section("6. Using it safely");

        // Decide with Hrefine, then hand on href, never the original string.
        // java.net.URI, HttpClient, and most servers follow RFC 3986, and
        // java.net.URL its own older rules, not the URL Standard.
        for (String input : List.of(
            "https://api.example.com/v1/items",
            "https://example.com\\@evil.example/",
            "https://evil.example#@example.com",
            "https://0x7f.1/admin",
            "http://example.com/",
            "javascript:alert(1)",
            "https://exa mple.com"
        )) {
            System.out.println(input + ": " + check(input));
        }

        // Check hosts from configuration with parseHost, which domainToAscii
        // isn't for: it passes all three.
        for (String input : List.of("example.com", "0x7f.1", "exa mple.com")) {
            try {
                Host host = parseHost(input);
                System.out.println("host " + input + ": " + host.getKind() + " " + host.getSerialized());
            } catch (RuntimeException e) {
                System.out.println("host " + input + ": not a host");
            }
        }

        // A server redirecting to a `next` parameter: resolve it against
        // your own site, and redirect only to the same origin. In a
        // servlet: response.sendRedirect(next.getHref()).
        Url site = parseUrl("https://example.com/");
        for (String target : List.of("/account", "//evil.example/", "/\\evil.example", "//[::1")) {
            Url next = site.tryResolve(target);
            if (next != null && next.sameOrigin(site)) {
                System.out.println("next=" + target + ": redirect to " + next.getHref());
            } else {
                System.out.println("next=" + target + ": refuse, " + (next != null ? next.getOrigin() : "not a URL"));
            }
        }

        section("7. Changing parts");

        // The standard's setters, as methods that give a new URL, so a URL
        // that passed a check can't change after. A value that can't be
        // set is ignored, as in JavaScript.
        Url page = parseUrl("https://example.com/docs?lang=en&q=a+b");
        System.out.println("page: " + page.getHref());
        System.out.println("with host: " + page.withHost("example.org:8443").getHref());
        System.out.println("with pathname and hash: " + page.withPathname("/a b").withHash("top").getHref());
        System.out.println("with protocol: " + page.withProtocol("http").getHref());
        System.out.println("port \"http\", ignored: " + page.withPort("http").getHref());
        System.out.println("with port number: " + page.withPortNumber(8443).getHref());
        System.out.println("unchanged: " + page.getHref());
        // Search parameters: a copy of the query, changed in place, then
        // put back.
        UrlSearchParams params = page.getSearchParams();
        System.out.println("q: " + params.get("q"));
        params.append("lang", "fr");
        params.set("q", "café & more");
        params.remove("missing");
        params.sort();
        System.out.println("lang: " + String.join(", ", params.getAll("lang")));
        for (Map.Entry<String, String> entry : params.entries()) {
            System.out.println(entry.getKey() + " = " + entry.getValue());
        }
        System.out.println("with search params: " + page.withSearchParams(params).getHref());
        // Or from pairs of names and values.
        UrlSearchParams fromPairs = UrlSearchParams.fromEntries(List.of(Map.entry("q", "a b"), Map.entry("page", "2")));
        System.out.println("from pairs: " + fromPairs);
   

        section("8. Test cases");

        // Each of web-platform-tests' URL cases gives an input, a base, and
        // the href it must parse to, or "" where parsing must fail.
        // Hrefine's tests run them all, checking every part, and so does
        // the site, in the browser.
        String[][] cases = {
            {"http:\\\\foo.com\\", "http://example.org/foo/bar", "http://foo.com/"},
            {"../aaa/test.txt", "http://www.example.com/test", "http://www.example.com/aaa/test.txt"},
            {"http://999999999", "http://other.com/", "http://59.154.201.255/"},
            {"http://192.168.0.257", "http://other.com/", ""},
        };
        for (String[] test : cases) {  // snippet: scoreboard
            String input = test[0], base = test[1], href = test[2];  // snippet: scoreboard
            Url parsed = Url.parse(input, base);  // snippet: scoreboard
            String got = parsed == null ? "" : parsed.getHref();  // snippet: scoreboard
            System.out.println(input + " against " + base + ": " + (got.equals(href) ? "pass" : "fail"));  // snippet: scoreboard
        }  // snippet: scoreboard

        section("9. Policies");

        // A policy does the checks of section 6 in one call, on the parsed
        // URL. Build it once, a rule at a time, and use it for every URL:
        // https only, no credentials, no private, loopback, or other special
        // addresses or names, and example.com or its subdomains.
        UrlPolicy policy = UrlPolicy.any.withSchemes(List.of("https")).withCredentials(false)  // snippet: policy
            .withSpecialHosts(false).withHosts(List.of("example.com"), true);  // snippet: policy
        List<String> inputs = List.of(
            "https://api.example.com/v1/items",
            "http://example.com/",
            "https://example.com@evil.example/",
            "https://127.1/",
            "https://[::ffff:127.0.0.1]/",
            "https://localhost./",
            "https://exаmple.com/"
        );
        for (String input : inputs) {  // snippet: policy
            PolicyCheck result = policy.check(input);  // snippet: policy
            if (result.getUrl() != null) {  // snippet: policy
                System.out.println(input + ": fetch " + result.getUrl().getHref());  // snippet: policy
            } else {  // snippet: policy
                System.out.println(input + ": refuse, " + result.toString());  // snippet: policy
            }  // snippet: policy
        }  // snippet: policy

        // Strict mode refuses what the standard accepts but notes as an
        // error, as cautious parsers do: backslashes, tabs, odd IPv4 forms,
        // and the like. withStrict(true) adds it to a policy.
        for (String input : List.of("https://example.com/a b", "http://0x7f.1/", "https://example.com\\a", " https://example.com/")) {
            UrlCheck check = checkUrl(input);
            Url strictUrl = check.getStrictUrl();
            if (strictUrl != null) {
                System.out.println("strict " + shown(input) + ": " + strictUrl.getHref());
            } else {
                String errors = check.getStrictErrors().stream().map(ValidationError::toString).collect(Collectors.joining(", "));
                System.out.println("strict " + shown(input) + ": refuse, " + errors);
            }
        }

        // Redirect targets: withPathOnly takes only a path, query, or
        // fragment on the base, never another host, however it's written.
        UrlPolicy redirects = UrlPolicy.any.withBase(site).withPathOnly(true);
        for (String target : List.of("/account?tab=2", "//evil.example/", "/\\evil.example", "/\t/evil.example", "https://example.com/")) {
            PolicyCheck result = redirects.check(target);
            System.out.println("next=" + shown(target) + ": " + (result.getUrl() != null ? "redirect to " + result.getUrl().getHref() : "refuse, " + result.toString()));
        }
    }
}
