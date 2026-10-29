// Hrefine's benchmark in C++; see ../run.py, which compiles it with the
// generated sources and runs it.
#include <chrono>
#include <cstdio>
#include <fstream>
#include <functional>
#include <sstream>
#include <string>
#include <vector>
#include "hrefine/init.hpp"

using Clock = std::chrono::steady_clock;
static double seconds = 1.0;

static double since(Clock::time_point start) {
  return std::chrono::duration<double>(Clock::now() - start).count();
}

static std::vector<std::string> readLines(const std::string& folder, const std::string& name) {
  std::ifstream file(folder + "/" + name);
  std::vector<std::string> lines;
  std::string line;
  while (std::getline(file, line)) {
    if (!line.empty()) lines.push_back(line);
  }
  return lines;
}

struct Pair {
  std::string input;
  bool hasBase;
  std::string base;
};

static std::string parse(const Pair& pair) {
  try {
    auto url = pair.hasBase ? hrefine::parseUrl(pair.input, pair.base) : hrefine::parseUrl(pair.input);
    return url->get_href();
  } catch (...) {
    return "fail";
  }
}

static std::string toAscii(const std::string& domain) {
  try {
    return hrefine::domainToAscii(domain);
  } catch (...) {
    return "fail";
  }
}

// Nanoseconds per item, after warming up for `seconds`, running
// over `items` for `seconds` more.
template <typename T>
static double rate(std::function<std::string(const T&)> run, const std::vector<T>& items) {
  size_t sink = 0;
  auto start = Clock::now();
  while (since(start) < seconds) {
    for (const auto& item : items) sink += run(item).size();
  }
  long passes = 0;
  start = Clock::now();
  while (true) {
    for (const auto& item : items) sink += run(item).size();
    passes += 1;
    double elapsed = since(start);
    if (elapsed >= seconds) {
      if (sink == 1) std::printf("%zu\n", sink);
      return elapsed * 1e9 / (passes * items.size());
    }
  }
}

int main(int argc, char** argv) {
  std::string mode = argv[1];
  std::string folder = argv[2];
  if (argc > 3) seconds = std::stod(argv[3]);
  auto t0 = Clock::now();
  hrefine::global_init_init();
  double load = since(t0);
  std::vector<Pair> urls;
  for (const auto& line : readLines(folder, "urls.txt")) {
    auto tab = line.find('\t');
    if (tab == std::string::npos) {
      urls.push_back({line, false, ""});
    } else {
      urls.push_back({line.substr(0, tab), true, line.substr(tab + 1)});
    }
  }
  auto domains = readLines(folder, "domains.txt");
  if (mode == "check") {
    for (const auto& pair : urls) std::printf("%s\n", parse(pair).c_str());
    for (const auto& domain : domains) std::printf("%s\n", toAscii(domain).c_str());
    return 0;
  }
  auto t1 = Clock::now();
  parse({"https://example.com/", false, ""});
  double firstAscii = since(t1);
  auto t2 = Clock::now();
  toAscii("b\xc3\xbc" "cher.example");
  double firstIdna = since(t2);
  double parseNs = rate<Pair>(parse, urls);
  double idnaNs = rate<std::string>(toAscii, domains);
  std::printf(
      "{\"load_ms\": %f, \"first_ascii_ms\": %f, \"first_idna_ms\": %f, \"parse_ns\": %f, \"idna_ns\": %f}\n",
      load * 1e3, firstAscii * 1e3, firstIdna * 1e3, parseNs, idnaNs);
}
