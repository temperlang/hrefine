-- A tour of Hrefine, from Lua.
--
-- The same tour exists for each language Hrefine supports, and they all print
-- the same text. See demos/README.md for how to run them.

local hrefine = require("hrefine")
local Url, HostKind, parseUrl, checkUrl = hrefine.Url, hrefine.HostKind, hrefine.parseUrl, hrefine.checkUrl
local parseHost, domainToAscii, domainToUnicode = hrefine.parseHost, hrefine.domainToAscii, hrefine.domainToUnicode
-- Temper's runtime gives temper.null, not nil, for no value, so null_to_nil
-- turns it into nil.
local temper = require("temper-core")
local null_to_nil = temper.null_to_nil

local function section(title)
  print()
  print("## " .. title)
end

-- Tabs and newlines made visible.
local function shown(text)
  return (text:gsub("\t", "\\t"):gsub("\n", "\\n"))
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
-- Typed parts, beside the standard's strings.
print("scheme: " .. url.scheme)
print("port number: " .. url.portNumber)
print("host kind: " .. url.hostKind:toString())
-- The standard's parts are strings, as in JavaScript's URL, so no port is
-- "", and portNumber is null.
local plain = parseUrl("HTTPS://example.com:443")
print("default port: " .. plain.href .. ', port "' .. plain.port .. '", port number '
  .. (null_to_nil(plain.portNumber) or "none"))

section("2. Relative URLs")

-- Parse the base once, then resolve against it.
local guide = parseUrl("https://example.com/docs/guide/intro.html")
print("base: " .. guide.href)
for _, relative in ipairs({ "setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js" }) do
  print(relative .. " -> " .. guide:resolve(relative).href)
end
-- Or give the base as a string, parsed on each call.
print("with a string base: " .. parseUrl("faq.html", guide.href).href)

section("3. Failures")

-- checkUrl says why input isn't a URL, with the standard's names for
-- what's wrong and where, counted in code points from 0. The last error is
-- why it failed. Some errors don't stop a URL from parsing, as browsers
-- accept it.
for _, input in ipairs({
  "https://exa mple.com",
  "http://[::1",
  "https://example.com:99999",
  "setup.html",
  "https:example.com/a b",
}) do
  local check = checkUrl(input)
  local errors = {}
  for _, error in ipairs(check.errors) do
    errors[#errors + 1] = error:toString()
  end
  local parsed = null_to_nil(check.url)
  print(input .. ": " .. (parsed and parsed.href or "not a URL") .. " (" .. table.concat(errors, ", ") .. ")")
end
-- Url.parse gives null where parseUrl raises, and Url.canParse says only
-- whether it would parse, as in JavaScript.
print("nullable parse: " .. (null_to_nil(Url.parse("setup.html")) == nil and "nothing" or "a URL"))
print("can parse: " .. tostring(Url.canParse("setup.html")))
-- parseUrl raises an error, which pcall catches. It's Temper's bubble,
-- whose message is only "Bubble", so checkUrl says why.
if pcall(parseUrl, "setup.html") then
  print("throwing parse: parsed")
else
  print("throwing parse: throws")
end

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
-- eq compares hrefs; == compares tables.
print("same URL: " .. tostring(parseUrl("HTTP://EXAMPLE.COM/a/./b/../c"):eq(parseUrl("http://example.com/a/c"))))

section("6. Using it safely")

-- Decide with Hrefine, then hand on href, never the original string.
-- LuaSocket, lua-http, and OpenResty's clients parse URLs their own way.
local allowed = { ["example.com"] = true, ["api.example.com"] = true }

-- The URL to fetch, or why not.
local function check(input)
  local url = null_to_nil(Url.parse(input))
  if url == nil then return "refuse: not a URL" end
  if url.scheme ~= "https" then return "refuse: scheme " .. url.scheme end
  -- An IP address isn't a name on the list, however it's written. Each
  -- kind is one table, so == works.
  if url.hostKind ~= HostKind.domain then
    return "refuse: " .. url.hostKind:toString() .. " host " .. url.hostname
  end
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

-- Check hosts from configuration with parseHost, which domainToAscii isn't
-- for: it passes all three.
for _, input in ipairs({ "example.com", "0x7f.1", "exa mple.com" }) do
  local ok, host = pcall(parseHost, input)
  if ok then
    print("host " .. input .. ": " .. host.kind:toString() .. " " .. host.serialized)
  else
    print("host " .. input .. ": not a host")
  end
end

-- A server redirecting to a `next` parameter: resolve it against your own
-- site, and redirect only to the same origin. In OpenResty:
-- return ngx.redirect(url.href).
local site = parseUrl("https://example.com/")
for _, target in ipairs({ "/account", "//evil.example/", "/\\evil.example", "//[::1" }) do
  local next = null_to_nil(site:tryResolve(target))
  if next ~= nil and next:sameOrigin(site) then
    print("next=" .. target .. ": redirect to " .. next.href)
  else
    print("next=" .. target .. ": refuse, " .. (next and next.origin or "not a URL"))
  end
end
