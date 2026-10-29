// Hrefine's benchmark in Java; see ../run.py, which compiles it with the
// generated sources and runs it.
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

public final class Bench {
    static double seconds;

    static List<String> readLines(String folder, String name) throws Exception {
        List<String> lines = new ArrayList<>();
        for (String line : Files.readString(Path.of(folder, name), StandardCharsets.UTF_8).split("\n")) {
            if (!line.isEmpty()) lines.add(line);
        }
        return lines;
    }

    static String parse(String[] pair) {
        try {
            return hrefine.HrefineGlobal.parseUrl(pair[0], pair[1]).getHref();
        } catch (RuntimeException e) {
            return "fail";
        }
    }

    static String toAscii(String domain) {
        try {
            return hrefine.HrefineGlobal.domainToAscii(domain);
        } catch (RuntimeException e) {
            return "fail";
        }
    }

    // Nanoseconds per item, after warming up for `seconds`, running over
    // `items` for `seconds` more.
    static <T> double rate(Function<T, String> run, List<T> items) {
        long sink = 0;
        long end = System.nanoTime() + (long) (seconds * 1e9);
        while (System.nanoTime() < end) {
            for (T item : items) sink += run.apply(item).length();
        }
        long passes = 0;
        long start = System.nanoTime();
        while (true) {
            for (T item : items) sink += run.apply(item).length();
            passes += 1;
            long elapsed = System.nanoTime() - start;
            if (elapsed >= seconds * 1e9) {
                if (sink < 0) System.out.println(sink);
                return (double) elapsed / (passes * items.size());
            }
        }
    }

    public static void main(String[] args) throws Exception {
        String mode = args[0];
        String folder = args[1];
        seconds = args.length > 2 ? Double.parseDouble(args[2]) : 1.0;
        long t0 = System.nanoTime();
        Class.forName("hrefine.HrefineGlobal");
        long t1 = System.nanoTime();
        List<String[]> urls = new ArrayList<>();
        for (String line : readLines(folder, "urls.txt")) {
            String[] parts = line.split("\t", -1);
            urls.add(new String[] {parts[0], parts.length > 1 ? parts[1] : null});
        }
        List<String> domains = readLines(folder, "domains.txt");
        if (mode.equals("check")) {
            StringBuilder out = new StringBuilder();
            for (String[] pair : urls) out.append(parse(pair)).append('\n');
            for (String domain : domains) out.append(toAscii(domain)).append('\n');
            System.out.write(out.toString().getBytes(StandardCharsets.UTF_8));
            System.out.flush();
            return;
        }
        long t2 = System.nanoTime();
        parse(new String[] {"https://example.com/", null});
        long t3 = System.nanoTime();
        toAscii("bücher.example");
        long t4 = System.nanoTime();
        double parseNs = rate(Bench::parse, urls);
        double idnaNs = rate(Bench::toAscii, domains);
        System.out.printf(
            "{\"load_ms\": %f, \"first_ascii_ms\": %f, \"first_idna_ms\": %f, \"parse_ns\": %f, \"idna_ns\": %f}%n",
            (t1 - t0) / 1e6, (t3 - t2) / 1e6, (t4 - t3) / 1e6, parseNs, idnaNs);
    }
}
