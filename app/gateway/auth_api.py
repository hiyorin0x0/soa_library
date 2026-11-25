"""JWT authentication endpoints exposed by the API Gateway."""
from flask import Blueprint, g, jsonify, request

from app.extensions import csrf
from app.security.jwt_tokens import ACCESS_LIFETIME, create_access_token
from app.service_security import api_auth_required
from app.services.auth_service import AuthService


auth_api_bp = Blueprint('api_auth', __name__)


@auth_api_bp.post('/api/v1/auth/login')
@csrf.exempt
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or payload.get('email') or '').strip()
    password = payload.get('password') or ''
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username/email and password are required'}), 400

    user, error = AuthService.verify_credentials(username, password)
    if error:
        # Use one message for unknown accounts and incorrect passwords.
        return jsonify({'status': 'error', 'message': 'Invalid username/email or password'}), 401

    AuthService.record_login(user)
    token = create_access_token(user)
    response = jsonify({
        'status': 'success',
        'token_type': 'Bearer',
        'access_token': token,
        'expires_in': int(ACCESS_LIFETIME.total_seconds()),
        'user': user.to_dict(),
    })
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    return response


@auth_api_bp.get('/api/v1/auth/me')
@api_auth_required
def me():
    return jsonify({'status': 'success', 'data': g.api_user.to_dict()})
