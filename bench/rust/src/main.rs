//! Hrefine's benchmark in Rust; see ../run.py, which runs it.
use std::time::Instant;

static mut SECONDS: f64 = 1.0;

fn seconds() -> f64 {
    unsafe { SECONDS }
}

fn read_lines(folder: &str, name: &str) -> Vec<String> {
    std::fs::read_to_string(format!("{folder}/{name}"))
        .unwrap()
        .split('\n')
        .filter(|line| !line.is_empty())
        .map(String::from)
        .collect()
}

fn parse(pair: &(String, Option<String>)) -> String {
    match hrefine::parse_url(pair.0.as_str(), pair.1.as_deref()) {
        Ok(url) => url.href_with_credentials().to_string(),
        Err(_) => "fail".to_string(),
    }
}

fn to_ascii(domain: &String) -> String {
    match hrefine::domain_to_ascii(domain.as_str()) {
        Ok(ascii) => ascii.to_string(),
        Err(_) => "fail".to_string(),
    }
}

/// Nanoseconds per item, after warming up for `seconds`, running over
/// `items` for `seconds` more.
fn rate<T>(run: fn(&T) -> String, items: &[T]) -> f64 {
    let mut sink = 0;
    let start = Instant::now();
    while start.elapsed().as_secs_f64() < seconds() {
        for item in items {
            sink += run(item).len();
        }
    }
    let mut passes = 0;
    let start = Instant::now();
    loop {
        for item in items {
            sink += run(item).len();
        }
        passes += 1;
        let elapsed = start.elapsed().as_secs_f64();
        if elapsed >= seconds() {
            if sink == 1 {
                println!("{sink}");
            }
            return elapsed * 1e9 / (passes * items.len()) as f64;
        }
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let (mode, folder) = (args[1].as_str(), args[2].as_str());
    if let Some(s) = args.get(3) {
        unsafe { SECONDS = s.parse().unwrap() };
    }
    let t0 = Instant::now();
    hrefine::init(None).unwrap();
    let load = t0.elapsed().as_secs_f64();
    let urls: Vec<(String, Option<String>)> = read_lines(folder, "urls.txt")
        .into_iter()
        .map(|line| match line.split_once('\t') {
            Some((input, base)) => (input.to_string(), Some(base.to_string())),
            None => (line, None),
        })
        .collect();
    let domains = read_lines(folder, "domains.txt");
    if mode == "check" {
        for pair in &urls {
            println!("{}", parse(pair));
        }
        for domain in &domains {
            println!("{}", to_ascii(domain));
        }
        return;
    }
    let t1 = Instant::now();
    parse(&("https://example.com/".to_string(), None));
    let first_ascii = t1.elapsed().as_secs_f64();
    let t2 = Instant::now();
    to_ascii(&"bücher.example".to_string());
    let first_idna = t2.elapsed().as_secs_f64();
    let parse_ns = rate(parse, &urls);
    let idna_ns = rate(to_ascii, &domains);
    println!(
        "{{\"load_ms\": {}, \"first_ascii_ms\": {}, \"first_idna_ms\": {}, \"parse_ns\": {}, \"idna_ns\": {}}}",
        load * 1e3,
        first_ascii * 1e3,
        first_idna * 1e3,
        parse_ns,
        idna_ns
    );
}
