# /// script
# requires-python = ">=3.11"
# ///
"""Benchmarks Hrefine in each language, and measures its size.

Usage, from anywhere in the repo:

    uv run bench/run.py [--runs N] [--seconds S] [--no-build] [LANGUAGE ...]

For each language, this builds the library without its tests (a copy of
src/ without test blocks or generated test files, in bench/build/lib), builds
`bench/<language>/`, checks that it prints `bench/expected.txt` for the URLs
in `urls.txt` and the domains in `domains.txt`, and then runs it `--runs`
times, each in a new process, reporting the median and range of:

- runtime: importing Temper's runtime, in Python, JavaScript, and Lua,
  which any Temper library needs, before the library;
- load: importing or initializing the library;
- first IDNA: the first domain to ASCII of a host beyond ASCII,
  `bücher.example`, after one ASCII URL;
- parse: nanoseconds per URL, parsing each URL in the mix (against its base,
  if it has one) and getting its `hrefWithCredentials` (the exact URL),
  over and over for `--seconds` after warming up as long;
- IDNA: nanoseconds per domain to ASCII of each domain in the mix;

and the size of the generated library, raw and gzipped. Builds run one at a
time, to spare memory. Timing on a busy machine is noisy, so compare runs
made back to back.
"""

import argparse
import gzip
import json
import os
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "bench"
LIB = BENCH / "build" / "lib"
OUT = LIB / "temper.out"
LANGUAGES = ["cpp", "csharp", "java", "js", "lua", "py", "rust"]
NAMES = {"cpp": "C++", "csharp": "C#", "java": "Java", "js": "JavaScript", "lua": "Lua",
         "py": "Python", "rust": "Rust"}


def run(args, cwd=ROOT, env=None, capture=True):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=capture, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))} failed:\n{result.stderr}{result.stdout}")
    return result.stdout


def copy_library():
    """src/ without tests, so sizes and builds leave them out."""
    if LIB.exists():
        shutil.rmtree(LIB / "src", ignore_errors=True)
    (LIB / "src").mkdir(parents=True, exist_ok=True)
    for path in (ROOT / "src").glob("*.temper.md"):
        if path.name.startswith("wpt-"):
            continue
        lines, out, skipping = path.read_text(encoding="utf-8").split("\n"), [], False
        for line in lines:
            if skipping:
                skipping = line != "    }"
            elif line.startswith("    test("):
                skipping = True
            else:
                out.append(line)
        (LIB / "src" / path.name).write_text("\n".join(out), encoding="utf-8")


def build_library(language):
    # Its own work root and ignore file, since the repo's ignores build/.
    (LIB / ".temperignore").write_text("temper.out/\n")
    run(["temper", "build", "-w", str(LIB), "--ignorefile", str(LIB / ".temperignore"),
         "-b", language], cwd=LIB)


def python_env():
    path = os.pathsep.join(str(OUT / "py" / p) for p in ["hrefine", "std", "temper-core"])
    return {**os.environ, "PYTHONPATH": path}


def java_build():
    classes = BENCH / "java" / "build"
    shutil.rmtree(classes, ignore_errors=True)
    sources = [str(p) for lib in ["temper-core", "std", "hrefine"]
               for p in (OUT / "java" / lib / "src" / "main").rglob("*.java")]
    run(["javac", "-nowarn", "-encoding", "UTF-8", "-d", str(classes), *sources,
         str(BENCH / "java" / "Bench.java")])


def js_build():
    # Links the runtime where Node looks for it, as npm's workspaces would.
    scope = OUT / "js" / "node_modules" / "@temperlang"
    scope.mkdir(parents=True, exist_ok=True)
    link = scope / "core"
    if not link.exists():
        link.symlink_to("../../temper-core")


def cpp_build():
    build = BENCH / "cpp" / "build"
    build.mkdir(exist_ok=True)
    cpp = OUT / "cpp"
    std = [str(p) for p in (cpp / "std").glob("*.cpp") if p.name != "main.cpp"]
    objects = []
    # One file at a time, to spare memory.
    for source in [str(cpp / "hrefine" / "init.cpp"), *std, str(BENCH / "cpp" / "bench.cpp")]:
        name = Path(source).parent.name + "_" + Path(source).stem + ".o"
        run(["g++", "-std=c++14", "-O2", "-I", str(cpp), "-c", source, "-o", str(build / name)])
        objects.append(str(build / name))
    run(["g++", "-o", str(build / "bench"), *objects])


