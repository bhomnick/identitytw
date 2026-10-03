#!/usr/bin/env python3
"""Create one YAML file per provider in web/data/providers from a JSON export.

The JSON is a list of objects as written by the Django site's
`export_providers` command:

    [{"name": ..., "url": ..., "category": "Finance",
      "legacy_arc": "full|separate|none", "new_arc": "full|separate|none",
      "service": "full|partial|none", "registration": "online|offline",
      "updated": "YYYY-MM-DD", "active": true}, ...]

Usage:
    python web/scripts/import_providers.py providers.json [--overwrite]

Existing files are left alone unless --overwrite is given.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

WEB_DIR = Path(__file__).resolve().parent.parent
PROVIDERS_DIR = WEB_DIR / 'data' / 'providers'
CATEGORIES_FILE = WEB_DIR / 'data' / 'categories.yaml'


def slugify(name):
    name = unicodedata.normalize('NFKC', name).lower()
    return re.sub(r'[^\w]+|_+', '-', name).strip('-')


def q(value):
    """A double-quoted YAML scalar (JSON strings are valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def render(row, category_slug):
    lines = [
        f'name: {q(row["name"])}',
        f'url: {q(row["url"])}',
        f'category: {category_slug}',
        f'legacy_arc: {row["legacy_arc"]}',
        f'new_arc: {row["new_arc"]}',
        f'service: {row["service"]}',
        f'registration: {row["registration"]}',
        f'updated: {row["updated"]}',
    ]
    if not row.get('active', True):
        lines.append('active: false')
    if row.get('notes'):
        lines.append('notes: ' + q(row['notes']))
    if row.get('sources'):
        lines.append('sources:')
        lines += [f'  - {q(s)}' for s in row['sources']]
    return '\n'.join(lines) + '\n'


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    overwrite = '--overwrite' in argv
    rows = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    categories = yaml.safe_load(CATEGORIES_FILE.read_text(encoding='utf-8'))
    by_english_name = {names['en'].lower(): slug for slug, names in categories.items()}

    PROVIDERS_DIR.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    seen = set()
    for row in rows:
        slug = slugify(row['name'])
        if not slug or slug in seen:
            raise SystemExit(f'cannot make a unique slug for {row["name"]!r}')
        seen.add(slug)
        category_slug = by_english_name.get(row['category'].lower())
        if category_slug is None:
            raise SystemExit(f'unknown category {row["category"]!r}; add it to {CATEGORIES_FILE}')
        path = PROVIDERS_DIR / f'{slug}.yaml'
        if path.exists() and not overwrite:
            skipped += 1
            continue
        path.write_text(render(row, category_slug), encoding='utf-8')
        written += 1
    print(f'wrote {written} provider files, skipped {skipped} existing')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
