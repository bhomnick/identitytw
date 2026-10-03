# Validator reference implementations

Each file here is the exact code shown on the homepage, and each one is run
against `fixtures.txt` in CI. Change the algorithm in every language at once
and keep the fixture in sync.

| Language   | File                         | Entry point            |
|------------|------------------------------|------------------------|
| JavaScript | `javascript/taiwan_id.js`    | `isValid(idNumber)`    |
| Python     | `python/taiwan_id.py`        | `is_valid(id_number)`  |
| PHP        | `php/TaiwanId.php`           | `isValid($idNumber)`   |
| Java       | `java/TaiwanId.java`         | `TaiwanId.isValid(..)` |

The JavaScript module is also what the Cloudflare Worker in `../worker`
serves at `https://v.identity.tw`.

## Algorithm

An ID is one letter, one gender or type character, seven digits and a check
digit. The second character is `1` or `2` for citizens, `A` to `D` for legacy
ARC numbers issued before 2021, and `8` or `9` for ARC numbers issued from
2021 onwards.

Letters map to two-digit codes in this order (`A` = 10 through `O` = 35):

    A B C D E F G H J K L M N P Q R S T U V X Y W Z I O

The checksum weights the first letter's tens digit by 1, its units digit by
9, the second character by 8 (a letter counts as the units digit of its
code), the next seven digits by 7 down to 1, and the check digit by 1. The
ID is valid when the total is divisible by 10.

## Running the tests

    ./test.sh                                   # all languages
    VALIDATOR_LANGS="python javascript" ./test.sh

Requires `python3`, `node` (18+), `php` (8+) and a JDK (11+).
