<?php
// Taiwan ID number validator.
//
// Accepts ROC national ID numbers, legacy ARC/APRC numbers (two leading
// letters, issued before 2021) and new-format ARC/APRC numbers (letter + 8/9,
// issued from 2021).
//
// Format: 1 letter, then 1/2 (citizen), A-D (legacy ARC) or 8/9 (new ARC),
// then 7 digits and a check digit.

const TAIWAN_ID_PATTERN = '/^[A-Z][12A-D89][0-9]{8}\z/';
const TAIWAN_ID_LETTER_CODES = 'ABCDEFGHJKLMNPQRSTUVXYWZIO'; // index + 10 = the letter's numeric code

function isValid(string $idNumber): bool
{
    $normalized = strtoupper($idNumber);
    if (preg_match(TAIWAN_ID_PATTERN, $normalized) !== 1) {
        return false;
    }

    $letterCode = strpos(TAIWAN_ID_LETTER_CODES, $normalized[0]) + 10;
    $sum = intdiv($letterCode, 10) + ($letterCode % 10) * 9;

    // A letter in the second position (legacy ARC) counts as the last digit of its code.
    $second = $normalized[1];
    $secondValue = ctype_alpha($second)
        ? (strpos(TAIWAN_ID_LETTER_CODES, $second) + 10) % 10
        : (int) $second;
    $sum += $secondValue * 8;

    for ($i = 2; $i < 9; $i++) {
        $sum += (9 - $i) * (int) $normalized[$i];
    }
    $sum += (int) $normalized[9];

    return $sum % 10 === 0;
}
