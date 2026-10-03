#!/usr/bin/env python3
"""Build the identity.tw static site.

    python web/build.py              # writes web/dist
    python web/build.py --out DIR

Reads providers from web/data, validator snippets from validator/, and
translations from web/locale. The .po files are compiled here, so pybabel is
only needed when adding or changing translatable strings (see README).
"""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po
from babel.support import NullTranslations, Translations
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

WEB_DIR = Path(__file__).resolve().parent
REPO_DIR = WEB_DIR.parent
DATA_DIR = WEB_DIR / 'data'
TEMPLATES_DIR = WEB_DIR / 'templates'
STATIC_DIR = WEB_DIR / 'static'
PUBLIC_DIR = WEB_DIR / 'public'
LOCALE_DIR = WEB_DIR / 'locale'
VALIDATOR_DIR = REPO_DIR / 'validator'
DEFAULT_OUT = WEB_DIR / 'dist'

SITE_URL = 'https://identity.tw'
API_URL = 'https://v.identity.tw'
REPO_URL = 'https://github.com/bhomnick/identitytw'


@dataclass(frozen=True)
class Language:
    code: str           # BCP 47 tag, used for lang= and hreflang
    prefix: str         # URL prefix; '' for the default language
    locale: str | None  # directory under web/locale; None for the source language
    native_name: str


LANGUAGES = [
    Language('en', '', None, 'English'),
    Language('zh-Hant', 'zh-hant', 'zh_Hant', '正體中文'),
]


def N_(text):
    """Marks a string for extraction; it is translated when a page is rendered."""
    return text


# criterion -> value -> (points, short description, long description)
CRITERIA = {
    'legacy_arc': {
        'full': (0, N_('Full legacy ARC support'),
                 N_('Fully accepts legacy ARC number in place of ROC ID')),
        'separate': (-10, N_('Legacy ARC requires separate UI'),
                     N_('Accepts legacy ARC number in a separate UI (passport number, for instance)')),
        'none': (-25, N_('No legacy ARC support'),
                 N_('Does not accept legacy ARC numbers')),
    },
    'new_arc': {
        'full': (0, N_('Full new ARC support'),
                 N_('Fully accepts new ARC number in place of ROC ID')),
        'separate': (-10, N_('New ARC requires separate UI'),
                     N_('Accepts new ARC number in a separate UI (passport number, for instance)')),
        'none': (-25, N_('No new ARC support'),
                 N_('Does not accept new ARC numbers')),
    },
    'service': {
        'full': (0, N_('Full service for all users'),
                 N_('Provides same service to all users')),
        'partial': (-25, N_('Some services not available to non-citizens'),
                    N_('A portion of features not available to non-citizens')),
        'none': (-50, N_('Denies service to non-citizens'),
                 N_('Denies all services to non-citizens')),
    },
    'registration': {
        'online': (0, N_('All users may register online'),
                   N_('All users may register online using the same process')),
        'offline': (-25, N_('Non-citizens require offline registration'),
                    N_('Non-citizens require additional offline registration steps')),
    },
}

CRITERIA_LABELS = {
    'legacy_arc': N_('Legacy ARC numbers'),
    'new_arc': N_('New ARC numbers'),
    'service': N_('Service'),
    'registration': N_('Registration'),
}

GRADES = [(100, 'A+'), (90, 'A'), (80, 'B'), (70, 'C'), (60, 'D'), (50, 'E')]

# language key -> (file under validator/, tab title, Pygments lexer)
SNIPPET_FILES = {
    'javascript': ('javascript/taiwan_id.js', 'JavaScript', 'javascript'),
    'python': ('python/taiwan_id.py', 'Python', 'python'),
    'php': ('php/TaiwanId.php', 'PHP', 'php'),
    'java': ('java/TaiwanId.java', 'Java', 'java'),
    'go': ('go/taiwanid.go', 'Go', 'go'),
}

EXAMPLE_RESPONSE = '{\n  "id": "A123456789",\n  "valid": true\n}'

REQUIRED_FIELDS = ('name', 'url', 'category', 'legacy_arc', 'new_arc', 'service', 'registration', 'updated')
OPTIONAL_FIELDS = ('notes', 'sources', 'active')


class DataError(Exception):
    """A provider or category file is malformed. The message names the file."""


def grade_for(score):
    for threshold, grade in GRADES:
        if score >= threshold:
            return grade
    return 'F'


@dataclass(frozen=True)
class Criterion:
    key: str
    value: str
    points: int
    short: str
    long: str
    label: str


