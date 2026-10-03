# identity.tw

Which online services in Taiwan accept resident (ARC) numbers? A public
scorecard of how services treat foreign residents, plus validation code in
five languages that accepts every legal Taiwan ID number format.

Foreign residents hold an Alien Resident Certificate (ARC) number instead of
a national ID. Many websites validate ID numbers with a citizens-only check
and lock them out. This repository holds everything behind the site:

| Directory    | What it is                                                                 |
|--------------|----------------------------------------------------------------------------|
| `web/`       | The static site: generator, templates, translations, report data, `wrangler.toml`. |
| `validator/` | Reference validators in JavaScript, Python, PHP, Java and Go, with tests.  |
| `worker/`    | The Cloudflare Worker behind the API at `https://v.identity.tw`.           |
| `.github/`   | CI for all three, and deployment to Cloudflare on every push to `master`.  |

## Adding or updating a service in the report

The report is the files in `web/data/providers/`, one per service. To add
one, copy an existing file and name it after the service in lower-case with
hyphens (`cathay-united-bank.yaml`). The fields:

| Field          | Values                                                                      |
|----------------|-----------------------------------------------------------------------------|
| `name`         | Display name.                                                               |
| `url`          | Where the sign-up or ID check happens.                                      |
| `category`     | A key from `web/data/categories.yaml`.                                      |
| `legacy_arc`   | `full`, `separate` or `none`: how legacy ARC numbers (two letters) are handled. |
| `new_arc`      | `full`, `separate` or `none`: how post-2021 ARC numbers (letter + 8/9) are handled. |
| `service`      | `full`, `partial` or `none`: whether non-citizens get the same service.     |
| `registration` | `online` or `offline`: whether non-citizens can register online.            |
| `updated`      | Date of the last check, `YYYY-MM-DD`.                                       |
| `notes`        | Optional. What was tested and what happened.                                |
| `sources`      | Optional list of URLs backing the assessment.                               |
| `active`       | Optional, `false` hides the service from the report.                        |

Scores are computed at build time (see "How the grades work" on the site),
so there is nothing to calculate by hand. Open a pull request; CI validates
the file and builds the site, and the service's page shows every change from
git history. To report a service without editing files, open an issue.

## Local development

Python 3.13 (see `.python-version`).

    python3.13 -m venv .venv && source .venv/bin/activate   # or: uv venv --python 3.13
    pip install -r requirements.txt
    python web/build.py --serve

That builds the site, serves it at http://127.0.0.1:8000/, rebuilds whenever
anything under `web/` or `validator/` changes, and reloads open pages. A
failing build shows its error at the bottom of the page and keeps serving
the last good build. `python web/build.py` alone writes `web/dist` once.

Tests:

    python -m unittest discover -s web -p 'test_*.py'    # generator, data, translations
    ./validator/test.sh                                  # all five validator implementations
    (cd worker && npm install && npm test)               # API worker

## Translations

The site is in English and Traditional Chinese. After adding or changing a
string in `web/templates/` or `web/build.py`:

    python web/build.py --update-catalog
    # fill in the empty msgstr entries in web/locale/zh_Hant/LC_MESSAGES/messages.po

The build compiles `.po` files itself. CI fails when the catalog is out of
date or a string is untranslated. Entries marked `NEEDS NATIVE REVIEW` in the
catalog were drafted without a native speaker; corrections are welcome.

## Validators and the API

Each file in `validator/<language>/` is exactly the code shown on the site,
and every implementation runs against `validator/fixtures.txt` in CI. See
`validator/README.md` for the algorithm. The JavaScript module is also what
the Worker serves; `validator/javascript/package.json` is ready for
`npm publish` as `validate-taiwan-id` but has not been published.

The API (`worker/README.md`) is a demo for trying the algorithm. Production
systems should use the code so ID numbers never leave them.

## CI and deployment

Every push and pull request runs the generator tests, builds the site and
smoke-tests the build, runs all five validator implementations, and runs the
Worker tests plus a wrangler dry run. A missing toolchain fails the job; nothing
is skipped silently.

The site is hosted as a Cloudflare Worker that serves static assets (the
current form of Cloudflare Pages), configured in `web/wrangler.toml`;
`web/redirect.js` runs in front of the assets to send www to the bare domain.
Pull requests from this repository get a preview version with its own URL,
smoke-tested and linked in a comment on the PR.

Pushes to `master` deploy the API Worker and the site with `wrangler deploy`,
using the exact build artifact the tests ran against, then fetch the live
pages and API to verify the deploy. Until the custom domains are attached the
site lives at https://identitytw.bhomnick.workers.dev. A weekly scheduled run
repeats the tests and the live checks. Dependabot opens weekly grouped
update PRs for pip, npm, Go and the GitHub Actions.

All of this needs these repository secrets:

| Secret                  | Value                                                                      |
|-------------------------|----------------------------------------------------------------------------|
| `CLOUDFLARE_API_TOKEN`  | API token: Account / Workers Scripts / Edit, Zone / Workers Routes / Edit, Zone / DNS / Edit (for the custom domains), Zone / Zone / Read, scoped to this account and the identity.tw zone. |
| `CLOUDFLARE_ACCOUNT_ID` | Account ID from the Workers & Pages overview (already set).                |

Until the secrets are set, the deploy and preview jobs print a warning and
skip. After the custom domain is live, set the repository variable
`SITE_URL` to `https://identity.tw` so the post-deploy check and the weekly
health check test the real domain instead of `identitytw.pages.dev`.

### Moving off Heroku

The site used to be a Django app on Heroku with the report in Postgres. To
cut over:

1. Export the live data with the Django app's `export_providers` command (on
   the `modernize` branch / PR #23) and replace the scraped files:
   `heroku run -a <app> python manage.py export_providers > providers.json`,
   then `python web/scripts/import_providers.py providers.json --overwrite`.
2. Add the secrets above and merge the static-site PR. CI deploys the site to
   https://identitytw.bhomnick.workers.dev and checks it.
3. Uncomment the two `[[routes]]` blocks in `web/wrangler.toml` and merge
   that change. wrangler attaches `identity.tw` and `www.identity.tw` as
   custom domains and replaces the DNS records that point at Heroku. Then set
   the repository variable `SITE_URL` to `https://identity.tw`; the
   post-deploy check then also verifies the www redirect.
4. Delete the Heroku app and its database.

Licensed under the MIT license. See `LICENSE`.
