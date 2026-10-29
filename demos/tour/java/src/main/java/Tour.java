// A tour of Hrefine, from Java.
//
// The same tour exists for each language Hrefine supports, and they all print
// the same text. See demos/README.md for how to run them.

import static hrefine.HrefineGlobal.domainToAscii;
import static hrefine.HrefineGlobal.domainToUnicode;
import static hrefine.HrefineGlobal.parseUrl;

import hrefine.Url;
import java.util.List;
import java.util.Optional;
import java.util.Set;

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

    /** The URL, or empty if it isn't one. */
    static Optional<Url> tryParse(String text, String base) {
        try {
            return Optional.of(parseUrl(text, base));
        } catch (RuntimeException e) {
            return Optional.empty();
        }
    }

    static final Set<String> ALLOWED = Set.of("example.com", "api.example.com");

    /** The URL to fetch, or why not. */
    static String check(String input) {
        Optional<Url> parsed = tryParse(input, null);
        if (parsed.isEmpty()) return "refuse: not a URL";
        Url url = parsed.get();
        if (!url.getProtocol().equals("https:")) return "refuse: protocol " + url.getProtocol();
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
        // Every part is a string, as in JavaScript's URL, so no port is "".
        Url plain = parseUrl("HTTPS://example.com:443");
        System.out.println("default port: " + plain.getHref() + ", port \"" + plain.getPort() + "\"");

        section("2. Relative URLs");

        String base = "https://example.com/docs/guide/intro.html";
        System.out.println("base: " + base);
        for (String relative : List.of("setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js")) {
            // The base is a string, parsed again on each call.
            System.out.println(relative + " -> " + parseUrl(relative, base).getHref());
        }
        // Url.parse is the same as parseUrl, as in JavaScript's URL.parse.
        System.out.println("Url.parse: " + Url.parse("setup.html", base).getHref());
        // A Url can't be a base itself, so pass its href.
        Url guide = parseUrl(base);
        System.out.println("from a Url: " + parseUrl("faq.html", guide.getHref()).getHref());

        section("3. Failures");

        // Input that isn't a URL throws a plain RuntimeException, with no
        // message, so it says nothing of why, and catching it catches every
        // other unchecked exception too. (java.net.URI throws
        // URISyntaxException, with a reason and an index.)
        String[][] cases = {
            {"https://exa mple.com", null},
            {"http://[::1", null},
            {"https://example.com:99999", null},
            {"setup.html", null},
            {"setup.html", "not a base"},
        };
        for (String[] pair : cases) {
            String input = pair[0];
            String against = pair[1];
            String label = against != null ? input + " against " + against : input + ", without a base";
            try {
                parseUrl(input, against);
                System.out.println(label + ": parsed");
            } catch (RuntimeException e) {
                System.out.println(label + ": not a URL");
            }
        }
        // Or wrap it, as tryParse above does, for an Optional.
        System.out.println("as an optional: " + (tryParse("https://exa mple.com", null).isEmpty() ? "nothing" : "a URL"));

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

        // A server redirecting to a `next` parameter: resolve it against
        // your own origin, and redirect only if the origin stays the same.
        // In a servlet: response.sendRedirect(next.getHref()).
        String site = "https://example.com/";
        for (String target : List.of("/account", "//evil.example/", "/\\evil.example")) {
            Optional<Url> next = tryParse(target, site);
            if (next.isPresent() && next.get().getOrigin().equals("https://example.com")) {
                System.out.println("next=" + target + ": redirect to " + next.get().getHref());
            } else {
                System.out.println("next=" + target + ": refuse, " + next.map(Url::getOrigin).orElse("not a URL"));
            }
        }
    }
}
