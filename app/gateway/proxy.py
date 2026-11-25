"""Authenticated API Gateway proxy for the domain services."""
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import abort, current_app, request, Response
from flask import g
from app.extensions import csrf
from app.service_security import api_auth_required
from app.security.jwt_tokens import create_service_token


def register_service_gateway(app):
    service_names = {'books', 'members', 'loans', 'reports'}

    def forward(service, path=''):
        if service not in service_names:
            abort(404)
        if request.method == 'DELETE' and not g.api_user.is_admin:
            abort(403)
        target = current_app.config['SERVICE_URLS'][service].rstrip('/') + f'/api/v1/{service}/' + path
        if request.query_string:
            target += '?' + request.query_string.decode('ascii', errors='ignore')
        headers = {'Authorization': f'Bearer {create_service_token(service)}'}
        if request.content_type:
            headers['Content-Type'] = request.content_type
        outbound = Request(target, data=request.get_data() or None, headers=headers, method=request.method)
        try:
            with urlopen(outbound, timeout=10) as upstream:
                return Response(upstream.read(), status=upstream.status,
                                content_type=upstream.headers.get('Content-Type', 'application/json'))
        except HTTPError as error:
            return Response(error.read(), status=error.code,
                            content_type=error.headers.get('Content-Type', 'application/json'))
        except (URLError, TimeoutError, OSError):
            return {'status': 'error', 'message': f'Service {service} hiện không khả dụng.'}, 503

    # JWT-authenticated API calls are exempt from cookie CSRF checks. The auth
    # decorator requires a bearer token for all writes, so session cookies alone
    # cannot be used to perform cross-site mutations.
    gateway_forward = csrf.exempt(api_auth_required(forward))
    app.add_url_rule('/api/v1/<service>/', 'gateway_api_root', gateway_forward,
                     defaults={'path': ''}, methods=['GET', 'POST'])
    app.add_url_rule('/api/v1/<service>/<path:path>', 'gateway_api', gateway_forward,
                     methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
