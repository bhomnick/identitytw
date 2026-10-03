"""The validator reference implementations shown on the homepage.

The files live in the top-level ``validator`` directory alongside their
tests, so the code on the page is exactly the code that CI exercises.
"""
from django.conf import settings


SNIPPET_FILES = {
    'javascript': 'javascript/taiwan_id.js',
    'python': 'python/taiwan_id.py',
    'php': 'php/TaiwanId.php',
    'java': 'java/TaiwanId.java',
}


def load_snippets():
    return {
        language: (settings.VALIDATOR_DIR / relative_path).read_text(encoding='utf-8').strip()
        for language, relative_path in SNIPPET_FILES.items()
    }


SNIPPETS = load_snippets()
