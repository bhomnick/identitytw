// Runs in front of the static assets on every request.
//
//  - www.identity.tw is sent to identity.tw.
//  - "/" sends browsers whose first language is Chinese to /zh-hant/, unless
//    a `lang` cookie records an explicit choice. Crawlers send no
//    Accept-Language and stay on English; every language has its own URL and
//    hreflang links, so nothing is hidden from them.
//  - ?lang=en or ?lang=zh-Hant on the language links stores the choice in the
//    cookie and redirects to the clean URL.
//  - Staging and preview hosts (*.workers.dev) are marked noindex so they
//    never compete with the real domain in search results.

const LANGUAGES = { en: '/', 'zh-Hant': '/zh-hant/' };
const COOKIE = 'lang';
const YEAR = 60 * 60 * 24 * 365;

export function prefersChinese(acceptLanguage) {
  const first = (acceptLanguage || '').split(',')[0].trim().toLowerCase();
  return first.startsWith('zh');
}

export function readCookie(header, name) {
  for (const part of (header || '').split(';')) {
    const [key, ...rest] = part.trim().split('=');
    if (key === name) {
      return rest.join('=');
    }
  }
  return null;
}

function redirect(location, extraHeaders) {
  const headers = new Headers({ Location: location, 'Cache-Control': 'no-store' });
  for (const [key, value] of Object.entries(extraHeaders || {})) {
    headers.set(key, value);
  }
  return new Response(null, { status: 302, headers });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.hostname === 'www.identity.tw') {
      url.hostname = 'identity.tw';
      return Response.redirect(url.toString(), 301);
    }

    const chosen = url.searchParams.get('lang');
    if (chosen !== null) {
      url.searchParams.delete('lang');
      const headers = {};
      if (LANGUAGES[chosen] !== undefined) {
        headers['Set-Cookie'] = `${COOKIE}=${chosen}; Path=/; Max-Age=${YEAR}; SameSite=Lax; Secure`;
      }
      return redirect(url.pathname + url.search, headers);
    }

    if (url.pathname === '/') {
      const stored = readCookie(request.headers.get('Cookie'), COOKIE);
      const wantsChinese = stored !== null
        ? stored === 'zh-Hant'
        : prefersChinese(request.headers.get('Accept-Language'));
      if (wantsChinese) {
        return redirect('/zh-hant/' + url.search, { Vary: 'Accept-Language, Cookie' });
      }
    }

    const upstream = await env.ASSETS.fetch(request);
    const staging = url.hostname.endsWith('.workers.dev');
    if (!staging && url.pathname !== '/') {
      return upstream;
    }
    const response = new Response(upstream.body, upstream);
    if (staging) {
      response.headers.set('X-Robots-Tag', 'noindex');
    }
    if (url.pathname === '/') {
      response.headers.append('Vary', 'Accept-Language, Cookie');
    }
    return response;
  },
};
