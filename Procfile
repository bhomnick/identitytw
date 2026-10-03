# Heroku's router is the only peer that reaches the dyno, so trust its
# X-Forwarded-* headers; waitress 2+ strips them otherwise and Django's HTTPS
# redirect loops.
web: cd identity && waitress-serve --port=$PORT --trusted-proxy='*' --trusted-proxy-headers='x-forwarded-for x-forwarded-proto x-forwarded-port' --log-untrusted-proxy-headers identity.wsgi:application
release: python manage.py migrate
