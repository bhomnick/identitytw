// Package taiwanid validates Taiwan ID numbers.
//
// Accepts ROC national ID numbers, legacy ARC/APRC numbers (two leading
// letters, issued before 2021) and new-format ARC/APRC numbers (letter + 8/9,
// issued from 2021).
//
// Format: 1 letter, then 1/2 (citizen), A-D (legacy ARC) or 8/9 (new ARC),
// then 7 digits and a check digit.
package taiwanid

import (
	"regexp"
	"strings"
)

var idPattern = regexp.MustCompile(`^[A-Z][12A-D89][0-9]{8}$`)

const letterCodes = "ABCDEFGHJKLMNPQRSTUVXYWZIO" // index + 10 = the letter's numeric code

// IsValid reports whether id is a well-formed Taiwan ID number with a
// correct check digit. Lower-case input is accepted.
func IsValid(id string) bool {
	normalized := strings.ToUpper(id)
	if !idPattern.MatchString(normalized) {
		return false
	}

	letterCode := strings.IndexByte(letterCodes, normalized[0]) + 10
	sum := letterCode/10 + (letterCode%10)*9

	// A letter in the second position (legacy ARC) counts as the last digit of its code.
	second := normalized[1]
	var secondValue int
	if second >= 'A' && second <= 'Z' {
		secondValue = (strings.IndexByte(letterCodes, second) + 10) % 10
	} else {
		secondValue = int(second - '0')
	}
	sum += secondValue * 8

	for i := 2; i < 9; i++ {
		sum += (9 - i) * int(normalized[i]-'0')
	}
	sum += int(normalized[9] - '0')

	return sum%10 == 0
}
