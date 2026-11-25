"""
Application Configuration
Supports multiple environments: development, testing, production
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    SERVICE_JWT_SECRETS = {
        service: os.environ.get(f'{service.upper()}_SERVICE_JWT_SECRET')
        for service in ('books', 'members', 'loans', 'reports')
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
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
    
    # University Library Business Rules (Miễn phí cho SV/GV nội bộ trường)
    LIBRARY_NAME = 'Thư viện Trường Đại học'
    LIBRARY_SHORT_NAME = 'Thư viện Đại học'
    LIBRARY_MODEL = 'Miễn phí khuyến khích đọc (Nội bộ nhà trường)'
    LOAN_DURATION_DAYS = 14
    MAX_LOANS_PER_MEMBER = 5
    FINE_PER_DAY = 2000  # VNĐ / ngày quá hạn (chế tài đảm bảo xoay vòng tài liệu)
    MAX_RENEWALS = 2
    BORROW_RULES = {
        'student': {
            'label': 'Sinh viên',
            'max_loans': 5,
            'loan_days': 14,
            'renew_days': 7,
            'max_renewals': 2,
            'card_months': 48,
        },
        'postgrad': {
            'label': 'Học viên cao học',
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
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library_dev.db')
    SQLALCHEMY_ECHO = False  # Set True for SQL debug


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = 'testing-only-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
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
