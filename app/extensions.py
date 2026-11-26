"""
Flask Extensions - initialized here, bound to app in create_app()
"""
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_mail import Mail

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()
mail = Mail()

# Login manager config
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'


@event.listens_for(Engine, 'connect')
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    """Enable WAL journaling and foreign keys so multi-process SOA services never lock SQLite."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')
        cursor.execute('PRAGMA foreign_keys=ON;')
        cursor.execute('PRAGMA busy_timeout=10000;')
        cursor.close()
