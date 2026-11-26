"""
Auth Service - SOA Service Layer
Handles staff authentication, RBAC authorization, and account safety
"""
from datetime import datetime
from flask_login import login_user, logout_user
from sqlalchemy import func
from app.extensions import db
from app.models.user import User


class AuthService:
    """Service responsible for staff authentication and account lifecycle."""

    @staticmethod
    def verify_credentials(username_or_email, password):
        ident = (username_or_email or '').strip()
        user = User.query.filter(
            (func.lower(User.username) == ident.lower()) | (func.lower(User.email) == ident.lower())
        ).first()

        if not user:
            return None, "Thông tin đăng nhập không chính xác."
        if not user.is_active:
            return None, "Tài khoản này đã tạm ngừng kích hoạt. Vui lòng liên hệ quản trị viên."
        if not user.check_password(password):
            return None, "Thông tin đăng nhập không chính xác."
        return user, None

    @staticmethod
    def record_login(user):
        user.last_login = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def authenticate(username_or_email, password, remember=False):
        user, error = AuthService.verify_credentials(username_or_email, password)
        if error:
            return None, error
        AuthService.record_login(user)
        login_user(user, remember=remember)
        return user, None

    @staticmethod
    def logout():
        logout_user()

    @staticmethod
    def create_user(username, email, password, role='librarian', full_name=''):
        username = (username or '').strip()
        email = (email or '').strip().lower()
        full_name = (full_name or '').strip()
        if not username or not email or not password:
            return None, "Vui lòng điền đầy đủ thông tin tài khoản."
        if len(password) < 6:
            return None, "Mật khẩu phải có tối thiểu 6 ký tự."
        if User.query.filter(func.lower(User.username) == username.lower()).first():
            return None, f"Tên đăng nhập '{username}' đã tồn tại."
        if User.query.filter(func.lower(User.email) == email).first():
            return None, f"Email '{email}' đã được sử dụng."

        user = User(
            username=username,
            email=email,
            full_name=full_name or username,
            role=role if role in ('admin', 'librarian') else 'librarian',
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user, None

    @staticmethod
    def change_password(user, old_password, new_password):
        if not user.check_password(old_password):
            return False, "Mật khẩu hiện tại không chính xác."
        if not new_password or len(new_password) < 6:
            return False, "Mật khẩu mới phải có tối thiểu 6 ký tự."
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return True, None

    @staticmethod
    def get_all_users():
        return User.query.order_by(User.role.asc(), User.full_name.asc()).all()

    @staticmethod
    def toggle_user_status(user_id, actor_id=None):
        user = db.get_or_404(User, user_id)
        if actor_id and user.id == actor_id:
            return None, "Không thể tự khóa tài khoản đang đăng nhập."
        if user.is_active and user.role == 'admin':
            active_admins = User.query.filter_by(role='admin', is_active=True).count()
            if active_admins <= 1:
                return None, "Phải duy trì ít nhất 1 quản trị viên đang hoạt động."
        user.is_active = not user.is_active
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return user, None


class PermissionService:
    ROLES = {
        'admin': ['manage_users', 'manage_books', 'manage_members', 'manage_loans',
                  'view_reports', 'delete_records', 'manage_categories'],
        'librarian': ['manage_books', 'manage_members', 'manage_loans', 'view_reports'],
    }

    @staticmethod
    def has_permission(user, permission):
        if not user or not user.is_active:
            return False
        return permission in PermissionService.ROLES.get(user.role, [])

    @staticmethod
    def require_admin(f):
        from functools import wraps
        from flask import abort
        from flask_login import current_user

        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin:
                abort(403)
            return f(*args, **kwargs)
        return decorated
