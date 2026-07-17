"""
ASGI config for ydcleaning project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

<<<<<<< HEAD
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ydcleaning.settings")
=======
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ydcleaning.settings')
>>>>>>> 5815f15 (Initial project commit)

application = get_asgi_application()