@dataclass
class Provider:
    slug: str
    name: str
    url: str
    category: str
    legacy_arc: str
    new_arc: str
    service: str
    registration: str
    updated: dt.date
    notes: str | None = None
    sources: list = field(default_factory=list)
    active: bool = True
    path: Path | None = None

    @property
    def criteria(self):
        return [
            Criterion(key, value, *CRITERIA[key][value], CRITERIA_LABELS[key])
            for key, value in (
                ('legacy_arc', self.legacy_arc),
                ('new_arc', self.new_arc),
                ('service', self.service),
                ('registration', self.registration),
            )
        ]

    @property
    def score(self):
        return 100 + sum(c.points for c in self.criteria)

    @property
    def reasons(self):
        return [c for c in self.criteria if c.points != 0]

    @property
    def grade(self):
        return grade_for(self.score)

    @property
    def grade_class(self):
        return self.grade[0].lower()


# --- data ------------------------------------------------------------------

def load_categories(data_dir=DATA_DIR):
    path = data_dir / 'categories.yaml'
    categories = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(categories, dict) or not categories:
        raise DataError(f'{path.name}: expected a mapping of category slug to names')
    for slug, names in categories.items():
        if not re.fullmatch(r'[a-z0-9-]+', str(slug)):
            raise DataError(f'{path.name}: category slug {slug!r} may only use a-z, 0-9 and -')
        missing = [lang.code for lang in LANGUAGES if not isinstance(names, dict) or not names.get(lang.code)]
        if missing:
            raise DataError(f'{path.name}: category {slug!r} has no name for {", ".join(missing)}')
    return categories


