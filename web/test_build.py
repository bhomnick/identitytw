"""Tests for the site generator. Run from the repo root:

    python -m unittest discover -s web -p 'test_*.py'
"""
import datetime as dt
import html
import http.server
import json
import re
import shutil
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from babel.messages.extract import DEFAULT_KEYWORDS, extract_from_dir
from babel.messages.pofile import read_po

import build

FULL = dict(legacy_arc='full', new_arc='full', service='full', registration='online')


def make_provider(**overrides):
    fields = dict(slug='example', name='Example', url='https://example.com', category='finance',
                  updated=dt.date(2024, 1, 1), **FULL)
    fields.update(overrides)
    return build.Provider(**fields)


class ScoringTests(unittest.TestCase):
    def test_full_support_is_100(self):
        provider = make_provider()
        self.assertEqual(provider.score, 100)
        self.assertEqual(provider.grade, 'A+')
        self.assertEqual(provider.reasons, [])

    def test_penalties_are_summed(self):
        provider = make_provider(legacy_arc='separate', service='partial')
        self.assertEqual(provider.score, 65)
        self.assertEqual(provider.grade, 'D')
        self.assertEqual([c.short for c in provider.reasons],
                         ['Legacy ARC requires separate UI', 'Some services not available to non-citizens'])

    def test_worst_case_is_an_f(self):
        provider = make_provider(legacy_arc='none', new_arc='none', service='none', registration='offline')
        self.assertEqual(provider.score, -25)
        self.assertEqual(provider.grade, 'F')
        self.assertEqual(len(provider.reasons), 4)

    def test_grade_boundaries(self):
        for score, grade in [(100, 'A+'), (90, 'A'), (80, 'B'), (70, 'C'), (60, 'D'), (50, 'E'), (49, 'F'), (-25, 'F')]:
            with self.subTest(score=score):
                self.assertEqual(build.grade_for(score), grade)


class DataTests(unittest.TestCase):
    def test_checked_in_data_is_valid(self):
        categories = build.load_categories()
        providers = build.load_providers(categories)
        self.assertGreater(len(providers), 50)
        self.assertEqual(len({p.slug for p in providers}), len(providers))
        for provider in providers:
            self.assertIn(provider.category, categories)

    def test_invalid_files_are_rejected_with_the_file_name(self):
        cases = {
            'missing': 'name: X\nurl: https://x.example\ncategory: finance\nlegacy_arc: full\nnew_arc: full\nservice: full\n',
            'bad-value': 'name: X\nurl: https://x.example\ncategory: finance\nlegacy_arc: yes\nnew_arc: full\nservice: full\nregistration: online\nupdated: 2024-01-01\n',
            'bad-category': 'name: X\nurl: https://x.example\ncategory: nope\nlegacy_arc: full\nnew_arc: full\nservice: full\nregistration: online\nupdated: 2024-01-01\n',
            'bad-url': 'name: X\nurl: x.example\ncategory: finance\nlegacy_arc: full\nnew_arc: full\nservice: full\nregistration: online\nupdated: 2024-01-01\n',
            'unknown-field': 'name: X\nurl: https://x.example\ncategory: finance\nlegacy_arc: full\nnew_arc: full\nservice: full\nregistration: online\nupdated: 2024-01-01\nscore: 5\n',
            'bad-date': 'name: X\nurl: https://x.example\ncategory: finance\nlegacy_arc: full\nnew_arc: full\nservice: full\nregistration: online\nupdated: soon\n',
        }
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            shutil.copy(build.DATA_DIR / 'categories.yaml', data_dir)
            (data_dir / 'providers').mkdir()
            categories = build.load_categories(data_dir)
            for name, content in cases.items():
                path = data_dir / 'providers' / f'{name}.yaml'
                path.write_text(content, encoding='utf-8')
                with self.subTest(case=name):
                    with self.assertRaises(build.DataError) as caught:
                        build.parse_provider(path, categories)
                    self.assertIn(f'{name}.yaml', str(caught.exception))

    def test_optional_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'opt.yaml'
            path.write_text(
                'name: X\nurl: https://x.example\ncategory: finance\nlegacy_arc: full\nnew_arc: full\n'
                'service: full\nregistration: online\nupdated: 2024-01-01\nactive: false\n'
                'notes: |\n  First.\n\n  Second.\nsources:\n  - https://x.example/help\n', encoding='utf-8')
            provider = build.parse_provider(path, build.load_categories())
        self.assertFalse(provider.active)
        self.assertEqual(provider.notes, 'First.\n\nSecond.')
        self.assertEqual(provider.sources, ['https://x.example/help'])


