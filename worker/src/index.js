// Taiwan ID validation API.
//
//   GET https://v.identity.tw/?id=A123456789
//   -> 200 {"id": "A123456789", "valid": true}
//   -> 400 {"error": "Must provide ID parameter."}   when id is missing or empty
//
// The ID is echoed back exactly as given and is never logged or stored.

import { isValid } from '../../validator/javascript/taiwan_id.js';

const CORS_HEADERS = {
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'GET,HEAD,OPTIONS',
  'access-control-allow-headers': '*',
  'access-control-max-age': '86400',
};

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      ...CORS_HEADERS,
      'content-type': 'application/json;charset=UTF-8',
      'cache-control': 'no-store',
    },
  });
}

export function handleRequest(request) {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: { ...CORS_HEADERS, allow: 'GET,HEAD,OPTIONS' } });
  }

  const id = new URL(request.url).searchParams.get('id');
  if (!id) {
    return jsonResponse({ error: 'Must provide ID parameter.' }, 400);
  }

  return jsonResponse({ id, valid: isValid(id) });
}

export default {
  fetch(request) {
    return handleRequest(request);
  },
};