def parse_provider(path, categories):
    def fail(message):
        raise DataError(f'{path.name}: {message}')

    try:
        raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        fail(f'invalid YAML: {exc}')
    if not isinstance(raw, dict):
        fail('expected a mapping of fields')
    unknown = sorted(set(raw) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
    if unknown:
        fail(f'unknown fields: {", ".join(unknown)}')
    missing = [name for name in REQUIRED_FIELDS if name not in raw]
    if missing:
        fail(f'missing fields: {", ".join(missing)}')
    if not isinstance(raw['name'], str) or not raw['name'].strip():
        fail('name must be a non-empty string')
    if not isinstance(raw['url'], str) or not re.match(r'https?://', raw['url']):
        fail('url must start with http:// or https://')
    if raw['category'] not in categories:
        fail(f'unknown category {raw["category"]!r}; see categories.yaml')
    for key, values in CRITERIA.items():
        if raw[key] not in values:
            fail(f'{key} must be one of {", ".join(values)}, not {raw[key]!r}')
    updated = raw['updated']
    if isinstance(updated, dt.datetime):
        updated = updated.date()
    if not isinstance(updated, dt.date):
        fail('updated must be a date written as YYYY-MM-DD')
    notes = raw.get('notes')
    if notes is not None and not isinstance(notes, str):
        fail('notes must be a string')
    sources = raw.get('sources') or []
    if not isinstance(sources, list) or not all(isinstance(s, str) for s in sources):
        fail('sources must be a list of URLs')
    active = raw.get('active', True)
    if not isinstance(active, bool):
        fail('active must be true or false')
    return Provider(
        slug=path.stem, name=raw['name'].strip(), url=raw['url'], category=raw['category'],
        legacy_arc=raw['legacy_arc'], new_arc=raw['new_arc'], service=raw['service'],
        registration=raw['registration'], updated=updated, notes=notes.strip() if notes else None,
        sources=sources, active=active, path=path,
    )


def load_providers(categories, data_dir=DATA_DIR):
    paths = sorted((data_dir / 'providers').glob('*.yaml'))
    return [parse_provider(path, categories) for path in paths]


def history(path):
    """(date, commit subject) for each commit touching path, newest first.

    Empty outside a git checkout or in a shallow clone without history.
    """
    try:
        result = subprocess.run(
            ['git', 'log', '--follow', '--format=%as%x09%s', '--', str(path)],
            cwd=REPO_DIR, capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [tuple(line.split('\t', 1)) for line in result.stdout.splitlines() if '\t' in line]


def load_snippets():
    """Raw source of each validator implementation, keyed by language."""
    return {
        language: (VALIDATOR_DIR / relative).read_text(encoding='utf-8').strip()
        for language, (relative, _title, _lexer) in SNIPPET_FILES.items()
    }


def highlight_code(code, lexer_name):
    formatter = HtmlFormatter(cssclass='highlight')
    return Markup(highlight(code, get_lexer_by_name(lexer_name), formatter))


def highlighted_snippets():
    """{language: {'title': ..., 'html': Markup}} for the code tabs."""
    raw = load_snippets()
    return {
        language: {'title': title, 'html': highlight_code(raw[language], lexer)}
        for language, (_relative, title, lexer) in SNIPPET_FILES.items()
    }


def pygments_css():
    light = HtmlFormatter(style='default', nobackground=True).get_style_defs('.highlight')
    dark = HtmlFormatter(style='github-dark', nobackground=True).get_style_defs('.highlight')
    return f'{light}\n@media (prefers-color-scheme: dark) {{\n{dark}\n}}\n'


def report_stats(providers):
    return {
        'total': len(providers),
        'fully_inclusive': sum(1 for p in providers if p.grade == 'A+'),
        'reject_new_arc': sum(1 for p in providers if p.new_arc == 'none'),
        'deny_service': sum(1 for p in providers if p.service == 'none'),
    }


def criteria_overview():
    """The scoring rules, for the methodology section."""
    return [
        {
            'key': key,
            'label': CRITERIA_LABELS[key],
            'options': [
                {'value': value, 'points': points, 'short': short, 'long': long}
                for value, (points, short, long) in options.items()
            ],
        }
        for key, options in CRITERIA.items()
    ]


# --- translations -----------------------------------------------------------

def po_path(language):
    return LOCALE_DIR / language.locale / 'LC_MESSAGES' / 'messages.po'


def compile_translations():
    for language in LANGUAGES:
        if not language.locale:
            continue
        with po_path(language).open('rb') as f:
            catalog = read_po(f, locale=language.locale)
        with po_path(language).with_suffix('.mo').open('wb') as f:
            write_mo(f, catalog)


def translations_for(language):
    if not language.locale:
        return NullTranslations()
    translations = Translations.load(str(LOCALE_DIR), [language.locale])
    if not isinstance(translations, Translations):
        raise RuntimeError(f'no compiled catalog for {language.locale}; run compile_translations()')
    return translations


# --- rendering --------------------------------------------------------------

def page_url(language, path=''):
    """Site-relative URL of a page. path is '' for the index or 'providers/<slug>/'."""
    return '/' + (language.prefix + '/' if language.prefix else '') + path


def make_env():
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(['html', 'xml']),
        extensions=['jinja2.ext.i18n'],
        trim_blocks=True,
        lstrip_blocks=True,
    )


def provider_json(provider):
    return {
        'slug': provider.slug,
        'name': provider.name,
        'url': provider.url,
        'category': provider.category,
        'legacy_arc': provider.legacy_arc,
        'new_arc': provider.new_arc,
        'service': provider.service,
        'registration': provider.registration,
        'score': provider.score,
        'grade': provider.grade,
        'updated': provider.updated.isoformat(),
        'notes': provider.notes,
        'sources': provider.sources,
        'page': SITE_URL + page_url(LANGUAGES[0], f'providers/{provider.slug}/'),
    }


def build(out_dir=DEFAULT_OUT, data_dir=DATA_DIR):
    out_dir = Path(out_dir)
    categories = load_categories(data_dir)
    providers = [p for p in load_providers(categories, data_dir) if p.active]
    providers.sort(key=lambda p: (categories[p.category]['en'].lower(), p.name.lower()))
    snippets = highlighted_snippets()
    stats = report_stats(providers)
    criteria = criteria_overview()
    example_response = highlight_code(EXAMPLE_RESPONSE, 'json')
    compile_translations()
    env = make_env()

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    shutil.copytree(STATIC_DIR, out_dir / 'static')
    (out_dir / 'static' / 'pygments.css').write_text(pygments_css(), encoding='utf-8')
    if PUBLIC_DIR.exists():
        shutil.copytree(PUBLIC_DIR, out_dir, dirs_exist_ok=True)

    histories = {p.slug: history(p.path) for p in providers}
    pages = []

    def write(language, path, html):
        target = out_dir / language.prefix / path / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding='utf-8')
        pages.append(page_url(language, path))

    for language in LANGUAGES:
        env.install_gettext_translations(translations_for(language), newstyle=True)

        def context(path, lang=language):
            return {
                'lang': lang,
                'page_path': path,
                'page_url': page_url(lang, path),
                'alternates': [
                    {'code': other.code, 'native_name': other.native_name, 'url': page_url(other, path)}
                    for other in LANGUAGES
                ],
                'category_name': lambda slug: categories[slug][lang.code],
                'index_url': page_url(lang),
                'site_url': SITE_URL,
                'api_url': API_URL,
                'repo_url': REPO_URL,
                'year': dt.date.today().year,
            }

        write(language, '', env.get_template('index.html').render(
            **context(''), providers=providers, categories=categories, snippets=snippets,
            stats=stats, criteria=criteria, grades=GRADES, example_response=example_response,
        ))
        for provider in providers:
            path = f'providers/{provider.slug}/'
            write(language, path, env.get_template('provider.html').render(
                **context(path), provider=provider, history=histories[provider.slug],
            ))

    (out_dir / 'providers.json').write_text(
        json.dumps([provider_json(p) for p in providers], ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f'  <url><loc>{SITE_URL}{page}</loc></url>' for page in pages]
    sitemap.append('</urlset>')
    (out_dir / 'sitemap.xml').write_text('\n'.join(sitemap) + '\n', encoding='utf-8')
    return out_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT, help='output directory (default: web/dist)')
    args = parser.parse_args(argv)
    try:
        out = build(args.out)
    except DataError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    pages = sum(1 for _ in out.rglob('index.html'))
    print(f'built {pages} pages into {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
