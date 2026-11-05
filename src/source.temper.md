# Source Spans

Where each part of a URL was written in the input, for tools that point
at the input as typed: an editor underlining a host, a linter's
message, or the site's tester. A `UrlSource` keeps the input and, for
each part, its span there, beside the parsed `Url`. It's a separate
type, not more members on `Url`, so code that checks URLs never reaches
the text as written by mistake.

The text as written is neither normalized nor checked: `EXAMPLE.com`,
`0x7f.1`, `%65vil.example`, and a host with a tab in it are all as
typed, and other parsers may read them otherwise. **Never use spans or
`asWritten()` for security decisions;** use `url`, as everywhere else.
And the text as written may contain credentials and other secrets
(passwords, or tokens in a query or fragment), so don't log it.
Policies and strict mode take only input strings and `Url`s.

The standard strips leading and trailing C0 controls and spaces, and
removes tabs and newlines, before parsing. Spans count code points in
the input as given, so they cover a tab inside a part, and never the
stripped ends. Validation errors count the same way (see `checkUrl`).

```temper inert
let source = parseUrlSource(" https://EXAMPLE.com:443/a\tb?q#top");
source.url.href;                // "https://example.com/ab?q#top"
source.hostSpan.asWritten;      // "EXAMPLE.com", from 9, 11 long
source.pathSpan.asWritten;      // "/a\tb"
```

## The API

Parses `input`, against `base` if given, as `parseUrl` does, and keeps
where each part was written. It bubbles where `parseUrl` does.

    export let parseUrlSource(input: String, base: String? = null): UrlSource throws Bubble {
      let baseRecord = if (base == null) { noBase } else { parseRecord(base, noBase, false, null) };
      let log = new ErrorLog();
      let record = parseRecord(input, baseRecord, base != null, log);
      let pathEnd = if (log.queryStart >= 0) {
        log.queryStart - 1
      } else if (log.fragmentStart >= 0) {
        log.fragmentStart - 1
      } else {
        log.length
      };
      let queryEnd = if (log.fragmentStart >= 0) { log.fragmentStart - 1 } else { log.length };
      let usernameEnd = if (log.colonAt >= 0) { log.colonAt } else { log.lastAt };
      let cursor = new SpanCursor();
      new UrlSource(
        input, urlOf(record),
        spanOf(log, cursor, input, if (log.schemeEnd >= 0) { 0 } else { -1 }, log.schemeEnd),
        spanOf(log, cursor, input, if (log.lastAt >= 0) { log.userinfoStart } else { -1 }, usernameEnd),
        spanOf(log, cursor, input, if (log.colonAt >= 0) { log.colonAt + 1 } else { -1 }, log.lastAt),
        spanOf(log, cursor, input, log.hostStart, log.hostEnd),
        spanOf(log, cursor, input, log.portStart, log.portEnd),
        spanOf(log, cursor, input, log.pathStart, pathEnd),
        spanOf(log, cursor, input, log.queryStart, queryEnd),
        spanOf(log, cursor, input, log.fragmentStart, log.length),
      )
    }

