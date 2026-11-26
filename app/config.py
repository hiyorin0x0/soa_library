"""
Application Configuration
Supports multiple environments: development, testing, production
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

_DEV_FALLBACK_SECRETS = {
    'books': 'dev-only-books-service-jwt-secret-key-32chars-min',
    'members': 'dev-only-members-service-jwt-secret-key-32chars-min',
    'loans': 'dev-only-loans-service-jwt-secret-key-32chars-min',
    'reports': 'dev-only-reports-service-jwt-secret-key-32chars-min',
}


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    SERVICE_JWT_SECRETS = {
        service: os.environ.get(f'{service.upper()}_SERVICE_JWT_SECRET')
        for service in ('books', 'members', 'loans', 'reports')
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 15},
        'pool_pre_ping': True,
    }
    WTF_CSRF_ENABLED = True

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    REMEMBER_COOKIE_DURATION = timedelta(hours=12)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'

    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'static', 'img', 'books')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

    # Pagination
    BOOKS_PER_PAGE = 12
    MEMBERS_PER_PAGE = 15
    LOANS_PER_PAGE = 20

    # University Library Business Rules
    LIBRARY_NAME = 'Thư viện Trung tâm Đại học'
    LIBRARY_SHORT_NAME = 'LibCore University'
    LIBRARY_MODEL = 'Lưu thông học thuật nội bộ'
    LOAN_DURATION_DAYS = 14
    MAX_LOANS_PER_MEMBER = 5
    MAX_RESERVATIONS_PER_MEMBER = 3
    RESERVATION_HOLD_DAYS = 3
    FINE_PER_DAY = 2000           # VNĐ / ngày quá hạn
    DAMAGE_FINE_RATIO = 0.30      # 30% giá bìa khi trả sách hư hỏng nặng
    MIN_DAMAGE_FINE = 20000       # Phí tu bổ tối thiểu khi hư hỏng nặng
    DEFAULT_LOST_FEE = 50000      # Phí xử lý tài liệu không định giá bìa khi làm mất
    MAX_RENEWALS = 2
    BORROW_RULES = {
        'student': {
            'label': 'Sinh viên đại học',
            'max_loans': 5,
            'loan_days': 14,
            'renew_days': 7,
            'max_renewals': 2,
            'card_months': 48,
        },
        'postgrad': {
            'label': 'Học viên sau đại học',
            'max_loans': 7,
            'loan_days': 21,
            'renew_days': 7,
            'max_renewals': 2,
            'card_months': 24,
        },
        'lecturer': {
            'label': 'Giảng viên / Cán bộ',
            'max_loans': 10,
            'loan_days': 30,
            'renew_days': 14,
            'max_renewals': 2,
            'card_months': 60,
        },
    }

    # Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'thuvien@university.edu.vn'
    SERVICE_URLS = {
        'books': os.environ.get('BOOKS_SERVICE_URL', 'http://127.0.0.1:5001'),
        'members': os.environ.get('MEMBERS_SERVICE_URL', 'http://127.0.0.1:5002'),
        'loans': os.environ.get('LOANS_SERVICE_URL', 'http://127.0.0.1:5003'),
        'reports': os.environ.get('REPORTS_SERVICE_URL', 'http://127.0.0.1:5004'),
    }
    SERVICE_PORTS = {
        'gateway': int(os.environ.get('GATEWAY_PORT', 5000)),
        'books': int(os.environ.get('BOOKS_SERVICE_PORT', 5001)),
        'members': int(os.environ.get('MEMBERS_SERVICE_PORT', 5002)),
        'loans': int(os.environ.get('LOANS_SERVICE_PORT', 5003)),
        'reports': int(os.environ.get('REPORTS_SERVICE_PORT', 5004)),
    }


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-only-flask-session-secret-key-minimum-32-chars'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-only-api-gateway-jwt-secret-key-minimum-32-chars'
    SERVICE_JWT_SECRETS = {
        service: os.environ.get(f'{service.upper()}_SERVICE_JWT_SECRET') or _DEV_FALLBACK_SECRETS[service]
        for service in ('books', 'members', 'loans', 'reports')
    }
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library_dev.db')
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = 'testing-only-secret-key-at-least-32-characters-long'
    JWT_SECRET_KEY = 'testing-only-jwt-secret-key-at-least-32-characters'
    SERVICE_JWT_SECRETS = _DEV_FALLBACK_SECRETS.copy()
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library.db')
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
