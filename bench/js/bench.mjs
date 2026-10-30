// Hrefine's benchmark in JavaScript; see ../run.py, which runs it.
import { readFileSync } from "node:fs";

const [mode, folder, secondsArg] = process.argv.slice(2);
const seconds = Number(secondsArg ?? 1);
// Temper's runtime first, so the library's own load is timed alone.
const out = new URL("../build/lib/temper.out/js/", import.meta.url);
const t0 = performance.now();
await import(new URL("temper-core/index.js", out));
const t1 = performance.now();
const hrefine = await import(new URL("hrefine/index.js", out));
const load = performance.now() - t1;
const runtime = t1 - t0;

const readLines = (name) => readFileSync(`${folder}/${name}`, "utf8").split("\n").filter((l) => l);
const urls = readLines("urls.txt").map((line) => {
  const [input, base] = line.split("\t");
  return [input, base ?? null];
});
const domains = readLines("domains.txt");

function parse([input, base]) {
  try {
    return hrefine.parseUrl(input, base).hrefWithCredentials;
  } catch {
    return "fail";
  }
}

function toAscii(domain) {
  try {
    return hrefine.domainToAscii(domain);
  } catch {
    return "fail";
  }
}

// Nanoseconds per item, after warming up for `seconds`, running
// over `items` for `seconds` more.
function rate(run, items) {
  let sink = 0;
  let end = performance.now() + seconds * 1000;
  while (performance.now() < end) {
    for (const item of items) sink += run(item).length;
  }
  let passes = 0;
  const start = performance.now();
  for (;;) {
    for (const item of items) sink += run(item).length;
    passes += 1;
    const elapsed = performance.now() - start;
    if (elapsed >= seconds * 1000) {
      if (sink < 0) console.log(sink);
      return (elapsed * 1e6) / (passes * items.length);
    }
  }
}

if (mode === "check") {
  for (const pair of urls) console.log(parse(pair));
  for (const domain of domains) console.log(toAscii(domain));
} else {
  const t1 = performance.now();
  parse(["https://example.com/", null]);
  const t2 = performance.now();
  toAscii("bücher.example");
  const t3 = performance.now();
  console.log(JSON.stringify({
    runtime_ms: runtime, load_ms: load, first_ascii_ms: t2 - t1, first_idna_ms: t3 - t2,
    parse_ns: rate(parse, urls), idna_ns: rate(toAscii, domains),
  }));
}
