// Reads URLs with java.net.URI and java.net.URL, for site/record/record.py.
//
// Each input line is base64 of the input, a space, and base64 of the base
// (or "-" for none). Prints one JSON line per input line, with each parser's
// result. Run as source: java Probe.java

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

public final class Probe {
    static String decode(String text) {
        return new String(Base64.getDecoder().decode(text), StandardCharsets.UTF_8);
    }

    static String json(String text) {
        if (text == null) return "null";
        StringBuilder out = new StringBuilder("\"");
        for (char c : text.toCharArray()) {
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                default -> {
                    if (c < 0x20) out.append(String.format("\\u%04x", (int) c));
                    else out.append(c);
                }
            }
        }
        return out.append('"').toString();
    }

    static String ok(String scheme, String host, String href) {
        return "{\"ok\":true,\"scheme\":" + json(scheme) + ",\"host\":" + json(host) + ",\"href\":" + json(href) + "}";
    }

    static String error(Exception e) {
        return "{\"ok\":false,\"error\":" + json(e.getClass().getSimpleName() + ": " + e.getMessage()) + "}";
    }

    static String uri(String input, String base) {
        try {
            URI uri = base == null ? new URI(input) : new URI(base).resolve(new URI(input));
            return ok(uri.getScheme(), uri.getHost(), uri.toString());
        } catch (Exception e) {
            return error(e);
        }
    }

    @SuppressWarnings("deprecation")
    static String url(String input, String base) {
        try {
            URL url = base == null ? new URL(input) : new URL(new URL(base), input);
            return ok(url.getProtocol(), url.getHost(), url.toExternalForm());
        } catch (Exception e) {
            return error(e);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length > 0 && args[0].equals("--version")) {
            System.out.println(System.getProperty("java.vendor") + " " + System.getProperty("java.runtime.version"));
            return;
        }
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        for (String line; (line = in.readLine()) != null; ) {
            String[] parts = line.split(" ");
            String input = decode(parts[0]);
            String base = parts[1].equals("-") ? null : decode(parts[1]);
            System.out.println("{\"java-uri\":" + uri(input, base) + ",\"java-url\":" + url(input, base) + "}");
        }
    }
}
