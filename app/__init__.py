"""
Flask Application Factory
SOA-based University Library System
"""
import os
from datetime import date, datetime
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
        required_secrets = {
            'SECRET_KEY': app.config.get('SECRET_KEY'),
            'JWT_SECRET_KEY': app.config.get('JWT_SECRET_KEY'),
        }
        required_secrets.update({
            f'{service.upper()}_SERVICE_JWT_SECRET': secret
            for service, secret in app.config['SERVICE_JWT_SECRETS'].items()
        })
        missing = [
            name for name, secret in required_secrets.items()
            if not secret or len(secret) < 32
            or secret.lower().startswith(('replace-', 'generate-'))
        ]
        if missing:
            raise RuntimeError('Set strong (at least 32-character) secrets in .env: ' + ', '.join(missing))

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Ensure all models are registered
    from app.models import user, book, member, loan, reservation  # noqa: F401

    # Register Web UI blueprints
    from app.web.auth import auth_bp
    from app.web.books import books_bp
    from app.web.members import members_bp
    from app.web.loans import loans_bp
    from app.web.dashboard import dashboard_bp
    from app.web.opac import opac_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(opac_bp, url_prefix='/catalog')
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

    register_error_handlers(app)
    register_template_filters(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return response

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
        try:
            return f"{int(round(float(value))):,}₫".replace(',', '.')
        except (ValueError, TypeError):
            return "0₫"

    @app.template_filter('fmt_date')
    def fmt_date(value):
        if not value:
            return '—'
        if isinstance(value, datetime):
            return value.strftime('%d/%m/%Y')
        if isinstance(value, date):
            return value.strftime('%d/%m/%Y')
        if isinstance(value, str):
            try:
                return date.fromisoformat(value[:10]).strftime('%d/%m/%Y')
            except ValueError:
                return value
        return str(value)

    @app.template_filter('fmt_datetime')
    def fmt_datetime(value):
        if not value:
            return '—'
        if isinstance(value, datetime):
            return value.strftime('%d/%m/%Y %H:%M')
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).strftime('%d/%m/%Y %H:%M')
            except ValueError:
                return value
        return str(value)

    @app.template_filter('truncate_text')
    def truncate_text(value, length=100):
        if value and len(value) > length:
            return value[:length] + '…'
        return value or ''

    @app.template_filter('status_badge')
    def status_badge(status):
        badges = {
            'available': '<span class="status-pill pill-emerald"><span class="dot"></span>Đang phục vụ</span>',
            'unavailable': '<span class="status-pill pill-slate"><span class="dot"></span>Tạm ngưng</span>',
            'borrowed': '<span class="status-pill pill-amber"><span class="dot"></span>Đang mượn</span>',
            'lost': '<span class="status-pill pill-rose"><span class="dot"></span>Làm mất sách</span>',
            'active': '<span class="status-pill pill-emerald"><span class="dot"></span>Đang hoạt động</span>',
            'suspended': '<span class="status-pill pill-rose"><span class="dot"></span>Đang khóa thẻ</span>',
            'graduated': '<span class="status-pill pill-indigo"><span class="dot"></span>Đã thanh lý thẻ</span>',
            'inactive': '<span class="status-pill pill-slate"><span class="dot"></span>Ngưng hoạt động</span>',
            'overdue': '<span class="status-pill pill-rose"><span class="dot"></span>Quá hạn</span>',
            'returned': '<span class="status-pill pill-sky"><span class="dot"></span>Đã trả sách</span>',
            'borrowable': '<span class="status-pill pill-emerald"><span class="dot"></span>Cho mượn về</span>',
            'reference_only': '<span class="status-pill pill-slate"><span class="dot"></span>Đọc tại thư viện</span>',
            'pending': '<span class="status-pill pill-amber"><span class="dot"></span>Chờ sách trả về</span>',
            'ready': '<span class="status-pill pill-emerald"><span class="dot"></span>Có sách tại quầy</span>',
            'fulfilled': '<span class="status-pill pill-sky"><span class="dot"></span>Đã nhận sách</span>',
            'cancelled': '<span class="status-pill pill-slate"><span class="dot"></span>Đã hủy</span>',
            'expired': '<span class="status-pill pill-rose"><span class="dot"></span>Quá hạn nhận</span>',
        }
        return badges.get(status, f'<span class="status-pill pill-slate">{status}</span>')

    @app.template_filter('member_type_label')
    def member_type_label(mtype):
        labels = {
            'student': 'Sinh viên',
            'postgrad': 'Học viên cao học',
            'lecturer': 'Giảng viên / Cán bộ',
        }
        return labels.get(mtype, mtype or '—')

    @app.template_filter('condition_label')
    def condition_label(cond):
        labels = {
            'good': 'Nguyên vẹn',
            'fair': 'Khá',
            'poor': 'Cũ nhẹ',
            'damaged': 'Hư hỏng nặng',
            'lost': 'Làm mất sách',
        }
        return labels.get(cond, cond or '—')

    @app.template_filter('fine_reason_label')
    def fine_reason_label(reason):
        labels = {
            'overdue': 'Tiền phạt trả muộn',
            'damaged': 'Đền bù hư hỏng sách',
            'overdue_damaged': 'Phạt trả muộn & hư hỏng',
            'lost': 'Đền bù làm mất sách',
        }
        return labels.get(reason, 'Tiền phạt / Đền bù')
