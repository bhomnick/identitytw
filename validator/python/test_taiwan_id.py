import unittest
from pathlib import Path

from taiwan_id import is_valid

FIXTURES = Path(__file__).resolve().parent.parent / 'fixtures.txt'


def load_cases():
    cases = []
    for line in FIXTURES.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        expected, id_number = line.split()  # raises on malformed lines
        cases.append((id_number, expected == 'valid'))
    return cases


class IsValidTests(unittest.TestCase):
    def test_shared_fixture(self):
        cases = load_cases()
        self.assertGreater(len(cases), 20, 'fixture file looks empty')
        for id_number, expected in cases:
            with self.subTest(id=id_number):
                self.assertEqual(is_valid(id_number), expected)

    def test_lower_case_input_is_accepted(self):
        self.assertTrue(is_valid('a123456789'))
        self.assertTrue(is_valid('ab12345677'))

    def test_surrounding_whitespace_is_rejected(self):
        for value in (' A123456789', 'A123456789 ', 'A123456789\n', 'A 23456789'):
            with self.subTest(value=value):
                self.assertFalse(is_valid(value))

    def test_empty_and_non_string_input_is_rejected(self):
        self.assertFalse(is_valid(''))
        self.assertFalse(is_valid(None))
        self.assertFalse(is_valid(123456789))


if __name__ == '__main__':
    unittest.main()
