"""
WSGI config for web project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

if os.environ.get("CUCKOO_APP", "").lower() == "web":
    from cuckoo.web.web.startup import init_and_get_wsgi
    application = init_and_get_wsgi()

else:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    # Apply WSGI middleware here.