import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { isValid } from './taiwan_id.js';

const fixturesPath = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'fixtures.txt');
const cases = readFileSync(fixturesPath, 'utf8')
  .split('\n')
  .map((line) => line.trim())
  .filter((line) => line && !line.startsWith('#'))
  .map((line) => {
    const parts = line.split(/\s+/);
    assert.equal(parts.length, 2, `malformed fixture line: ${line}`);
    return { id: parts[1], expected: parts[0] === 'valid' };
  });

test('shared fixture', () => {
  assert.ok(cases.length > 20, 'fixture file looks empty');
  for (const { id, expected } of cases) {
    assert.equal(isValid(id), expected, `${id} should be ${expected ? 'valid' : 'invalid'}`);
  }
});

test('lower-case input is accepted', () => {
  assert.equal(isValid('a123456789'), true);
  assert.equal(isValid('ab12345677'), true);
  assert.equal(isValid('i123456781'), true, 'lower-case i must upper-case to I in every locale');
});

test('surrounding whitespace is rejected', () => {
  assert.equal(isValid(' A123456789'), false);
  assert.equal(isValid('A123456789 '), false);
  assert.equal(isValid('A123456789\n'), false);
  assert.equal(isValid('A 23456789'), false);
});

test('empty and non-string input is rejected', () => {
  assert.equal(isValid(''), false);
  assert.equal(isValid(null), false);
  assert.equal(isValid(undefined), false);
  assert.equal(isValid(123456789), false);
});
