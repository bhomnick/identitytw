// Runs in front of the static assets: sends www.identity.tw to identity.tw,
// everything else is served from ./dist by the ASSETS binding.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === 'www.identity.tw') {
      url.hostname = 'identity.tw';
      return Response.redirect(url.toString(), 301);
    }
    return env.ASSETS.fetch(request);
  },
};
