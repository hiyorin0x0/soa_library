"""JWT authentication helpers for API Gateway and private service endpoints."""
from functools import wraps

from flask import abort, current_app, g, jsonify, request
from flask_login import current_user
from jwt.exceptions import InvalidTokenError

from app.security.jwt_tokens import decode_access_token, decode_service_token


def api_auth_required(view):
    """Accept an authenticated gateway session or a valid short-lived access JWT."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get('Authorization', '')
        scheme, _, token = authorization.partition(' ')
        has_bearer = scheme.lower() == 'bearer' and bool(token.strip())
        safe_method = request.method in {'GET', 'HEAD', 'OPTIONS'}

        if (safe_method and not has_bearer and current_user.is_authenticated
                and current_user.is_active):
            g.api_user = current_user
            return view(*args, **kwargs)

        if not has_bearer:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

        try:
            claims = decode_access_token(token.strip())
            user_id = int(claims['sub'])
        except (InvalidTokenError, KeyError, TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'Invalid or expired access token'}), 401

        from app.extensions import db
        from app.models.user import User
        user = db.session.get(User, user_id)
        if not user or not user.is_active or user.role != claims.get('role'):
            return jsonify({'status': 'error', 'message': 'Account is inactive or token is no longer valid'}), 401

        g.api_user = user
        return view(*args, **kwargs)
    return wrapped


def service_token_required(view):
    """Require a short-lived JWT issued specifically for this service."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_app.config.get('APP_ROLE') == 'monolith':
            if not current_user.is_authenticated:
                abort(401)
            return view(*args, **kwargs)

        authorization = request.headers.get('Authorization', '')
        scheme, _, token = authorization.partition(' ')
        service_name = current_app.config.get('SERVICE_NAME')
        if scheme.lower() != 'bearer' or not token.strip() or not service_name:
            return jsonify({'status': 'error', 'message': 'Service authentication required'}), 401
        try:
            decode_service_token(token.strip(), service_name)
        except InvalidTokenError:
            return jsonify({'status': 'error', 'message': 'Invalid or expired service token'}), 401
        return view(*args, **kwargs)
    return wrapped
