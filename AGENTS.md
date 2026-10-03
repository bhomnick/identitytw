# Working in this repository

Read `README.md` first for what the project is and how to build, test and
deploy it. This file is the operating manual: where things live, what must
change together, and what not to touch.

## Layout

| Path                         | Purpose                                                          |
|------------------------------|------------------------------------------------------------------|
| `web/build.py`               | The whole site generator. Scoring rules (`CRITERIA`, `GRADES`) live here. |
| `web/templates/`             | Jinja2 templates: `base.html`, `index.html`, `provider.html`.   |
| `web/static/`                | `site.css`, `site.js`, `favicon.png`. Nothing else; keep it that way. |
| `web/data/providers/*.yaml`  | The transparency report, one file per service. Filename = URL slug. |
| `web/data/categories.yaml`   | Category keys and their names per language.                      |
| `web/locale/zh_Hant/…/messages.po` | Traditional Chinese catalog. `.mo` files are build output.  |
| `web/test_build.py`          | Generator, data, translation and build-output tests.             |
| `web/scripts/import_providers.py` | Converts an `export_providers` JSON dump into provider files. |
| `validator/<language>/`      | Reference validators. `fixtures.txt` is the shared test set.     |
| `worker/`                    | Cloudflare Worker for `v.identity.tw`. Imports the JS validator. |
| `.github/workflows/ci.yml`   | Tests everything; deploys Pages and the Worker from `master`.    |

`web/dist/` is build output and is ignored by git. Never edit it.

## Commands

    python web/build.py --serve                           # build, serve on :8000, rebuild + reload on change
    python web/build.py                                   # one-off build -> web/dist
    python web/build.py --update-catalog                  # after changing translatable strings
    python -m unittest discover -s web -p 'test_*.py'     # site tests
    ./validator/test.sh                                   # all five validators (php, java, go needed)
    VALIDATOR_LANGS="python javascript" ./validator/test.sh
    (cd worker && npm test && npm run check)              # worker tests + wrangler dry run

Run the site tests and the validator tests before opening a pull request;
CI runs the same commands.

## Invariants

- **The five validators change together.** JavaScript, Python, PHP, Java and
  Go must implement the same algorithm. Add any new case to
  `validator/fixtures.txt` (`valid`/`invalid`, whitespace, ID) and keep
  edge cases that cannot live in the fixture (empty, whitespace, lower-case,
  `\n`) in every harness. The worker imports the JavaScript file, and the
  site embeds all five verbatim, so there is one copy of each.
- **Every translatable string is translated.** After adding or changing
  text in `web/templates/` or `web/build.py`, run
  `python web/build.py --update-catalog` and fill in `messages.po`. The
  test suite fails on missing, obsolete, fuzzy or empty entries. Mark
  translations you drafted without a native speaker with the translator
  comment `NEEDS NATIVE REVIEW`. Python-side strings are wrapped in `N_()`
  and translated at render time with `_()` in templates.
- **Provider files are validated, not trusted.** `parse_provider` rejects
  unknown fields, bad criteria values, unknown categories, non-HTTP URLs and
  non-date `updated` values, naming the file. Add a field there and in the
  README table together. Scores and grades are never stored; the build
  computes them.
- **Scoring changes are data changes.** Editing points in `CRITERIA` or
  thresholds in `GRADES` changes every grade on the next build. Update the
  scoring tests in `web/test_build.py` and say so in the commit message.
- **Static assets stay small.** The page loads one stylesheet, one script and
  the Pygments CSS the build writes. Do not add frameworks, fonts or icon
  sets; inline an SVG if an icon is needed.
- **The API contract is fixed.** `worker/src/index.js` must keep: any method
  and path, `id` query parameter, `400` with `{"error": "Must provide ID
  parameter."}` when missing, pretty-printed JSON, `Access-Control-Allow-Origin: *`,
  `Cache-Control: no-store`, no logging. The tests in `worker/test/` pin this.

## Conventions

- Python 3.13, exact pins in `requirements.txt` (regenerate with `pip freeze`).
  Node 22 and `package-lock.json` for the worker (`npm ci` in CI).
- Provider slugs are lower-case with hyphens; non-ASCII names keep their
  characters (`街利存帳戶.yaml`). Renaming a file changes its URL.
- Dates are `YYYY-MM-DD`. `updated` means "last checked", not "last edited".
- Commit messages explain why. CI needs full git history (`fetch-depth: 0`)
  because service pages render `git log` for their file.
- Deploys happen only from `master` and only when the Cloudflare secrets
  exist; a PR never deploys. Pull requests upload the built site as a CI
  artifact for review.

## Things not to do

- Do not edit `web/dist/`, commit `.mo` or `.pot` files, or add a `.env`.
- Do not reintroduce a database, an admin, or a server-rendered page; the
  point of this layout is that the report is files with history.
- Do not change the default language or URL scheme (`/` English,
  `/zh-hant/` Chinese) without updating `LANGUAGES`, the sitemap test and
  the hreflang assertions together.
