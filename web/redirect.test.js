import { test } from 'node:test';
import assert from 'node:assert/strict';

import worker, { prefersChinese, readCookie } from './redirect.js';

const env = { ASSETS: { fetch: async (request) => new Response('page ' + new URL(request.url).pathname, { headers: { 'content-type': 'text/html' } }) } };
const call = (url, headers) => worker.fetch(new Request(url, { headers }), env);

test('www goes to the bare domain, path kept', async () => {
  const r = await call('https://www.identity.tw/providers/x/?a=1');
  assert.equal(r.status, 301);
  assert.equal(r.headers.get('location'), 'https://identity.tw/providers/x/?a=1');
});

test('Chinese browsers are sent from / to /zh-hant/', async () => {
  const r = await call('https://identity.tw/', { 'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8' });
  assert.equal(r.status, 302);
  assert.equal(r.headers.get('location'), '/zh-hant/');
  assert.match(r.headers.get('vary'), /Accept-Language/);
});

test('other browsers and crawlers stay on English', async () => {
  for (const lang of ['en-US,en;q=0.9,zh-TW;q=0.8', 'ja', '', undefined]) {
    const r = await call('https://identity.tw/', lang === undefined ? {} : { 'Accept-Language': lang });
    assert.equal(r.status, 200, String(lang));
    assert.equal(await r.text(), 'page /');
    assert.match(r.headers.get('vary'), /Accept-Language/);
  }
});

test('only the root negotiates', async () => {
  const r = await call('https://identity.tw/providers/x/', { 'Accept-Language': 'zh-TW' });
  assert.equal(r.status, 200);
});

test('an explicit choice in the cookie wins over Accept-Language', async () => {
  const english = await call('https://identity.tw/', { 'Accept-Language': 'zh-TW', Cookie: 'other=1; lang=en' });
  assert.equal(english.status, 200);
  const chinese = await call('https://identity.tw/', { 'Accept-Language': 'en-US', Cookie: 'lang=zh-Hant' });
  assert.equal(chinese.status, 302);
});

test('?lang= stores the choice and redirects to the clean URL', async () => {
  const r = await call('https://identity.tw/zh-hant/?lang=zh-Hant');
  assert.equal(r.status, 302);
  assert.equal(r.headers.get('location'), '/zh-hant/');
  assert.match(r.headers.get('set-cookie'), /^lang=zh-Hant; Path=\/; Max-Age=31536000; SameSite=Lax; Secure$/);
  const bad = await call('https://identity.tw/?lang=klingon');
  assert.equal(bad.status, 302);
  assert.equal(bad.headers.get('set-cookie'), null);
});

test('staging hosts are noindex, production is not', async () => {
  const staging = await call('https://identitytw.bhomnick.workers.dev/providers/x/');
  assert.equal(staging.headers.get('x-robots-tag'), 'noindex');
  const prod = await call('https://identity.tw/providers/x/');
  assert.equal(prod.headers.get('x-robots-tag'), null);
});

test('helpers', () => {
  assert.equal(prefersChinese('zh-Hant-TW,zh;q=0.8'), true);
  assert.equal(prefersChinese('en,zh;q=0.9'), false);
  assert.equal(readCookie('a=1; lang=zh-Hant; b=2', 'lang'), 'zh-Hant');
  assert.equal(readCookie('', 'lang'), null);
});
