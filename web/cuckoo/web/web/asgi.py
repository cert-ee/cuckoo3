"""
ASGI config for web project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

if os.environ.get("CUCKOO_APP", "").lower() == "web":
    from cuckoo.web.web.startup import init_and_get_asgi

    application = init_and_get_asgi()

else:
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
    application = get_asgi_application()
