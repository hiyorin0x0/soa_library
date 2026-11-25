"""
Auth Service - SOA Service Layer
Handles authentication, authorization, and user management
"""
from datetime import datetime
from flask import current_app
from flask_login import login_user, logout_user
from app.extensions import db
from app.models.user import User


class AuthService:
    """
    Service responsible for authentication and authorization.
    """

    @staticmethod
    def verify_credentials(username_or_email, password):
        """
        Verify credentials without establishing a browser session.
        Returns: (User, error_message)
        """
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if not user:
            return None, "Tài khoản không tồn tại."

        if not user.is_active:
            return None, "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên."

        if not user.check_password(password):
            return None, "Mật khẩu không chính xác."

        return user, None

    @staticmethod
    def record_login(user):
        user.last_login = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def authenticate(username_or_email, password, remember=False):
        """Authenticate a user and establish the existing browser session."""
        user, error = AuthService.verify_credentials(username_or_email, password)
        if error:
            return None, error

        # Update last login
        AuthService.record_login(user)

        login_user(user, remember=remember)
        return user, None

    @staticmethod
    def logout():
        """Logout current user"""
        logout_user()

    @staticmethod
    def create_user(username, email, password, role='librarian', full_name=''):
        """
        Create a new staff user.
        Returns: (User, error_message)
        """
        if User.query.filter_by(username=username).first():
            return None, f"Tên đăng nhập '{username}' đã tồn tại."
        if User.query.filter_by(email=email).first():
            return None, f"Email '{email}' đã được đăng ký."

        user = User(
            username=username,
            email=email,
            full_name=full_name or username,
            role=role,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user, None

    @staticmethod
    def change_password(user, old_password, new_password):
        """Change user password"""
        if not user.check_password(old_password):
            return False, "Mật khẩu hiện tại không đúng."
        if len(new_password) < 6:
            return False, "Mật khẩu mới phải có ít nhất 6 ký tự."
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return True, None

    @staticmethod
    def get_all_users():
        return User.query.order_by(User.full_name).all()

    @staticmethod
    def toggle_user_status(user_id):
        """Toggle user active status"""
        user = User.query.get_or_404(user_id)
        user.is_active = not user.is_active
        db.session.commit()
        return user


class PermissionService:
    """
    Centralized permission checking.
    """
    ROLES = {
        'admin': ['manage_users', 'manage_books', 'manage_members', 'manage_loans',
                  'view_reports', 'delete_records', 'manage_categories'],
        'librarian': ['manage_books', 'manage_members', 'manage_loans', 'view_reports'],
    }

    @staticmethod
    def has_permission(user, permission):
        """Check if user has a specific permission"""
        if not user or not user.is_active:
            return False
        return permission in PermissionService.ROLES.get(user.role, [])

    @staticmethod
    def require_admin(f):
        """Decorator to require admin role"""
        from functools import wraps
        from flask import abort
        from flask_login import current_user

        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin:
                abort(403)
            return f(*args, **kwargs)
        return decorated
