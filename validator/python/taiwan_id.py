"""Taiwan ID number validator.

Accepts ROC national ID numbers, legacy ARC/APRC numbers (two leading
letters, issued before 2021) and new-format ARC/APRC numbers (letter + 8/9,
issued from 2021).

Format: 1 letter, then 1/2 (citizen), A-D (legacy ARC) or 8/9 (new ARC),
then 7 digits and a check digit.
"""
import re

ID_PATTERN = re.compile(r'[A-Z][12A-D89][0-9]{8}')
LETTER_CODES = 'ABCDEFGHJKLMNPQRSTUVXYWZIO'  # index + 10 = the letter's numeric code


def is_valid(id_number):
    normalized = str(id_number).upper()
    if not ID_PATTERN.fullmatch(normalized):
        return False

    letter_code = LETTER_CODES.index(normalized[0]) + 10
    total = letter_code // 10 + (letter_code % 10) * 9

    # A letter in the second position (legacy ARC) counts as the last digit of its code.
    second = normalized[1]
    if second.isalpha():
        second_value = (LETTER_CODES.index(second) + 10) % 10
    else:
        second_value = int(second)
    total += second_value * 8

    for position in range(2, 9):
        total += (9 - position) * int(normalized[position])
    total += int(normalized[9])

    return total % 10 == 0
