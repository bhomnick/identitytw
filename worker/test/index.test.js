import { test } from 'node:test';
import assert from 'node:assert/strict';

import worker, { handleRequest } from '../src/index.js';

const BASE = 'https://v.identity.tw';

async function call(path, init) {
  const response = handleRequest(new Request(BASE + path, init));
  const text = await response.text();
  return { response, text, body: text ? JSON.parse(text) : null };
}

test('valid ID', async () => {
  const { response, body } = await call('/?id=A123456789');
  assert.equal(response.status, 200);
  assert.deepEqual(body, { id: 'A123456789', valid: true });
});

test('invalid ID', async () => {
  const { response, body } = await call('/?id=A123456788');
  assert.equal(response.status, 200);
  assert.deepEqual(body, { id: 'A123456788', valid: false });
});

test('legacy and new ARC numbers', async () => {
  assert.equal((await call('/?id=AB12345677')).body.valid, true);
  assert.equal((await call('/?id=A800000014')).body.valid, true);
});

test('ID is echoed back exactly as given', async () => {
  assert.deepEqual((await call('/?id=a123456789')).body, { id: 'a123456789', valid: true });
  assert.deepEqual((await call('/?id=%20A123456789%20')).body, { id: ' A123456789 ', valid: false });
});

test('missing or empty id is a 400', async () => {
  for (const path of ['/', '/?id=', '/?foo=bar']) {
    const { response, body } = await call(path);
    assert.equal(response.status, 400, path);
    assert.deepEqual(body, { error: 'Must provide ID parameter.' });
  }
});

test('any path and method are accepted', async () => {
  assert.equal((await call('/anything/here?id=A123456789')).response.status, 200);
  assert.equal((await call('/?id=A123456789', { method: 'POST' })).response.status, 200);
});

test('response headers', async () => {
  const { response, text } = await call('/?id=A123456789');
  assert.equal(response.headers.get('content-type'), 'application/json;charset=UTF-8');
  assert.equal(response.headers.get('access-control-allow-origin'), '*');
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(text, '{\n  "id": "A123456789",\n  "valid": true\n}', 'body is pretty-printed like the original API');
});

test('CORS preflight', async () => {
  const { response, text } = await call('/?id=A123456789', {
    method: 'OPTIONS',
    headers: { origin: 'https://identity.tw', 'access-control-request-method': 'GET' },
  });
  assert.equal(response.status, 204);
  assert.equal(text, '');
  assert.equal(response.headers.get('access-control-allow-origin'), '*');
  assert.match(response.headers.get('access-control-allow-methods'), /GET/);
});

test('default export is what Cloudflare calls', async () => {
  const response = await worker.fetch(new Request(BASE + '/?id=A123456789'));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { id: 'A123456789', valid: true });
});
