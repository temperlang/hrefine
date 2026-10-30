# Demos

## Tour

`tour/` shows Hrefine in each supported language: parsing and reading a
URL's parts, typed ones too, resolving against a parsed base, failures
and why (`checkUrl`'s validation errors), international domain names,
serializing with `href`, and using it safely (deciding with Hrefine, by
scheme, host kind, and origin, then handing on `href`, with that
language's usual HTTP clients and servers shown in comments). Every version prints the same text,
`tour/expected.txt`, so the tours double as a cross-language test.

First build the libraries from the repo's top, with
[Temper](https://temperlang.dev/):

    temper build -b cpp -b csharp -b java -b js -b lua -b py -b rust

Each tour uses the generated library in `temper.out/` by relative path. Run
one from its directory:

| Language | In `tour/…` | Commands |
|---|---|---|
| C++ | `cpp` | `cmake -B build && cmake --build build && ./build/tour` |
| C# | `csharp` | `dotnet run` |
| Java | `java` | `./gradlew run` |
| JavaScript | `js` | `npm ci && npm start` |
| Lua | `lua` | `lua -l paths tour.lua` |
| Python | `py` | `uv run tour.py` |
| Rust | `rust` | `cargo run` |

Or run them all and compare each with `expected.txt`:

    uv run demos/run.py [LANGUAGE ...]

CI does the same for each backend, after its tests.

Java's Gradle build compiles the generated sources along with the tour,
because the generated Maven projects expect a JDK 8 toolchain and release
signing, and prints in UTF-8 whatever the locale. Python's tour names
Temper's runtime as a dependency too, so it comes from `temper.out/`, not
from older releases on PyPI.
