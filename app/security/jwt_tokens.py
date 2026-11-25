"""Short-lived JWTs for public API access and private service calls."""
from datetime import datetime, timedelta, timezone
import secrets

import jwt
from jwt.exceptions import InvalidTokenError
from flask import current_app


ISSUER = 'library-gateway'
ACCESS_AUDIENCE = 'library-api'
SERVICE_AUDIENCE_PREFIX = 'library-service:'
ACCESS_LIFETIME = timedelta(minutes=15)
SERVICE_LIFETIME = timedelta(seconds=60)
ALGORITHM = 'HS256'
_REQUIRED_CLAIMS = ['exp', 'iat', 'nbf', 'iss', 'sub', 'aud', 'jti', 'token_type']


def _now_timestamp():
    return int(datetime.now(timezone.utc).timestamp())


def create_access_token(user):
    now = _now_timestamp()
    payload = {
        'iss': ISSUER,
        'aud': ACCESS_AUDIENCE,
        'sub': str(user.id),
        'role': user.role,
        'token_type': 'access',
        'jti': secrets.token_urlsafe(18),
        'iat': now,
        'nbf': now,
        'exp': now + int(ACCESS_LIFETIME.total_seconds()),
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm=ALGORITHM)


def decode_access_token(token):
    claims = jwt.decode(
        token,
        current_app.config['JWT_SECRET_KEY'],
        algorithms=[ALGORITHM],
        audience=ACCESS_AUDIENCE,
        issuer=ISSUER,
        options={'require': _REQUIRED_CLAIMS},
    )
    if claims.get('token_type') != 'access':
        raise InvalidTokenError('Wrong token type')
    return claims


def create_service_token(service_name):
    now = _now_timestamp()
    payload = {
        'iss': ISSUER,
        'aud': f'{SERVICE_AUDIENCE_PREFIX}{service_name}',
        'sub': 'library-gateway',
        'service': service_name,
        'token_type': 'service',
        'jti': secrets.token_urlsafe(18),
        'iat': now,
        'nbf': now,
        'exp': now + int(SERVICE_LIFETIME.total_seconds()),
    }
    secret = current_app.config['SERVICE_JWT_SECRETS'][service_name]
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_service_token(token, expected_service):
    claims = jwt.decode(
        token,
        current_app.config['SERVICE_JWT_SECRETS'][expected_service],
        algorithms=[ALGORITHM],
        audience=f'{SERVICE_AUDIENCE_PREFIX}{expected_service}',
        issuer=ISSUER,
        options={'require': _REQUIRED_CLAIMS + ['service']},
    )
    if claims.get('token_type') != 'service' or claims.get('service') != expected_service:
        raise InvalidTokenError('Wrong service token')
    return claims
