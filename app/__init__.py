"""
Flask Application Factory
SOA-based Library Management System
"""
import os
from flask import Flask, render_template
from app.config import config
from app.extensions import db, login_manager, csrf, migrate, mail


def create_app(config_name=None, role='monolith'):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config['APP_ROLE'] = role
    app.config['USE_SERVICE_CLIENTS'] = role == 'gateway'

    if role == 'gateway':
        required_secrets = {'SECRET_KEY': app.config.get('SECRET_KEY'),
                            'JWT_SECRET_KEY': app.config.get('JWT_SECRET_KEY')}
        required_secrets.update({f'{service.upper()}_SERVICE_JWT_SECRET': secret
                                 for service, secret in app.config['SERVICE_JWT_SECRETS'].items()})
        missing = [name for name, secret in required_secrets.items()
                   if not secret or len(secret) < 32
                   or secret.lower().startswith(('replace-', 'generate-'))]
        if missing:
            raise RuntimeError('Set strong (at least 32-character) secrets in .env: ' + ', '.join(missing))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Register blueprints - Web UI routes (the gateway owns the browser session).
    from app.web.auth import auth_bp
    from app.web.books import books_bp
    from app.web.members import members_bp
    from app.web.loans import loans_bp
    from app.web.dashboard import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(books_bp, url_prefix='/books')
    app.register_blueprint(members_bp, url_prefix='/members')
    app.register_blueprint(loans_bp, url_prefix='/loans')

    if role == 'monolith':
        from app.api.books import api_books_bp
        from app.api.members import api_members_bp
        from app.api.loans import api_loans_bp
        from app.api.reports import api_reports_bp

        app.register_blueprint(api_books_bp, url_prefix='/api/v1/books')
        app.register_blueprint(api_members_bp, url_prefix='/api/v1/members')
        app.register_blueprint(api_loans_bp, url_prefix='/api/v1/loans')
        app.register_blueprint(api_reports_bp, url_prefix='/api/v1/reports')
    else:
        from app.gateway.auth_api import auth_api_bp
        from app.gateway.proxy import register_service_gateway
        app.register_blueprint(auth_api_bp)
        register_service_gateway(app)

    # Register error handlers
    register_error_handlers(app)

    # Register template filters
    register_template_filters(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return response

    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500


def register_template_filters(app):
    @app.template_filter('vnd')
    def vnd_format(value):
        """Format number as Vietnamese Dong"""
        try:
            return f"{int(value):,}₫".replace(',', '.')
        except (ValueError, TypeError):
            return "0₫"

    @app.template_filter('truncate_text')
    def truncate_text(value, length=100):
        if value and len(value) > length:
            return value[:length] + '...'
        return value or ''

    @app.template_filter('status_badge')
    def status_badge(status):
        badges = {
            'available': '<span class="badge-tag tag-success">Còn sẵn</span>',
            'unavailable': '<span class="badge-tag tag-neutral">Tạm ngưng</span>',
            'borrowed': '<span class="badge-tag tag-warning">Đang mượn</span>',
            'lost': '<span class="badge-tag tag-danger">Báo mất</span>',
            'active': '<span class="badge-tag tag-success">Đang hoạt động</span>',
            'suspended': '<span class="badge-tag tag-danger">Tạm khóa</span>',
            'graduated': '<span class="badge-tag tag-navy">Đã ra trường</span>',
            'inactive': '<span class="badge-tag tag-neutral">Ngưng hoạt động</span>',
            'overdue': '<span class="badge-tag tag-danger">Quá hạn</span>',
            'returned': '<span class="badge-tag tag-info">Đã trả</span>',
            'borrowable': '<span class="badge-tag tag-success">Cho mượn về</span>',
            'reference_only': '<span class="badge-tag tag-navy">Đọc tại chỗ</span>',
        }
        return badges.get(status, f'<span class="badge-tag tag-neutral">{status}</span>')

    @app.template_filter('member_type_label')
    def member_type_label(mtype):
        labels = {
            'student': 'Sinh viên',
            'postgrad': 'Học viên cao học',
            'lecturer': 'Giảng viên / Cán bộ',
        }
        return labels.get(mtype, mtype or '-')
