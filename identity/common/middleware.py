from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class HerokuRedirectMiddleware:
    """
    Redirects .herokuapp.com domains to a canonical domain. To use set
    HEROKU_APP to your heroku app name and HEROKU_DOMAIN to your canonical
    domain name.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.HEROKU_APP and settings.HEROKU_DOMAIN:
            host = request.get_host().partition(':')[0]
            if host == f'{settings.HEROKU_APP}.herokuapp.com':
                protocol = 'https' if settings.USE_SSL else 'http'
                redirect = f'{protocol}://{settings.HEROKU_DOMAIN}{request.path}'
                return HttpResponsePermanentRedirect(redirect)

        return self.get_response(request)
