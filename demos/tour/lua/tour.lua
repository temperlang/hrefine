-- A tour of Hrefine, from Lua.
--
-- The same tour exists for each language Hrefine supports, and they all print
-- the same text. See demos/README.md for how to run them.

local hrefine = require("hrefine")
local Url, parseUrl = hrefine.Url, hrefine.parseUrl
local domainToAscii, domainToUnicode = hrefine.domainToAscii, hrefine.domainToUnicode

local function section(title)
  print()
  print("## " .. title)
end

-- Tabs and newlines made visible.
local function shown(text)
  return (text:gsub("\t", "\\t"):gsub("\n", "\\n"))
end

-- The URL, or nil if it isn't one.
local function tryParse(text, base)
  local ok, url = pcall(parseUrl, text, base)
  if ok then return url end
  return nil
end

print("# Hrefine tour")

section("1. Parsing and reading parts")

local text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top"
local url = parseUrl(text)
print("input: " .. text)
print("href: " .. url.href)
print("origin: " .. url.origin)
print("protocol: " .. url.protocol)
print("username: " .. url.username)
print("password: " .. url.password)
print("host: " .. url.host)
print("hostname: " .. url.hostname)
print("port: " .. url.port)
print("pathname: " .. url.pathname)
print("search: " .. url.search)
print("hash: " .. url.hash)
-- Every part is a string, as in JavaScript's URL, so no port is "".
local plain = parseUrl("HTTPS://example.com:443")
print("default port: " .. plain.href .. ', port "' .. plain.port .. '"')

section("2. Relative URLs")

local base = "https://example.com/docs/guide/intro.html"
print("base: " .. base)
for _, relative in ipairs({ "setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js" }) do
  -- The base is a string, parsed again on each call.
  print(relative .. " -> " .. parseUrl(relative, base).href)
end
-- Url.parse is the same as parseUrl, as in JavaScript's URL.parse.
print("Url.parse: " .. Url.parse("setup.html", base).href)
-- A Url can't be a base itself, so pass its href.
local guide = parseUrl(base)
print("from a Url: " .. parseUrl("faq.html", guide.href).href)

section("3. Failures")

-- Input that isn't a URL raises an error, which pcall catches. The error is
-- Temper's bubble, whose message is only "Bubble", so it says nothing of
-- why.
for _, case in ipairs({
  { "https://exa mple.com" },
  { "http://[::1" },
  { "https://example.com:99999" },
  { "setup.html" },
  { "setup.html", "not a base" },
}) do
  local input, against = case[1], case[2]
  local label = against and (input .. " against " .. against) or (input .. ", without a base")
  if pcall(parseUrl, input, against) then
    print(label .. ": parsed")
  else
    print(label .. ": not a URL")
  end
end
-- Or wrap it, as tryParse above does, for nil in place of failure.
print("as an optional: " .. (tryParse("https://exa mple.com") == nil and "nothing" or "a URL"))

section("4. International domain names")

-- Hosts go to ASCII, as browsers send them.
local idn = parseUrl("https://Bücher.example/straße?q=ü")
print("hostname: " .. idn.hostname)
print("href: " .. idn.href)
for _, domain in ipairs({ "Bücher.Example", "faß.de", "☕.example", "xn--tešla" }) do
  local ok, ascii = pcall(domainToAscii, domain)
  if ok then
    print("to ASCII: " .. domain .. " -> " .. ascii)
  else
    print("to ASCII: " .. domain .. " fails")
  end
end
-- And back to Unicode, for showing; it never fails. Decide on the ASCII
-- form: the second is a Cyrillic а, not apple.com.
for _, domain in ipairs({ "xn--bcher-kva.example", "xn--pple-43d.com" }) do
  print("to Unicode: " .. domain .. " -> " .. domainToUnicode(domain))
end

section("5. Serializing with href")

-- href is the standard's canonical form, which other parsers read alike.
for _, input in ipairs({
  "HTTP://EXAMPLE.COM/a/./b/../c",
  "https:\\\\example.com\\path",
  "http://0x7f.1/",
  "https://[0:0::1]:443/",
  "https://example.com/a b?c d#e f",
  " https://exa\tmple.com/\n",
}) do
  print(shown(input) .. " -> " .. parseUrl(input).href)
end
-- url:toString() is href too, but tostring(url) isn't.
print("as a string: " .. url:toString())

section("6. Using it safely")

-- Decide with Hrefine, then hand on href, never the original string.
-- LuaSocket, lua-http, and OpenResty's clients parse URLs their own way.
local allowed = { ["example.com"] = true, ["api.example.com"] = true }

-- The URL to fetch, or why not.
local function check(input)
  local url = tryParse(input)
  if url == nil then return "refuse: not a URL" end
  if url.protocol ~= "https:" then return "refuse: protocol " .. url.protocol end
  if not allowed[url.hostname] then return "refuse: host " .. url.hostname end
  -- With LuaSocket (and LuaSec for https): http.request{ url = url.href,
  -- redirect = false, ... }, never input. Check each redirect the same
  -- way. A hostname doesn't say where DNS sends it.
  return "fetch " .. url.href
end

for _, input in ipairs({
  "https://api.example.com/v1/items",
  "https://example.com\\@evil.example/",
  "https://evil.example#@example.com",
  "https://0x7f.1/admin",
  "http://example.com/",
  "javascript:alert(1)",
  "https://exa mple.com",
}) do
  print(input .. ": " .. check(input))
end

-- A server redirecting to a `next` parameter: resolve it against your own
-- origin, and redirect only if the origin stays the same. In OpenResty:
-- return ngx.redirect(url.href).
local site = "https://example.com/"
for _, target in ipairs({ "/account", "//evil.example/", "/\\evil.example" }) do
  local url = tryParse(target, site)
  if url ~= nil and url.origin == "https://example.com" then
    print("next=" .. target .. ": redirect to " .. url.href)
  else
    print("next=" .. target .. ": refuse, " .. (url and url.origin or "not a URL"))
  end
end
