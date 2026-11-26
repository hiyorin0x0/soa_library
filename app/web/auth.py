"""
Auth Web Routes
"""
from urllib.parse import urlsplit
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app.services.auth_service import AuthService, PermissionService

auth_bp = Blueprint('auth', __name__)


def _safe_next_url(target):
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith('/'):
        return None
    return target


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not username or not password:
            flash('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.', 'danger')
            return render_template('auth/login.html')

        user, error = AuthService.authenticate(username, password, remember)
        if error:
            flash(error, 'danger')
            return render_template('auth/login.html', username=username)

        next_page = _safe_next_url(request.args.get('next'))
        return redirect(next_page or url_for('dashboard.index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    AuthService.logout()
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            old_pw = request.form.get('old_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            if new_pw != confirm_pw:
                flash('Mật khẩu xác nhận không trùng khớp.', 'danger')
            else:
                success, error = AuthService.change_password(current_user, old_pw, new_pw)
                if success:
                    flash('Đã cập nhật mật khẩu thành công.', 'success')
                else:
                    flash(error, 'danger')

    return render_template('auth/profile.html')


@auth_bp.route('/users')
@login_required
@PermissionService.require_admin
def users():
    users_list = AuthService.get_all_users()
    return render_template('auth/users.html', users=users_list)


@auth_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@PermissionService.require_admin
def create_user():
    if request.method == 'POST':
        user, error = AuthService.create_user(
            username=request.form.get('username'),
            email=request.form.get('email'),
            password=request.form.get('password'),
            role=request.form.get('role', 'librarian'),
            full_name=request.form.get('full_name'),
        )
        if error:
            flash(error, 'danger')
        else:
            flash(f'Đã khởi tạo tài khoản nhân sự {user.username}.', 'success')
            return redirect(url_for('auth.users'))

    return render_template('auth/create_user.html')


@auth_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@PermissionService.require_admin
def toggle_user(user_id):
    user, error = AuthService.toggle_user_status(user_id, actor_id=current_user.id)
    if error:
        flash(error, 'danger')
    else:
        status_text = 'kích hoạt' if user.is_active else 'tạm khóa'
        flash(f'Tài khoản {user.username} đã được {status_text}.', 'success')
    return redirect(url_for('auth.users'))
