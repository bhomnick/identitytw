"""Tests for web/scripts/import_providers.py."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import build

spec = importlib.util.spec_from_file_location('import_providers', build.WEB_DIR / 'scripts' / 'import_providers.py')
import_providers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(import_providers)

SAMPLE = [
    {'name': 'Example Bank', 'url': 'https://bank.example', 'category': 'Finance',
     'legacy_arc': 'none', 'new_arc': 'separate', 'service': 'partial', 'registration': 'offline',
     'updated': '2024-05-01', 'created': '2021-01-01', 'active': True},
    {'name': '街利存帳戶', 'url': 'https://x.example/', 'category': 'finance',
     'legacy_arc': 'full', 'new_arc': 'full', 'service': 'full', 'registration': 'online',
     'updated': '2023-08-14', 'active': False, 'notes': 'Tested with a real card.',
     'sources': ['https://x.example/help', 'https://x.example/faq']},
]


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.providers_dir = self.tmp / 'providers'
        self.export = self.tmp / 'export.json'
        self.export.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding='utf-8')
        self.original = import_providers.PROVIDERS_DIR
        import_providers.PROVIDERS_DIR = self.providers_dir
        self.categories = build.load_categories()

    def tearDown(self):
        import_providers.PROVIDERS_DIR = self.original
        shutil.rmtree(self.tmp)

    def run_import(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = import_providers.main(['import_providers.py', str(self.export), *extra])
        return code, out.getvalue()

    def test_slugify(self):
        for name, slug in [('Example Bank', 'example-bank'), ('104 iPhone App', '104-iphone-app'),
                           ('Car Tax - 使用牌照稅', 'car-tax-使用牌照稅'), ("Shen′ao Rail  Bike", 'shen-ao-rail-bike'),
                           ('台鐵e訂通 (Apple)', '台鐵e訂通-apple'), ('A_B', 'a-b')]:
            with self.subTest(name=name):
                self.assertEqual(import_providers.slugify(name), slug)

    def test_writes_files_the_generator_accepts(self):
        code, output = self.run_import()
        self.assertEqual(code, 0)
        self.assertIn('wrote 2 provider files', output)
        self.assertEqual(sorted(p.name for p in self.providers_dir.iterdir()), ['example-bank.yaml', '街利存帳戶.yaml'])

        bank = build.parse_provider(self.providers_dir / 'example-bank.yaml', self.categories)
        self.assertEqual((bank.name, bank.url, bank.category), ('Example Bank', 'https://bank.example', 'finance'))
        self.assertEqual((bank.legacy_arc, bank.new_arc, bank.service, bank.registration), ('none', 'separate', 'partial', 'offline'))
        self.assertEqual(bank.updated, dt.date(2024, 5, 1))
        self.assertTrue(bank.active)
        self.assertIsNone(bank.notes)
        self.assertEqual(bank.sources, [])

        other = build.parse_provider(self.providers_dir / '街利存帳戶.yaml', self.categories)
        self.assertFalse(other.active)
        self.assertEqual(other.notes, 'Tested with a real card.')
        self.assertEqual(other.sources, ['https://x.example/help', 'https://x.example/faq'])

    def test_existing_files_are_kept_unless_overwrite(self):
        self.run_import()
        path = self.providers_dir / 'example-bank.yaml'
        path.write_text(path.read_text(encoding='utf-8').replace('service: partial', 'service: none'), encoding='utf-8')
        code, output = self.run_import()
        self.assertEqual(code, 0)
        self.assertIn('skipped 2 existing', output)
        self.assertIn('service: none', path.read_text(encoding='utf-8'))
        self.run_import('--overwrite')
        self.assertIn('service: partial', path.read_text(encoding='utf-8'))

    def test_unknown_category_is_an_error(self):
        self.export.write_text(json.dumps([dict(SAMPLE[0], category='Nope')]), encoding='utf-8')
        with self.assertRaises(SystemExit) as caught:
            self.run_import()
        self.assertIn("unknown category 'Nope'", str(caught.exception))
        self.assertFalse(self.providers_dir.exists() and any(self.providers_dir.iterdir()))

    def test_usage_without_arguments(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(import_providers.main(['import_providers.py']), 2)
        self.assertIn('Usage', out.getvalue())


if __name__ == '__main__':
    unittest.main()
