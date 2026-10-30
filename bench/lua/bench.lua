-- Hrefine's benchmark in Lua; see ../run.py, which runs it.
local out = arg[0]:match("^(.*)/lua/[^/]*$") .. "/build/lib/temper.out/lua/"
package.path = out .. "?/init.lua;" .. out .. "?.lua;" .. package.path

local mode, folder, secondsArg = arg[1], arg[2], arg[3]
local seconds = tonumber(secondsArg or "1")
local clock = os.clock -- CPU time, the best Lua's standard library has

-- Temper's runtime first, so the library's own load is timed alone.
local t0 = clock()
require("temper-core")
local t1 = clock()
local hrefine = require("hrefine")
local load = clock() - t1
local runtime = t1 - t0

local function readLines(name)
  local lines = {}
  for line in io.lines(folder .. "/" .. name) do
    if line ~= "" then lines[#lines + 1] = line end
  end
  return lines
end

local urls = {}
for _, line in ipairs(readLines("urls.txt")) do
  local input, base = line:match("^([^\t]*)\t(.*)$")
  urls[#urls + 1] = input and { input, base } or { line, nil }
end
local domains = readLines("domains.txt")

local function parse(pair)
  local ok, href = pcall(function() return hrefine.parseUrl(pair[1], pair[2]).hrefWithCredentials end)
  return ok and href or "fail"
end

local function toAscii(domain)
  local ok, ascii = pcall(hrefine.domainToAscii, domain)
  return ok and ascii or "fail"
end

-- Nanoseconds per item, after warming up for `seconds`, running over
-- `items` for `seconds` more.
local function rate(run, items)
  local finish = clock() + seconds
  while clock() < finish do
    for _, item in ipairs(items) do run(item) end
  end
  local passes, start = 0, clock()
  while true do
    for _, item in ipairs(items) do run(item) end
    passes = passes + 1
    local elapsed = clock() - start
    if elapsed >= seconds then return elapsed * 1e9 / (passes * #items) end
  end
end

if mode == "check" then
  for _, pair in ipairs(urls) do print(parse(pair)) end
  for _, domain in ipairs(domains) do print(toAscii(domain)) end
else
  local t1 = clock()
  parse({ "https://example.com/", nil })
  local t2 = clock()
  toAscii("bücher.example")
  local t3 = clock()
  print(string.format(
    '{"runtime_ms": %.6f, "load_ms": %.6f, "first_ascii_ms": %.6f, "first_idna_ms": %.6f, "parse_ns": %.1f, "idna_ns": %.1f}',
    runtime * 1e3, load * 1e3, (t2 - t1) * 1e3, (t3 - t2) * 1e3, rate(parse, urls), rate(toAscii, domains)))
end
