# identity.tw

Inclusive Taiwan ID number validation, plus a transparency report on which
online services accept resident (ARC) numbers.

Many Taiwanese websites validate ID numbers with a citizens-only check and so
lock out foreign residents, who hold an Alien Resident Certificate (ARC)
number instead. This project provides:

- **Validator libraries** in JavaScript, Python, PHP and Java (`validator/`)
  that accept national IDs, legacy ARC numbers and the ARC format issued
  since 2021. Every implementation is tested against one shared fixture.
- **A hosted validation API** at `https://v.identity.tw` (`worker/`), a
  Cloudflare Worker built from the same JavaScript module.
- **The website** at `https://identity.tw` (`identity/`), a Django site that
  shows the snippets and the transparency report.

## Layout

    identity/     Django project (settings in identity/identity, app in identity/common)
    validator/    Reference implementations, shared test fixture, test runner
    worker/       Cloudflare Worker for the API
    .github/      CI: tests for all three, automatic Worker deploy from master

## Local development

Python 3.13 (see `.python-version`).

    python3.13 -m venv .venv && source .venv/bin/activate   # or: uv venv --python 3.13
    pip install -r requirements.txt
    cp .env.example .env                                     # edit SECRET_KEY
    ./manage.py migrate
    ./manage.py createsuperuser
    ./manage.py runserver

Providers in the transparency report are managed in the admin at `/admin/`.
The database defaults to SQLite; set `DATABASE_URL` in `.env` to use Postgres.

## Tests

    ./manage.py test common                       # site
    ./validator/test.sh                           # all four validator implementations
    VALIDATOR_LANGS="python javascript" ./validator/test.sh
    (cd worker && npm install && npm test)        # API

CI runs all of these on every push and pull request.

## Translations

The site is in English and Traditional Chinese. After changing a translatable
string:

    ./manage.py makemessages -l zh_Hant
    # edit identity/locale/zh_Hant/LC_MESSAGES/django.po
    ./manage.py compilemessages

Compiled `.mo` files are not committed; `bin/post_compile` builds them during
the Heroku build. Both commands need `gettext` installed.

## Deployment

### Website (Heroku)

`Procfile` and `.python-version` drive the build. Config vars:

| Variable                      | Value                                                                 |
|-------------------------------|-----------------------------------------------------------------------|
| `SECRET_KEY`                  | Required.                                                             |
| `DATABASE_URL`                | Set automatically by Heroku Postgres.                                 |
| `USE_SSL`                     | `true`. Enables the HTTPS redirect, HSTS and secure cookies.          |
| `HEROKU_APP`, `HEROKU_DOMAIN` | Redirect `<app>.herokuapp.com` to the canonical domain.               |
| `ALLOWED_HOSTS`               | Optional comma-separated override of the built-in list.               |

Static files are served by WhiteNoise and collected during the build. The
former `USE_S3` and `AWS_*` variables are no longer read.

### API (Cloudflare)

See [`worker/README.md`](worker/README.md). CI deploys the Worker on every
push to `master` once the Cloudflare secrets are configured.

## Contributing

Pull requests are welcome. A change to the validation algorithm must update
all four implementations in `validator/` and pass `./validator/test.sh`. To
report a service that rejects ARC numbers, open an issue with the site, the
ID format you tried and what happened.

Licensed under the MIT license. See `LICENSE`.
