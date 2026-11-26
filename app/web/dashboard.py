"""
Dashboard & Service Health Web Routes
"""
from urllib.error import URLError
from urllib.request import urlopen
import json
import time

from flask import Blueprint, current_app, render_template, redirect, url_for
from flask_login import login_required
from app.service_clients import reports_client
from app.service_access import service_router
from app.services.report_service import ReportService as LocalReportService
from app.services.notification_service import NotificationService as LocalNotificationService

ReportService = service_router(LocalReportService, reports_client)
NotificationService = service_router(LocalNotificationService, reports_client)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    summary = ReportService.get_dashboard_summary()
    alerts = NotificationService.get_system_alerts()
    monthly_data = ReportService.get_monthly_loan_chart(months=6)
    category_dist = ReportService.get_category_distribution()
    return render_template(
        'dashboard/index.html',
        summary=summary,
        alerts=alerts,
        monthly_data=monthly_data,
        category_dist=category_dist,
    )


@dashboard_bp.route('/system')
@login_required
def system_status():
    """Real-time SOA service health, latency, and circulation parameters."""
    service_meta = [
        {
            'key': 'books',
            'name': 'Catalog Service',
            'code': 'svc-books',
            'port': current_app.config['SERVICE_PORTS']['books'],
            'url': current_app.config['SERVICE_URLS']['books'],
            'prefix': '/api/v1/books',
            'domain': 'Quản lý danh mục, tồn kho bản sao & phân loại ngành',
        },
        {
            'key': 'members',
            'name': 'Member & Clearance Service',
            'code': 'svc-members',
            'port': current_app.config['SERVICE_PORTS']['members'],
            'url': current_app.config['SERVICE_URLS']['members'],
            'prefix': '/api/v1/members',
            'domain': 'Hồ sơ thẻ độc giả, tra cứu OPAC & xét hoàn tất tốt nghiệp',
        },
        {
            'key': 'loans',
            'name': 'Circulation & Hold Service',
            'code': 'svc-loans',
            'port': current_app.config['SERVICE_PORTS']['loans'],
            'url': current_app.config['SERVICE_URLS']['loans'],
            'prefix': '/api/v1/loans',
            'domain': 'Mượn trả, gia hạn, hàng đợi đặt chỗ & hạch toán phí',
        },
        {
            'key': 'reports',
            'name': 'Analytics & Alert Service',
            'code': 'svc-reports',
            'port': current_app.config['SERVICE_PORTS']['reports'],
            'url': current_app.config['SERVICE_URLS']['reports'],
            'prefix': '/api/v1/reports',
            'domain': 'Tổng hợp số liệu vận hành, thống kê theo khoa & cảnh báo',
        },
    ]

    use_clients = current_app.config.get('USE_SERVICE_CLIENTS', False)
    for svc in service_meta:
        if not use_clients:
            svc['health'] = 'local'
            svc['latency_ms'] = 1
        else:
            t0 = time.perf_counter()
            try:
                with urlopen(f"{svc['url'].rstrip('/')}/health", timeout=1.5) as resp:
                    payload = json.loads(resp.read().decode('utf-8'))
                    svc['latency_ms'] = max(1, round((time.perf_counter() - t0) * 1000))
                    svc['health'] = 'ok' if payload.get('status') == 'ok' else 'error'
            except (URLError, TimeoutError, OSError, ValueError):
                svc['latency_ms'] = None
                svc['health'] = 'offline'

    return render_template(
        'dashboard/architecture.html',
        services=service_meta,
        borrow_rules=current_app.config.get('BORROW_RULES', {}),
        fine_per_day=current_app.config.get('FINE_PER_DAY', 2000),
        gateway_port=current_app.config['SERVICE_PORTS']['gateway'],
        app_role=current_app.config.get('APP_ROLE', 'monolith'),
    )


@dashboard_bp.route('/architecture')
@login_required
def architecture():
    return redirect(url_for('dashboard.system_status'))
