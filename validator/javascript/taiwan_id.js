// Taiwan ID number validator.
//
// Accepts ROC national ID numbers, legacy ARC/APRC numbers (two leading
// letters, issued before 2021) and new-format ARC/APRC numbers (letter + 8/9,
// issued from 2021).
//
// Format: 1 letter, then 1/2 (citizen), A-D (legacy ARC) or 8/9 (new ARC),
// then 7 digits and a check digit.

const ID_PATTERN = /^[A-Z][12A-D89][0-9]{8}$/;
const LETTER_CODES = 'ABCDEFGHJKLMNPQRSTUVXYWZIO'; // index + 10 = the letter's numeric code

export function isValid(idNumber) {
  const normalized = String(idNumber).toUpperCase();
  if (!ID_PATTERN.test(normalized)) {
    return false;
  }

  const letterCode = LETTER_CODES.indexOf(normalized[0]) + 10;
  let sum = Math.floor(letterCode / 10) + (letterCode % 10) * 9;

  // A letter in the second position (legacy ARC) counts as the last digit of its code.
  const second = normalized[1];
  const secondValue = /[A-Z]/.test(second)
    ? (LETTER_CODES.indexOf(second) + 10) % 10
    : Number(second);
  sum += secondValue * 8;

  for (let i = 2; i < 9; i++) {
    sum += (9 - i) * Number(normalized[i]);
  }
  sum += Number(normalized[9]);

  return sum % 10 === 0;
}
