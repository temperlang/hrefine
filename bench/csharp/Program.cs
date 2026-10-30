// Hrefine's benchmark in C#; see ../run.py, which runs it.
using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Text;

static class Program
{
    static double seconds;

    static List<string> ReadLines(string folder, string name) =>
        File.ReadAllText(Path.Combine(folder, name), Encoding.UTF8)
            .Split('\n').Where(line => line != "").ToList();

    static string Parse((string Input, string? Base) pair)
    {
        try { return Hrefine.HrefineGlobal.ParseUrl(pair.Input, pair.Base).HrefWithCredentials; }
        catch (Exception) { return "fail"; }
    }

    static string ToAscii(string domain)
    {
        try { return Hrefine.HrefineGlobal.DomainToAscii(domain); }
        catch (Exception) { return "fail"; }
    }

    // Nanoseconds per item, after warming up for `seconds`, running
    // over `items` for `seconds` more.
    static double Rate<T>(Func<T, string> run, List<T> items)
    {
        long sink = 0;
        var clock = Stopwatch.StartNew();
        while (clock.Elapsed.TotalSeconds < seconds)
        {
            foreach (var item in items) sink += run(item).Length;
        }
        long passes = 0;
        clock.Restart();
        while (true)
        {
            foreach (var item in items) sink += run(item).Length;
            passes += 1;
            var elapsed = clock.Elapsed.TotalSeconds;
            if (elapsed >= seconds)
            {
                if (sink < 0) Console.WriteLine(sink);
                return elapsed * 1e9 / (passes * items.Count);
            }
        }
    }

    static void Main(string[] args)
    {
        var mode = args[0];
        var folder = args[1];
        seconds = args.Length > 2 ? double.Parse(args[2]) : 1.0;
        var clock = Stopwatch.StartNew();
        RuntimeHelpers.RunClassConstructor(typeof(Hrefine.HrefineGlobal).TypeHandle);
        var load = clock.Elapsed.TotalMilliseconds;
        var urls = ReadLines(folder, "urls.txt").Select(line =>
        {
            var parts = line.Split('\t');
            return (parts[0], parts.Length > 1 ? parts[1] : null);
        }).ToList();
        var domains = ReadLines(folder, "domains.txt");
        if (mode == "check")
        {
            var output = new StringBuilder();
            foreach (var pair in urls) output.Append(Parse(pair)).Append('\n');
            foreach (var domain in domains) output.Append(ToAscii(domain)).Append('\n');
            using var stdout = Console.OpenStandardOutput();
            var bytes = new UTF8Encoding(false).GetBytes(output.ToString());
            stdout.Write(bytes, 0, bytes.Length);
            return;
        }
        clock.Restart();
        Parse(("https://example.com/", null));
        var firstAscii = clock.Elapsed.TotalMilliseconds;
        clock.Restart();
        ToAscii("bücher.example");
        var firstIdna = clock.Elapsed.TotalMilliseconds;
        var parseNs = Rate<(string, string?)>(Parse, urls);
        var idnaNs = Rate<string>(ToAscii, domains);
        Console.WriteLine(FormattableString.Invariant(
            $"{{\"load_ms\": {load}, \"first_ascii_ms\": {firstAscii}, \"first_idna_ms\": {firstIdna}, \"parse_ns\": {parseNs}, \"idna_ns\": {idnaNs}}}"));
    }
}
