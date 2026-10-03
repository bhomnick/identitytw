# Validation API worker

The Cloudflare Worker behind `https://v.identity.tw`. It imports the
JavaScript validator from `../validator/javascript/taiwan_id.js`, so the API,
the homepage snippet and the test fixture can never disagree.

## API

    GET https://v.identity.tw/?id=A123456789

    200 {"id": "A123456789", "valid": true}
    400 {"error": "Must provide ID parameter."}

Any method and path work; only the `id` query parameter matters. The ID is
echoed back exactly as given, nothing is logged or stored, and every response
carries `Access-Control-Allow-Origin: *` and `Cache-Control: no-store`.

## Develop

    npm install
    npm test            # unit tests, no Cloudflare account needed
    npm run check       # bundles with wrangler --dry-run to validate config
    npx wrangler dev    # local server at http://localhost:8787

## Deploy

CI deploys automatically on every push to `master` once these repository
secrets exist (Settings > Secrets and variables > Actions):

| Secret                  | Value                                                              |
|-------------------------|--------------------------------------------------------------------|
| `CLOUDFLARE_API_TOKEN`  | API token with the "Edit Cloudflare Workers" template permissions  |
| `CLOUDFLARE_ACCOUNT_ID` | Account ID from the Workers & Pages overview page                  |

Until the secrets are set the deploy step prints a notice and skips.

Before the first automated deploy, check `name` in `wrangler.toml` against
the Worker that currently serves `v.identity.tw` in the dashboard. If the
names differ, either rename here or delete the old Worker after the new one
is live, otherwise two Workers will fight over the custom domain.

Manual deploy from a machine with `wrangler login` done:

    npm run deploy
