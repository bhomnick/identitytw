package taiwanid

import (
	"bufio"
	"os"
	"strings"
	"testing"
)

func TestSharedFixture(t *testing.T) {
	f, err := os.Open("../fixtures.txt")
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()

	count := 0
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.Fields(line)
		if len(parts) != 2 {
			t.Fatalf("malformed fixture line: %q", line)
		}
		want := parts[0] == "valid"
		count++
		if got := IsValid(parts[1]); got != want {
			t.Errorf("IsValid(%q) = %v, want %v", parts[1], got, want)
		}
	}
	if err := scanner.Err(); err != nil {
		t.Fatal(err)
	}
	if count < 20 {
		t.Fatalf("only %d cases ran; is fixtures.txt missing?", count)
	}
}

func TestEdgeCases(t *testing.T) {
	cases := map[string]bool{
		"a123456789":   true,  // lower-case input is accepted
		"ab12345677":   true,
		"i123456781":   true,
		" A123456789":  false, // surrounding whitespace is rejected
		"A123456789 ":  false,
		"A123456789\n": false,
		"A 23456789":   false,
		"":             false,
	}
	for input, want := range cases {
		if got := IsValid(input); got != want {
			t.Errorf("IsValid(%q) = %v, want %v", input, got, want)
		}
	}
}