A URL and where its parts were written. Each span is null where the
input didn't write that part: a relative URL's parts from the base, a
URL without credentials, or a port, and so on. A part written empty, as
the query in `https://example.com/?`, has an empty span, where it would
go. Spans leave out the delimiters: the scheme's `:`, `//`, `@`, the
port's `:`, `?`, and `#`, but the path keeps its leading `/`, as
`pathname` does.

    export class UrlSource {

The input, exactly as given: not normalized or checked. Never use it
for security decisions; use `url`. It may contain credentials and other
secrets; don't log it. It's a method, as are the username and password
spans, as `Url`'s `hrefWithCredentials()` is, so serializers that read
getters and properties, such as Java's Jackson and C#'s
`System.Text.Json`, leave the credentials out.

      public asWritten(): String { asWrittenValue }

      private asWrittenValue: String;

The parsed URL, the standard's canonical form, as `parseUrl` gives it.
This is the one for security decisions.

      public url: Url;

Where each part was written, as written: not normalized or checked, so
never for security decisions; use `url`'s parts. Each span's
`asWritten` may contain secrets, such as tokens in a query or fragment;
don't log it. The username and password spans are credentials, so
they're methods; the parser splits them at the first `:` before the
last `@`.

      public schemeSpan: SourceSpan?;

      public usernameSpan(): SourceSpan? { usernameSpanValue }

      public passwordSpan(): SourceSpan? { passwordSpanValue }

      public hostSpan: SourceSpan?;
      public portSpan: SourceSpan?;
      public pathSpan: SourceSpan?;
      public querySpan: SourceSpan?;
      public fragmentSpan: SourceSpan?;

      private usernameSpanValue: SourceSpan?;
      private passwordSpanValue: SourceSpan?;

      private constructor(
        asWritten: String, url: Url, schemeSpan: SourceSpan?, usernameSpan: SourceSpan?,
        passwordSpan: SourceSpan?, hostSpan: SourceSpan?, portSpan: SourceSpan?,
        pathSpan: SourceSpan?, querySpan: SourceSpan?, fragmentSpan: SourceSpan?,
      ) {
        this.asWrittenValue = asWritten;
        this.url = url;
        this.schemeSpan = schemeSpan;
        this.usernameSpanValue = usernameSpan;
        this.passwordSpanValue = passwordSpan;
        this.hostSpan = hostSpan;
        this.portSpan = portSpan;
        this.pathSpan = pathSpan;
        this.querySpan = querySpan;
        this.fragmentSpan = fragmentSpan;
      }
    }

A span of the input: its `start` and `length`, in code points of the
input as given, and its text `asWritten`, which is neither normalized
nor checked, so never for security decisions, and may contain
credentials and other secrets, so don't log it. It includes any tabs and
newlines the parser removed inside it. `toString` gives only where it
is, as `start+length`, such as `9+11`, never the text, so it's safe to
log.

    export class SourceSpan {
      public start: Int;
      public length: Int;
      public asWritten: String;

      private constructor(start: Int, length: Int, asWritten: String) {
        this.start = start;
        this.length = length;
        this.asWritten = asWritten;
      }

      public toString(): String { "${start.toString()}+${length.toString()}" }
    }

The span from `start` to `end` in the cleaned input, as counts of code
points, mapped back to the input as given; null if `start` is -1.

    let spanOf(
      log: ErrorLog, cursor: SpanCursor, input: String, start: Int, end: Int,
    ): SourceSpan? {
      if (start < 0 || end < start) {
        null
      } else {
        let from = positionIn(log, start);
        let to = endIn(log, start, end);
        let i = seekTo(cursor, input, from);
        new SourceSpan(from, to - from, input.slice(i, seekTo(cursor, input, to)))
      }
    }

Where the spans have got to in the input as given: a string index, and
its count of code points from 0. The parts come in order, so finding
each span's ends from the last walks the input about once.

    class SpanCursor {
      public var index: StringIndex = String.begin;
      public var count: Int = 0;
    }

The string index of code point `to` in `s`, counted from 0, or the end
if `s` is shorter, moving `cursor` there, forward or back.

    let seekTo(cursor: SpanCursor, s: String, to: Int): StringIndex {
      var i = cursor.index;
      var k = cursor.count;
      while (k < to && s.hasIndex(i)) {
        i = s.next(i);
        k += 1;
      }
      while (k > to) {
        i = s.prev(i);
        k -= 1;
      }
      cursor.index = i;
      cursor.count = k;
      i
    }

## Tests

