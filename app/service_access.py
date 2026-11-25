"""Lazy service routing so legacy mode remains available for local development."""
from flask import current_app


def service_router(local, remote):
    class Router:
        def __getattr__(self, name):
            target = remote if current_app.config.get('USE_SERVICE_CLIENTS') else local
            return getattr(target, name)
    return Router()