class TranslationTests(unittest.TestCase):
    """The catalog must match the templates and be fully translated, or CI fails."""

    @staticmethod
    def source_messages():
        keywords = dict(DEFAULT_KEYWORDS, N_=None)
        method_map = [('build.py', 'python'), ('templates/**.html', 'jinja2')]
        options_map = {'templates/**.html': {'extensions': 'jinja2.ext.i18n'}}
        return {message for _, _, message, _, _ in
                extract_from_dir(str(build.WEB_DIR), method_map, options_map, keywords=keywords)}

    def test_catalogs_are_in_sync_and_complete(self):
        sources = self.source_messages()
        self.assertGreater(len(sources), 20)
        for language in build.LANGUAGES:
            if not language.locale:
                continue
            with self.subTest(locale=language.locale):
                with build.po_path(language).open('rb') as f:
                    catalog = read_po(f, locale=language.locale)
                catalog_ids = {m.id for m in catalog if m.id}
                self.assertEqual(sources - catalog_ids, set(), 'strings missing from the catalog; run: python web/build.py --update-catalog')
                self.assertEqual(catalog_ids - sources, set(), 'obsolete strings in the catalog; run: python web/build.py --update-catalog')
                untranslated = sorted(m.id for m in catalog if m.id and (not m.string or m.fuzzy))
                self.assertEqual(untranslated, [], 'untranslated or fuzzy strings')


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.out = build.build(Path(cls.tmp) / 'dist')
        cls.providers = [p for p in build.load_providers(build.load_categories()) if p.active]
        cls.en = (cls.out / 'index.html').read_text(encoding='utf-8')
        cls.zh = (cls.out / 'zh-hant' / 'index.html').read_text(encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_index_pages(self):
        self.assertIn('<html lang="en">', self.en)
        self.assertIn('<html lang="zh-Hant">', self.zh)
        self.assertIn('hreflang="zh-Hant" href="https://identity.tw/zh-hant/"', self.en)
        self.assertIn('rel="canonical" href="https://identity.tw/zh-hant/"', self.zh)
        self.assertNotEqual(self.en, self.zh)
        self.assertRegex(self.zh, '[一-鿿]')

    def test_every_provider_has_a_page_in_every_language(self):
        for provider in self.providers:
            for prefix in ('', 'zh-hant'):
                page = self.out / prefix / 'providers' / provider.slug / 'index.html'
                with self.subTest(provider=provider.slug, prefix=prefix):
                    self.assertTrue(page.exists())
                    self.assertIn(provider.name, page.read_text(encoding='utf-8'))
                    self.assertIn(provider.name, self.en if not prefix else self.zh)

    def test_providers_json(self):
        data = json.loads((self.out / 'providers.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data), len(self.providers))
        self.assertEqual({'slug', 'name', 'url', 'category', 'legacy_arc', 'new_arc', 'service', 'registration',
                          'score', 'grade', 'updated', 'notes', 'sources', 'page'}, set(data[0]))

    def test_snippets_are_embedded_verbatim(self):
        snippets = build.load_snippets()
        self.assertEqual(set(snippets), set(build.SNIPPET_FILES))
        for language, snippet in snippets.items():
            with self.subTest(language=language):
                panel = re.search(r'<div role="tabpanel" id="panel-%s".*?</div>\s*</div>' % language, self.en, re.S).group(0)
                text = html.unescape(re.sub(r'<[^>]+>', '', panel)).strip()
                self.assertEqual(text, snippet, 'highlighted code must read back as the source file')

    def test_classic_layout_builds_with_the_same_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build.build(Path(tmp) / 'dist', layout='classic')
            html = (out / 'index.html').read_text(encoding='utf-8')
        self.assertIn('class="icon-boxes"', html)
        self.assertIn('class="report-table"', html)
        for provider in self.providers:
            self.assertIn(provider.name, html)

    def test_hero_statistics_match_the_data(self):
        stats = build.report_stats(self.providers)
        self.assertEqual(stats['total'], len(self.providers))
        self.assertIn(f'<strong>{stats["total"]}</strong>', self.en)
        self.assertIn(f'<strong>{stats["reject_new_arc"]}</strong>', self.en)

    def test_static_headers_and_sitemap(self):
        for name in ('site.css', 'site.js', 'pygments.css', 'favicon.png'):
            self.assertTrue((self.out / 'static' / name).exists(), name)
        self.assertIn('.highlight .k ', (self.out / 'static' / 'pygments.css').read_text())
        self.assertIn('X-Frame-Options', (self.out / '_headers').read_text())
        sitemap = (self.out / 'sitemap.xml').read_text()
        self.assertIn('<loc>https://identity.tw/</loc>', sitemap)
        self.assertIn('<loc>https://identity.tw/zh-hant/</loc>', sitemap)
        self.assertEqual(sitemap.count('<loc>'), 2 * (1 + len(self.providers)))


class DevServerTests(unittest.TestCase):
    def test_injects_reload_script_and_reports_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'providers' / 'x').mkdir(parents=True)
            (out / 'index.html').write_text('<html><body>home</body></html>', encoding='utf-8')
            (out / 'providers' / 'x' / 'index.html').write_text('<html><body>x</body></html>', encoding='utf-8')
            (out / 'data.json').write_text('{}', encoding='utf-8')
            state = build.DevState()
            state.version = 3
            state.error = 'boom'
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), build.make_handler(out, state))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f'http://127.0.0.1:{server.server_address[1]}'
            try:
                home = urllib.request.urlopen(base + '/').read().decode('utf-8')
                self.assertIn("fetch('/__version'", home)
                self.assertTrue(home.endswith('</body></html>'), 'script goes before </body>')
                self.assertIn("fetch('/__version'", urllib.request.urlopen(base + '/providers/x/').read().decode('utf-8'))
                self.assertEqual(json.loads(urllib.request.urlopen(base + '/__version').read()), {'version': 3, 'error': 'boom'})
                self.assertEqual(urllib.request.urlopen(base + '/data.json').read(), b'{}')
            finally:
                server.shutdown()

    def test_snapshot_ignores_build_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'dist').mkdir()
            (root / 'dist' / 'index.html').write_text('x')
            (root / 'locale').mkdir()
            (root / 'locale' / 'messages.mo').write_bytes(b'x')
            (root / 'data.yaml').write_text('x')
            self.assertEqual({p.name for p in build.snapshot([root])}, {'data.yaml'})


if __name__ == '__main__':
    unittest.main()
