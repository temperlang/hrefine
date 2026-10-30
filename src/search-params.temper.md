# Search Parameters

The URL Standard's [`application/x-www-form-urlencoded`](https://url.spec.whatwg.org/#application/x-www-form-urlencoded)
section, and its [`URLSearchParams`](https://url.spec.whatwg.org/#interface-urlsearchparams)
class: a query, as in `?q=a+b&page=2`, read as a list of names and
values, in order, which may repeat.

## Parsing

The [`application/x-www-form-urlencoded`
parser](https://url.spec.whatwg.org/#concept-urlencoded-parser) splits
`input` at each `&`, skipping empty pieces, then each piece at its first
`=` into a name and a value (empty if there's no `=`). In each, `+` is a
space, and percent-escapes are decoded as UTF-8, with bad bytes as
U+FFFD.

    let parseUrlencoded(input: String, out: ListBuilder<Pair<String, String>>): Void {
      var start = String.begin;
      while (true) {
        var end = start;
        var equals = input.end;
        while (input.hasIndex(end) && input[end] != char'&') {
          if (equals == input.end && input[end] == char'=') {
            equals = end;
          }
          end = input.next(end);
        }
        if (end > start) {
          let name = if (equals < end) { input.slice(start, equals) } else { input.slice(start, end) };
          let value = if (equals < end) { input.slice(input.next(equals), end) } else { "" };
          out.add(new Pair(formDecode(name), formDecode(value)));
        }
        if (!input.hasIndex(end)) {
          break;
        }
        start = input.next(end);
      }
    }

A name or value with `+` as space, percent-decoded. Most have neither
`+` nor `%`, and stay as they are.

    let formDecode(s: String): String {
      var plain = true;
      for (var i = String.begin; plain && s.hasIndex(i); i = s.next(i)) {
        let c = s[i];
        plain = c != char'+' && c != char'%';
      }
      if (plain) {
        s
      } else {
        let spaced = if (s.split("+").length == 1) { s } else { s.split("+").join(" ") { p => p } };
        utf8Decode(percentDecode(spaced))
      }
    }

## Serializing

The [`application/x-www-form-urlencoded`
serializer](https://url.spec.whatwg.org/#concept-urlencoded-serializer):
each name and value percent-encoded with the form set, but for spaces,
which become `+`, joined by `=` and `&`.

    let serializeUrlencoded(list: Listed<Pair<String, String>>): String {
      let out = new StringBuilder();
      for (var k = 0; k < list.length; k += 1) {
        if (k > 0) {
          out.append("&");
        }
        let pair = list[k];
        formEncodeOnto(out, pair.key);
        out.append("=");
        formEncodeOnto(out, pair.value);
      }
      out.toString()
    }

    let formEncodeOnto(out: StringBuilder, s: String): Void {
      for (var i = String.begin; s.hasIndex(i); i = s.next(i)) {
        let c = s[i];
        if (c == char' ') {
          out.append("+");
        } else {
          percentEncodeOnto(out, c, formSet);
        }
      }
    }

## Search Parameters

As JavaScript's `URLSearchParams`, with its names: a list of names and
values, from a query string, which methods read and change in place.
Unlike JavaScript's, it isn't tied to a URL: a URL's `searchParams`
gives a new one each time, and `url.withSearchParams(params)` gives a
URL with them as its query.

    export class UrlSearchParams {
      private var list: ListBuilder<Pair<String, String>>;

Parses `init`, without a leading `?` if it has one, as in
`new UrlSearchParams("?q=a+b")`, or makes an empty list.

      public constructor(init: String = "") {
        list = new ListBuilder<Pair<String, String>>();
        parseUrlencoded(withoutLeading(init, char'?'), list);
      }

How many name and value pairs there are, counting repeats.

      public get size(): Int { list.length }

Adds a pair at the end.

      public append(name: String, value: String): Void {
        list.add(new Pair(name, value));
      }

Removes every pair with this name, or, given a value, every pair with
this name and that value. JavaScript's `delete`, named `remove` since
`delete` is a C++ keyword (see the plan's API notes).

      public remove(name: String, value: String? = null): Void {
        // A loop, not `filter`: Temper's C# backend loses an optional
        // parameter that a closure uses (as of 2026-10-30).
        let next = new ListBuilder<Pair<String, String>>();
        for (var k = 0; k < list.length; k += 1) {
          let p = list[k];
          if (p.key != name || (value != null && p.value != value)) {
            next.add(p);
          }
        }
        list = next;
      }

The value of the first pair with this name, or null if there's none,
and every such value, in order.

      public get(name: String): String? {
        var found: String? = null;
        for (var k = 0; found == null && k < list.length; k += 1) {
          if (list[k].key == name) {
            found = list[k].value;
          }
        }
        found
      }

      public getAll(name: String): List<String> {
        let values = new ListBuilder<String>();
        for (var k = 0; k < list.length; k += 1) {
          if (list[k].key == name) {
            values.add(list[k].value);
          }
        }
        values.toList()
      }

Whether there's a pair with this name, or, given a value, with both.

      public has(name: String, value: String? = null): Boolean {
        var found = false;
        for (var k = 0; !found && k < list.length; k += 1) {
          let p = list[k];
          found = p.key == name && (value == null || p.value == value);
        }
        found
      }

Sets the first pair with this name to this value, and removes the rest
with the name, or adds a pair at the end if there's none.

      public set(name: String, value: String): Void {
        let next = new ListBuilder<Pair<String, String>>();
        var done = false;
        for (var k = 0; k < list.length; k += 1) {
          let p = list[k];
          if (p.key != name) {
            next.add(p);
          } else if (!done) {
            next.add(new Pair(name, value));
            done = true;
          }
        }
        if (!done) {
          next.add(new Pair(name, value));
        }
        list = next;
      }

Sorts the pairs by name, keeping pairs with the same name in order. As
in JavaScript, names compare by UTF-16 code units, so `🌈` sorts before
`ﬃ`, though its code point is higher.

      public sort(): Void {
        list.sort { (a: Pair<String, String>, b: Pair<String, String>): Int =>
          compareCodeUnits(a.key, b.key)
        };
      }

The pairs, as Temper's `Pair`s (each `key` a name), and the names and
values, each a new list, in order, for iterating over.

      public entries(): List<Pair<String, String>> { list.toList() }

      public keys(): List<String> { list.map { (p: Pair<String, String>): String => p.key } }

      public values(): List<String> { list.map { (p: Pair<String, String>): String => p.value } }

The pairs as a query, without a `?`, as `q=a+b&page=2`.

      public toString(): String { serializeUrlencoded(list) }
    }

## Comparing by Code Units

Compares strings as lists of UTF-16 code units, as JavaScript does. Code
points compare the same way, but for those past U+FFFF, which UTF-16
writes as surrogates, U+D800 to U+DFFF, so they sort before U+E000 to
U+FFFF.

    let compareCodeUnits(a: String, b: String): Int {
      var i = String.begin;
      var j = String.begin;
      var order = 0;
      while (order == 0 && a.hasIndex(i) && b.hasIndex(j)) {
        order = firstUnit(a[i]) - firstUnit(b[j]);
        if (order == 0) {
          order = a[i] - b[j];
        }
        i = a.next(i);
        j = b.next(j);
      }
      if (order != 0) {
        order
      } else if (a.hasIndex(i)) {
        1
      } else if (b.hasIndex(j)) {
        -1
      } else {
        0
      }
    }

    let firstUnit(c: Int): Int {
      if (c < 0x10000) { c } else { 0xD800 + ((c - 0x10000) >> 10) }
    }

## Tests

Ported from web-platform-tests' `urlsearchparams-*.any.js` and
`url-searchparams.any.js` (vendored in `tests/wpt/`), as far as they
don't test JavaScript's own conversions (`null` and numbers as names).
Each `+ ''` there is `toString()` here.

    test("Search parameters: serializing (urlsearchparams-stringifier)") {
      let params = new UrlSearchParams();
      params.append("a", "b c");
      assert(params.toString() == "a=b+c");
      params.remove("a");
      params.append("a b", "c");
      assert(params.toString() == "a+b=c");
      let empty = new UrlSearchParams();
      empty.append("a", "");
      empty.append("a", "");
      empty.append("", "b");
      empty.append("", "");
      assert(empty.toString() == "a=&a=&=b&=");
      let cases = [
        "b+c", "a=b%2Bc", "=", "a=%3D", "&", "a=%26", "*-._", "a=*-._", "b%c", "a=b%25c",
        "b\u{0}c", "a=b%00c", "b\u{1F4A9}c", "a=b%F0%9F%92%A9c", "c\rd", "a=c%0Dd",
      ];
      for (var k = 0; k < cases.length; k += 2) {
        let p = new UrlSearchParams();
        p.append("a", cases[k]);
        assert(p.toString() == cases[k + 1]) { p.toString() };
      }
      let round = [
        "a=b&c=d&&e&&", "a=b&c=d&e=",
        "a = b &a=b&c=d%20", "a+=+b+&a=b&c=d+",
        "a=&a=b", "a=&a=b",
        "b=%2sf%2a", "b=%252sf*",
        "b=%2%2af%2a", "b=%252*f*",
        "b=%%2a", "b=%25*",
        "id=0&value=%", "id=0&value=%25",
      ];
      for (var k = 0; k < round.length; k += 2) {
        let text = new UrlSearchParams(round[k]).toString();
        assert(text == round[k + 1]) { "${round[k]}: ${text}" };
      }
    }

    test("Search parameters: reading (get, getAll, has, size)") {
      let params = new UrlSearchParams("a=b&c=d&a=e&=f&g&");
      assert(params.get("a") == "b" && params.get("c") == "d" && params.get("x") == null);
      assert(params.get("") == "f" && params.get("g") == "");
      assert(params.getAll("a").join(",") { s => s } == "b,e");
      assert(params.getAll("x").isEmpty);
      assert(params.has("a") && params.has("") && !params.has("x"));
      assert(params.has("a", "e") && !params.has("a", "c") && params.has("g", ""));
      assert(params.size == 5);
      assert(params.keys().join(",") { s => s } == "a,c,a,,g");
      assert(params.values().join(",") { s => s } == "b,d,e,f,");
      assert(new UrlSearchParams("?a=1").get("a") == "1");
      assert(new UrlSearchParams("??a=1").get("?a") == "1");
    }

    test("Search parameters: changing (append, remove, set)") {
      let params = new UrlSearchParams("a=a&b=b&a=a&c=c");
      params.remove("a");
      assert(params.toString() == "b=b&c=c");
      let two = new UrlSearchParams();
      two.append("a", "b");
      two.append("a", "c");
      two.append("a", "d");
      two.remove("a", "c");
      assert(two.toString() == "a=b&a=d");
      let set = new UrlSearchParams("a=b&c=d&a=e");
      set.set("a", "B");
      assert(set.toString() == "a=B&c=d");
      set.set("e", "f");
      assert(set.toString() == "a=B&c=d&e=f");
      let size = new UrlSearchParams("a=1&b=2&a=3");
      size.remove("a");
      assert(size.size == 1);
      size.append("b", "4");
      assert(size.size == 2);
    }

A URL's parameters, and a URL with them; JavaScript's live link is two
steps here: read `searchParams`, change them, and `withSearchParams`.

    test("Search parameters: in a URL (url-searchparams, urlsearchparams-delete)") {
      let url = parseUrl("http://www.example.com/?a=b,c") orelse panic();
      let params = url.searchParams;
      assert(params.toString() == "a=b%2Cc");
      params.append("x", "y");
      assert(url.withSearchParams(params).href == "http://www.example.com/?a=b%2Cc&x=y");
      let file = parseUrl("http://example.org/file?a=b&c=d") orelse panic();
      let changed = file.withSearch("e=f&g=h");
      assert(changed.search == "?e=f&g=h" && changed.searchParams.toString() == "e=f&g=h");
      assert(file.withSearch("?e=f&g=h").search == "?e=f&g=h");
      let more = changed.searchParams;
      more.append("i", " j ");
      more.set("e", "updated");
      assert(changed.withSearchParams(more).search == "?e=updated&g=h&i=+j+");
      let doubled = parseUrl("http://example.org/file??a=b&c=d") orelse panic();
      assert(doubled.search == "??a=b&c=d");
      assert(doubled.searchParams.toString() == "%3Fa=b&c=d");
      assert(file.withSearch("?").searchParams.size == 0);
      let both = parseUrl("http://example.com/?param1&param2") orelse panic();
      let gone = both.searchParams;
      gone.remove("param1");
      gone.remove("param2");
      let cleared = both.withSearchParams(gone);
      assert(cleared.href == "http://example.com/" && cleared.search == "");
      let opaque = parseUrl("data:space    ?test#test") orelse panic();
      assert(opaque.searchParams.has("test"));
      let none = opaque.searchParams;
      none.remove("test");
      let stripped = opaque.withSearchParams(none);
      assert(stripped.pathname == "space   %20" && stripped.href == "data:space   %20#test") {
        stripped.href
      };
    }
