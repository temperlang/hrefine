-- A tour of Hrefine, from Lua.
--
-- The same tour exists for each language Hrefine supports, and they all print
-- the same text. See demos/README.md for how to run them.

local hrefine = require("hrefine")
local Url, HostKind, parseUrl, checkUrl = hrefine.Url, hrefine.HostKind, hrefine.parseUrl, hrefine.checkUrl
local UrlSearchParams, UrlPolicy = hrefine.UrlSearchParams, hrefine.UrlPolicy
local parseHost, domainToAscii, domainToUnicode = hrefine.parseHost, hrefine.domainToAscii, hrefine.domainToUnicode
local UrlDisplay, parseUrlSource = hrefine.UrlDisplay, hrefine.parseUrlSource
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

local text = "https://user:pass@EXAMPLE.com:8080/a/../b/./c?q=1#top"  -- snippet: hero
local url = parseUrl(text)  -- snippet: hero, parts
print("input: " .. text)
print("href: " .. url.href)  -- snippet: parts
print("origin: " .. url.origin)  -- snippet: parts
print("protocol: " .. url.protocol)  -- snippet: parts
print("username: " .. url.username)  -- snippet: parts
print("password: " .. url.password)  -- snippet: parts
print("host: " .. url.host)  -- snippet: parts
print("hostname: " .. url.hostname)  -- snippet: parts, hero
print("port: " .. url.port)  -- snippet: parts
print("pathname: " .. url.pathname)  -- snippet: parts
print("search: " .. url.search)  -- snippet: parts
print("hash: " .. url.hash)  -- snippet: parts
-- Typed parts, beside the standard's strings.
print("scheme: " .. url.scheme)  -- snippet: parts
print("port number: " .. url.portNumber)  -- snippet: parts
print("host kind: " .. url.hostKind:toString())  -- snippet: parts
-- The standard's parts are strings, as in JavaScript's URL, so no port is
-- "", and portNumber is null.
local plain = parseUrl("HTTPS://example.com:443")
print("default port: " .. plain.href .. ', port "' .. plain.port .. '", port number '
  .. (null_to_nil(plain.portNumber) or "none"))

section("2. Relative URLs")

-- Parse the base once, then resolve against it.
local guide = parseUrl("https://example.com/docs/guide/intro.html")  -- snippet: base
print("base: " .. guide.href)
for _, relative in ipairs({ "setup.html", "../api/", "/about", "?page=2", "#install", "//cdn.example/lib.js" }) do  -- snippet: base
  print(relative .. " -> " .. guide:resolve(relative).href)  -- snippet: base