Each part's span, as written, and through what the parser removes:
leading and trailing spaces and controls, and tabs and newlines inside
parts, which spans keep.

    let spansOf(source: UrlSource): String {
      let parts = [
        source.schemeSpan, source.usernameSpan(), source.passwordSpan(), source.hostSpan,
        source.portSpan, source.pathSpan, source.querySpan, source.fragmentSpan,
      ];
      parts.join(" ") { span =>
        if (span == null) { "-" } else { "${span.toString()}[${span.asWritten}]" }
      }
    }

    test("source spans") {
      let cases = [
        "https://user:pa:ss@EXAMPLE.com:443/a/../b?q=1#top",
        "0+5[https] 8+4[user] 13+5[pa:ss] 19+11[EXAMPLE.com] 31+3[443] 34+7[/a/../b] 42+3[q=1] 46+3[top]",
        " \u{1}https://example.com/ ",
        "2+5[https] - - 10+11[example.com] - 21+1[/] - -",
        "ht\ttps://exa\nmple.com/a\tb?q\r#f",
        "0+6[ht\ttps] - - 9+12[exa\nmple.com] - 21+4[/a\tb] 26+1[q] 29+1[f]",
        "https://a@b@c/",
        "0+5[https] 8+3[a@b] - 12+1[c] - 13+1[/] - -",
        "https://h?",
        "0+5[https] - - 8+1[h] - 9+0[] 10+0[] -",
        "http:\\\\h\\p",
        "0+4[http] - - 7+1[h] - 8+2[\\p] - -",
        "mailto:someone@example.com",
        "0+6[mailto] - - - - 7+19[someone@example.com] - -",
        "web+demo:/x",
        "0+8[web+demo] - - - - 9+2[/x] - -",
        "file:///C:/x",
        "0+4[file] - - 7+0[] - 7+5[/C:/x] - -",
        "file://C:/x",
        "0+4[file] - - - - 7+4[C:/x] - -",
        "https://h:/",
        "0+5[https] - - 8+1[h] 10+0[] 10+1[/] - -",
        "https://Bücher.example/ü",
        "0+5[https] - - 8+14[Bücher.example] - 22+2[/ü] - -",
      ];
      for (var k = 0; k < cases.length; k += 2) {
        let got = spansOf(parseUrlSource(cases[k]) orelse panic());
        assert(got == cases[k + 1]) { "${cases[k]}: ${got}" };
      }
    }

Against a base, parts the input didn't write have no span.

    test("source spans against a base") {
      let base = "https://user@example.com/a/b?q#f";
      let cases = [
        "c", "- - - - - 0+1[c] - -",
        "/c", "- - - - - 0+2[/c] - -",
        "?x", "- - - - - - 1+1[x] -",
        "#x", "- - - - - - - 1+1[x]",
        "//h/x", "- - - 2+1[h] - 3+2[/x] - -",
        "\t../c ", "- - - - - 1+4[../c] - -",
      ];
      for (var k = 0; k < cases.length; k += 2) {
        let source = parseUrlSource(cases[k], base) orelse panic();
        assert(spansOf(source) == cases[k + 1]) { "${cases[k]}: ${spansOf(source)}" };
      }
      let relative = parseUrlSource("../c", base) orelse panic();
      assert(relative.url.hrefWithCredentials() == "https://user@example.com/c");
      assert(relative.url.href == "https://example.com/c");
      assert(relative.asWritten() == "../c");
      let rejected: UrlSource? = parseUrlSource("https://exa mple.com") orelse null;
      assert(rejected == null) { "a URL that fails to parse bubbles" };
    }

Validation errors cover what they're about: one code point, a whole
host or port, or the stripped ends, counted in the input as given.

    test("error spans") {
      let cases = [
        "https://exa mple.com", "domain-invalid-code-point 8+12",
        " \thttps://example.com/a\tb| ", "invalid-URL-unit 0+2, invalid-URL-unit 23+1, invalid-URL-unit 25+1",
        "http://example.com:99999/", "port-out-of-range 19+5",
        "http://0x7f.1/", "IPv4-non-decimal-part 7+6",
        "https://user@h\t/", "invalid-URL-unit 14+1, invalid-credentials 12+1",
        "https://h/a\\b", "invalid-reverse-solidus 11+1",
        "https:", "special-scheme-missing-following-solidus 6+0, host-missing 6+0",
      ];
      for (var k = 0; k < cases.length; k += 2) {
        let check = checkUrl(cases[k]) orelse panic();
        let got = check.errors.join(", ") { e =>
          "${e.name} ${e.position.toString()}+${e.length.toString()}"
        };
        assert(got == cases[k + 1]) { "${cases[k]}: ${got}" };
      }
    }
