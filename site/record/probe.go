// Reads URLs with Go's net/url, for site/record/record.py.
//
// Each input line is base64 of the input, a space, and base64 of the base
// (or "-" for none). Prints one JSON line per input line.
// Run: go run probe.go
package main

import (
	"bufio"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/url"
	"os"
	"runtime"
	"strings"
)

type result struct {
	Ok     bool    `json:"ok"`
	Scheme *string `json:"scheme,omitempty"`
	Host   *string `json:"host,omitempty"`
	Href   *string `json:"href,omitempty"`
	Error  string  `json:"error,omitempty"`
}

func decode(text string) string {
	data, err := base64.StdEncoding.DecodeString(text)
	if err != nil {
		panic(err)
	}
	return string(data)
}

func parse(input string, base *string) result {
	var u *url.URL
	var err error
	if base == nil {
		u, err = url.Parse(input)
	} else {
		var b *url.URL
		b, err = url.Parse(*base)
		if err == nil {
			u, err = b.Parse(input)
		}
	}
	if err != nil {
		return result{Error: err.Error()}
	}
	scheme, host, href := u.Scheme, u.Hostname(), u.String()
	r := result{Ok: true, Scheme: &scheme, Href: &href}
	// No authority at all, as for javascript:alert(1), is no host.
	if u.Host != "" || strings.HasPrefix(u.String(), u.Scheme+"://") {
		r.Host = &host
	}
	return r
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "--version" {
		fmt.Println(runtime.Version())
		return
	}
	scanner := bufio.NewScanner(os.Stdin)
	out := json.NewEncoder(os.Stdout)
	out.SetEscapeHTML(false)
	for scanner.Scan() {
		parts := strings.Split(scanner.Text(), " ")
		input := decode(parts[0])
		var base *string
		if parts[1] != "-" {
			b := decode(parts[1])
			base = &b
		}
		out.Encode(map[string]result{"go": parse(input, base)})
	}
}