COMMANDS = {
    "cpp": (cpp_build, lambda: [str(BENCH / "cpp" / "build" / "bench")]),
    # Without build servers, which would stay running after.
    "csharp": (lambda: run(["dotnet", "build", "-c", "Release", "-v", "q", "--nologo",
                            "-nodeReuse:false", "-p:UseSharedCompilation=false"],
                           cwd=BENCH / "csharp"),
               lambda: ["dotnet", str(BENCH / "csharp" / "bin" / "Release" / "net6.0" / "Bench.dll")]),
    "java": (java_build, lambda: ["java", "-cp", str(BENCH / "java" / "build"), "Bench"]),
    "js": (js_build, lambda: ["node", str(BENCH / "js" / "bench.mjs")]),
    "lua": (lambda: None, lambda: ["lua", str(BENCH / "lua" / "bench.lua")]),
    "py": (lambda: None, lambda: [sys.executable, str(BENCH / "py" / "bench.py")]),
    "rust": (lambda: run(["cargo", "build", "-q", "--release"], cwd=BENCH / "rust"),
             lambda: [str(BENCH / "rust" / "target" / "release" / "bench")]),
}


def library_files(language):
    """The generated library's own code, without tests or source maps."""
    lib = OUT / language / "hrefine"
    patterns = {
        "cpp": ["init.hpp", "init.cpp"],
        "csharp": ["src/*.cs"],
        "java": ["src/main/java/**/*.java"],
        "js": ["*.js"],
        "lua": ["*.lua"],
        "py": ["hrefine/*.py"],
        "rust": ["src/**/*.rs"],
    }[language]
    files = sorted({p for pattern in patterns for p in lib.glob(pattern)})
    return [p for p in files if p.name not in ("main.rs", "main.cpp")]


def sizes(language):
    raw = packed = 0
    for path in library_files(language):
        data = path.read_bytes()
        raw += len(data)
        packed += len(gzip.compress(data, 9))
    return raw, packed


def bench(language, runs, seconds, build_program=True):
    build, command = COMMANDS[language]
    if build_program:
        build()
    env = python_env() if language == "py" else None
    expected = (BENCH / "expected.txt").read_text(encoding="utf-8")
    actual = run([*command(), "check", str(BENCH)], env=env)
    if actual != expected:
        raise RuntimeError(f"{language} printed something other than expected.txt:\n{actual}")
    results = [json.loads(run([*command(), "time", str(BENCH), str(seconds)], env=env))
               for _ in range(runs)]
    return {key: sorted(r[key] for r in results) for key in results[0]}


def number(value):
    """Three significant digits, without an exponent."""
    return f"{float(f'{value:.3g}'):,.{max(0, 2 - int(f'{value:e}'.split('e')[1]))}f}"


def show(values):
    median = number(statistics.median(values))
    if len(values) == 1:
        return median
    return f"{median} ({number(values[0])}–{number(values[-1])})"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("languages", nargs="*", metavar="LANGUAGE", help=", ".join(LANGUAGES))
    parser.add_argument("--runs", type=int, default=5, help="processes per language (5)")
    parser.add_argument("--seconds", type=float, default=1.0,
                        help="seconds per steady-state measurement (1)")
    parser.add_argument("--no-build", action="store_true",
                        help="use the library and programs already built")
    parser.add_argument("--json", type=Path, help="also write the results here")
    args = parser.parse_args()
    languages = args.languages or LANGUAGES
    unknown = set(languages) - set(LANGUAGES)
    if unknown:
        parser.error(f"unknown: {', '.join(sorted(unknown))}")
    if not args.no_build:
        copy_library()
    rows, failed, everything = [], [], {}
    for language in languages:
        try:
            if not args.no_build:
                build_library(language)
            result = bench(language, args.runs, args.seconds, not args.no_build)
        except (RuntimeError, OSError) as error:
            print(f"{language}: error\n{error}", file=sys.stderr)
            failed.append(language)
            continue
        finally:
            if language == "csharp":
                # Temper's own C# build may leave MSBuild nodes running.
                subprocess.run(["dotnet", "build-server", "shutdown"], capture_output=True)
                subprocess.run(["pkill", "-f", "MSBuild.dll /nologo /nodemode:"],
                               capture_output=True)
        raw, packed = sizes(language)
        everything[language] = {**result, "size": raw, "gzipped": packed}
        runtime = show(result["runtime_ms"]) if "runtime_ms" in result else "–"
        rows.append(f"| {NAMES[language]} | {runtime} | {show(result['load_ms'])} | "
                    f"{show(result['first_idna_ms'])} | {show(result['parse_ns'])} | "
                    f"{show(result['idna_ns'])} | {raw / 1000:.0f} KB | {packed / 1000:.0f} KB |")
        print(rows[-1], file=sys.stderr)
    print("| Language | Runtime (ms) | Load (ms) | First IDNA (ms) | Parse (ns/URL) "
          "| IDNA (ns/domain) | Size | Gzipped |")
    print("|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
    if args.json:
        args.json.write_text(json.dumps(everything, indent=2))
    if failed:
        print(f"Failed: {' '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