end  -- snippet: base
-- Or give the base as a string, parsed on each call.
print("with a string base: " .. parseUrl("faq.html", guide.href).href)  -- snippet: base

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
  local check = checkUrl(input)  -- snippet: errors
  local errors = {}  -- snippet: errors
  for _, error in ipairs(check.errors) do  -- snippet: errors
    errors[#errors + 1] = error:toString()  -- snippet: errors
  end  -- snippet: errors
  local parsed = null_to_nil(check.url)  -- snippet: errors
  print(input .. ": " .. (parsed and parsed.href or "not a URL") .. " (" .. table.concat(errors, ", ") .. ")")  -- snippet: errors
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
-- url:toString() masks credentials, for logs (tostring(url) doesn't call it
-- yet). Hand on href, which keeps them, or drop them first.
print("as a string: " .. url:toString())
print("href, to hand on: " .. url.href)
print("without credentials: " .. url:withoutCredentials().href)
-- eq compares hrefs; == compares tables.
print("same URL: " .. tostring(parseUrl("HTTP://EXAMPLE.COM/a/./b/../c"):eq(parseUrl("http://example.com/a/c"))))
-- strictHref also escapes what RFC 3986 parsers reject, for those that
-- follow it strictly.
local strict = parseUrl("https://example.com/a|b/%zz?q={x}#c^d")  -- snippet: proof
print("strict: " .. strict.href .. " -> " .. strict.strictHref)  -- snippet: proof

section("6. Using it safely")

-- Decide with Hrefine, then hand on href, never the original string.
-- LuaSocket, lua-http, and OpenResty's clients parse URLs their own way.
local allowed = { ["example.com"] = true, ["api.example.com"] = true }

-- The URL to fetch, or why not.
local function check(input)  -- snippet: card
  local url = null_to_nil(Url.parse(input))  -- snippet: card
  if url == nil then return "refuse: not a URL" end  -- snippet: card
  if url.scheme ~= "https" then return "refuse: scheme " .. url.scheme end  -- snippet: card
  -- An IP address isn't a name on the list, however it's written. Each
  -- kind is one table, so == works.
  if url.hostKind ~= HostKind.domain then  -- snippet: card
    return "refuse: " .. url.hostKind:toString() .. " host " .. url.hostname  -- snippet: card
  end  -- snippet: card
  if not allowed[url.hostname] then return "refuse: host " .. url.hostname end  -- snippet: card
  -- With LuaSocket (and LuaSec for https): http.request{ url = url.href,
  -- redirect = false, ... }, never input. Check each redirect the same
  -- way. A hostname doesn't say where DNS sends it.
  return "fetch " .. url.href  -- snippet: card
end  -- snippet: card

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

section("7. Changing parts")

-- The standard's setters, as methods that give a new URL, so a URL that
-- passed a check can't change after. A value that can't be set is ignored,
-- as in JavaScript.
local page = parseUrl("https://example.com/docs?lang=en&q=a+b")
print("page: " .. page.href)
print("with host: " .. page:withHost("example.org:8443").href)
print("with pathname and hash: " .. page:withPathname("/a b"):withHash("top").href)
print("with protocol: " .. page:withProtocol("http").href)
print('port "http", ignored: ' .. page:withPort("http").href)
print("with port number: " .. page:withPortNumber(8443).href)
print("unchanged: " .. page.href)
-- Search parameters: a copy of the query, changed in place, then put back.
local params = page.searchParams
print("q: " .. params:get("q"))
params:append("lang", "fr")
params:set("q", "café & more")
params:remove("missing")
params:sort()
local langs = {}
for _, lang in ipairs(params:getAll("lang")) do
  langs[#langs + 1] = lang
end
print("lang: " .. table.concat(langs, ", "))
for _, entry in ipairs(params:entries()) do
  print(entry.key .. " = " .. entry.value)
end
print("with search params: " .. page:withSearchParams(params).href)
-- Or from pairs of names and values, each a table with key and value.
local pairs_ = { { key = "q", value = "a b" }, { key = "page", value = "2" } }
print("from pairs: " .. UrlSearchParams.fromEntries(pairs_):toString())

section("8. Test cases")

-- Each of web-platform-tests' URL cases gives an input, a base, and the
-- href it must parse to, or "" where parsing must fail. Hrefine's tests run
-- them all, checking every part, and so does the site, in the browser.
local cases = {
  { "http:\\\\foo.com\\", "http://example.org/foo/bar", "http://foo.com/" },
  { "../aaa/test.txt", "http://www.example.com/test", "http://www.example.com/aaa/test.txt" },
  { "http://999999999", "http://other.com/", "http://59.154.201.255/" },
  { "http://192.168.0.257", "http://other.com/", "" },
}
for _, test in ipairs(cases) do  -- snippet: scoreboard
  local input, base, href = test[1], test[2], test[3]  -- snippet: scoreboard
  local url = null_to_nil(Url.parse(input, base))  -- snippet: scoreboard
  local got = url and url.href or ""  -- snippet: scoreboard
  print(input .. " against " .. base .. ": " .. (got == href and "pass" or "fail"))  -- snippet: scoreboard
end  -- snippet: scoreboard

section("9. Policies")

-- A policy does the checks of section 6 in one call, on the parsed URL. Build
-- it once, a rule at a time, and use it for every URL. UrlPolicy.fetch, for
-- URLs a server fetches, is https only, strict, with no credentials and no
-- private, loopback, or other special addresses or names; this one adds
-- example.com or its subdomains. Reasons never show credentials.
local policy = UrlPolicy.fetch:withHosts({ "example.com" }, true)  -- snippet: policy
local inputs = {
  "https://api.example.com/v1/items",
  "http://example.com/",
  "https://example.com@evil.example/",
  "https://127.1/",
  "https://169.254.169.254/latest/meta-data/",
  "https://[::ffff:127.0.0.1]/",
  "https://localhost./",
  "https://ex\u{430}mple.com/",
}
for _, input in ipairs(inputs) do  -- snippet: policy
  local result = policy:check(input)  -- snippet: policy
  local fetched = null_to_nil(result.url)  -- snippet: policy
  if fetched then  -- snippet: policy
    print(input .. ": fetch " .. fetched.href)  -- snippet: policy
  else  -- snippet: policy
    print(input .. ": refuse, " .. result:toString())  -- snippet: policy
  end  -- snippet: policy
end  -- snippet: policy

-- Strict mode refuses what the standard accepts but notes as an error, as
-- cautious parsers do: backslashes, tabs, odd IPv4 forms, and the like.
-- withStrict(true) adds it to a policy.
for _, input in ipairs({ "https://example.com/a b", "http://0x7f.1/", "https://example.com\\a", " https://example.com/" }) do
  local check = checkUrl(input)
  local strictUrl = null_to_nil(check.strictUrl)
  if strictUrl then
    print("strict " .. shown(input) .. ": " .. strictUrl.href)
  else
    local errors = {}
    for _, error in ipairs(check.strictErrors) do
      errors[#errors + 1] = error:toString()
    end
    print("strict " .. shown(input) .. ": refuse, " .. table.concat(errors, ", "))
  end
end

-- Redirect targets: withPathOnly takes only a path, query, or fragment on
-- the base, never another host, however it's written.
local redirects = UrlPolicy.any:withBase(site):withPathOnly(true)
for _, target in ipairs({ "/account?tab=2", "//evil.example/", "/\\evil.example", "/\t/evil.example", "https://example.com/" }) do
  local result = redirects:check(target)
  local next = null_to_nil(result.url)
  print("next=" .. shown(target) .. ": " .. (next and "redirect to " .. next.href or "refuse, " .. result:toString()))
end

section("10. Showing, comparing, and spans")

-- To show people a URL, as browsers' address bars do: hosts in Unicode
-- where browsers would show them (not look-alikes such as Cyrillic а in
-- xn--pple-43d.com), and escapes of non-ASCII text decoded. Never for
-- security decisions, nor for handing on: use href for those.
local display = UrlDisplay.addressBar:withRootSlash(false)  -- snippet: display
for _, input in ipairs({  -- snippet: display
  "https://user@xn--bcher-kva.example/caf%C3%A9?q=%E6%97%A5%E6%9C%AC",  -- snippet: display
  "https://xn--pple-43d.com/",  -- snippet: display
}) do  -- snippet: display
  print("display: " .. display:format(parseUrl(input)))  -- snippet: display
end  -- snippet: display
-- Credentials are left out, as address bars leave them out. Asked for, the
-- username shows, but a password only as ***.
print("with credentials: " .. display:withCredentials(true):format(parseUrl("https://user:pass@example.com/")))

-- The same URL, the same but for the fragment, or the same origin. All
-- compare canonical forms, so case and a default port don't matter.
local intro = parseUrl("https://EXAMPLE.com:443/a/../guide#intro")
local setup = parseUrl("https://example.com/guide#setup")
print("same URL: " .. tostring(intro:eq(setup)))
print("same document: " .. tostring(intro:sameDocument(setup)))
print("same origin: " .. tostring(intro:sameOrigin(parseUrl("https://example.com/about"))))

-- Where each part was written, for editors and linters: never for security
-- decisions, which use source.url. Spans count code points.
local source = parseUrlSource(" https://EXAMPLE.com:443/a/../b?q=1")
print("href: " .. source.url.href)
print("host as written: " .. source.hostSpan.asWritten .. ", at " .. source.hostSpan:toString())
print("path as written: " .. source.pathSpan.asWritten)
for _, error in ipairs(checkUrl("https://exa mple.com").errors) do
  print(error.name .. ": from " .. error.position .. ", " .. error.length .. " long")
end
