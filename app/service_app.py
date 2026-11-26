"""Standalone Flask application factory for a single domain service."""
from flask import Flask, jsonify
from sqlalchemy import text

from app.config import config
from app.extensions import db


SERVICE_BLUEPRINTS = {
    'books': ('app.api.books', 'api_books_bp', '/api/v1/books'),
    'members': ('app.api.members', 'api_members_bp', '/api/v1/members'),
    'loans': ('app.api.loans', 'api_loans_bp', '/api/v1/loans'),
    'reports': ('app.api.reports', 'api_reports_bp', '/api/v1/reports'),
}


def create_service_app(service_name, config_name=None):
    if service_name not in SERVICE_BLUEPRINTS:
        raise ValueError(f'Unknown service: {service_name}')
    config_name = config_name or 'development'
    app = Flask(f'library_{service_name}')
    app.config.from_object(config[config_name])
    app.config['APP_ROLE'] = service_name
    app.config['SERVICE_NAME'] = service_name
    service_key = app.config['SERVICE_JWT_SECRETS'].get(service_name)
    if (not service_key or len(service_key) < 32
            or service_key.lower().startswith(('replace-', 'generate-'))):
        key_name = f'{service_name.upper()}_SERVICE_JWT_SECRET'
        raise RuntimeError(f'Set a strong {key_name} (at least 32 characters) in .env')
    app.config['SERVICE_JWT_SECRETS'] = {service_name: service_key}
    db.init_app(app)

    # The legacy shared database has ORM relations across domains; load their models
    # in each process so SQLAlchemy can configure mappings consistently.
    from app.models import book, member, loan, user, reservation  # noqa: F401

    module_name, blueprint_name, prefix = SERVICE_BLUEPRINTS[service_name]
    module = __import__(module_name, fromlist=[blueprint_name])
    app.register_blueprint(getattr(module, blueprint_name), url_prefix=prefix)

    @app.get('/health')
    def health():
        try:
            db.session.execute(text('SELECT 1'))
            return jsonify({'status': 'ok', 'service': service_name})
        except Exception:
            app.logger.exception('Health check failed')
            return jsonify({'status': 'error', 'service': service_name}), 503

    @app.errorhandler(401)
    def unauthorized(_error):
        return jsonify({'status': 'error', 'message': 'Invalid service token'}), 401

    return app
