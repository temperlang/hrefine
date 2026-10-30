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
import hrefine.UrlCheck;
import hrefine.ValidationError;
import java.util.List;
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
    static String check(String input) {
        Url url = Url.parse(input);
        if (url == null) return "refuse: not a URL";
        if (!url.getScheme().equals("https")) return "refuse: scheme " + url.getScheme();
        // An IP address isn't a name on the list, however it's written.
        // Each kind is one object, so == works.
        if (url.getHostKind() != HostKind.domain) {
            return "refuse: " + url.getHostKind() + " host " + url.getHostname();
        }
        if (!ALLOWED.contains(url.getHostname())) return "refuse: host " + url.getHostname();
        // client.send(HttpRequest.newBuilder(URI.create(url.getHref())).build(), ...),
        // never input, with a client built with
        // .followRedirects(HttpClient.Redirect.NEVER), or check each redirect
        // the same way. URI.create follows RFC 3986, which rejects a few
        // characters href leaves as they are, such as | and ^. A hostname
        // doesn't say where DNS sends it.
        return "fetch " + url.getHref();
    }

    public static void main(String[] args) {
        System.out.println("# Hrefine tour");

        section("1. Parsing and reading parts");

        String text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top";
        Url url = parseUrl(text);
        System.out.println("input: " + text);
        System.out.println("href: " + url.getHref());
        System.out.println("origin: " + url.getOrigin());
        System.out.println("protocol: " + url.getProtocol());
        System.out.println("username: " + url.getUsername());
        System.out.println("password: " + url.getPassword());
        System.out.println("host: " + url.getHost());
        System.out.println("hostname: " + url.getHostname());
        System.out.println("port: " + url.getPort());
        System.out.println("pathname: " + url.getPathname());
        System.out.println("search: " + url.getSearch());
        System.out.println("hash: " + url.getHash());
        // Typed parts, beside the standard's strings.
        System.out.println("scheme: " + url.getScheme());
        System.out.println("port number: " + url.getPortNumber());
        System.out.println("host kind: " + url.getHostKind());
        // The standard's parts are strings, as in JavaScript's URL, so no
        // port is "", and getPortNumber() is null.
        Url plain = parseUrl("HTTPS://example.com:443");
        System.out.println("default port: " + plain.getHref() + ", port \"" + plain.getPort()
            + "\", port number " + Objects.toString(plain.getPortNumber(), "none"));

        section("2. Relative URLs");

        // Parse the base once, then resolve against it.
        Url guide = parseUrl("https://example.com/docs/guide/intro.html");
        System.out.println("base: " + guide.getHref());
        for (String relative : List.of("setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js")) {
            System.out.println(relative + " -> " + guide.resolve(relative).getHref());
        }
        // Or give the base as a string, parsed on each call.
        System.out.println("with a string base: " + parseUrl("faq.html", guide.getHref()).getHref());

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
            UrlCheck check = checkUrl(input);
            String errors = check.getErrors().stream().map(ValidationError::toString).collect(Collectors.joining(", "));
            String result = check.getUrl() != null ? check.getUrl().getHref() : "not a URL";
            System.out.println(input + ": " + result + " (" + errors + ")");
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
    }
}
