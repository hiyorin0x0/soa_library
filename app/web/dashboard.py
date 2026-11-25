"""
Dashboard & SOA Architecture Web Routes
"""
from urllib.error import URLError
from urllib.request import urlopen
import json

from flask import Blueprint, current_app, render_template
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
    return render_template('dashboard/index.html', summary=summary, alerts=alerts)


@dashboard_bp.route('/architecture')
@login_required
def architecture():
    """Phạm vi bài toán, quy tắc nghiệp vụ và thiết kế dịch vụ SOA."""
    service_meta = [
        {
            'key': 'books',
            'name': 'Books Service',
            'vn_name': 'Dịch vụ Quản lý Tài liệu & Danh mục',
            'port': current_app.config['SERVICE_PORTS']['books'],
            'url': current_app.config['SERVICE_URLS']['books'],
            'purpose': 'Quản lý kho giáo trình, tài liệu tham khảo, khóa luận theo khoa/ngành; kiểm soát hình thức lưu thông (cho mượn về vs. chỉ đọc tại chỗ) và giá trị bồi thường.',
            'endpoints': [
                'GET /api/v1/books/ — Tra cứu, lọc theo thể loại & hình thức lưu thông',
                'POST /api/v1/books/ — Nhập đầu sách mới kèm mã ISBN, vị trí kệ',
                'PUT /api/v1/books/<id> — Cập nhật bản sao & quy chế lưu thông',
                'GET /api/v1/books/categories — Quản lý danh mục ngành/thể loại',
            ],
        },
        {
            'key': 'members',
            'name': 'Members Service',
            'vn_name': 'Dịch vụ Quản lý Độc giả & Xác nhận Ra trường',
            'port': current_app.config['SERVICE_PORTS']['members'],
            'url': current_app.config['SERVICE_URLS']['members'],
            'purpose': 'Xác thực tư cách độc giả nội bộ trường qua MSSV/MCB (miễn phí thẻ), quản lý hạn mức mượn theo đối tượng và kiểm tra điều kiện hoàn tất nghĩa vụ thư viện trước khi tốt nghiệp.',
            'endpoints': [
                'GET /api/v1/members/ — Tra cứu độc giả theo MSSV, khoa, lớp, trạng thái',
                'POST /api/v1/members/ — Cấp thẻ thư viện miễn phí gắn MSSV/MCB',
                'GET /api/v1/members/clearance — Danh sách xét hoàn trả sách ra trường',
                'POST /api/v1/members/<id>/clearance — Xác nhận hoàn tất nghĩa vụ ra trường',
            ],
        },
        {
            'key': 'loans',
            'name': 'Loans Service',
            'vn_name': 'Dịch vụ Lưu thông Mượn – Trả & Xử lý Vi phạm',
            'port': current_app.config['SERVICE_PORTS']['loans'],
            'url': current_app.config['SERVICE_URLS']['loans'],
            'purpose': 'Thực thi toàn bộ quy tắc nghiệp vụ mượn trả: chặn sách đọc tại chỗ, chặn độc giả đang quá hạn hoặc nợ phạt, tính phí phạt trả muộn tự động (2.000đ/ngày), thanh toán phạt và bồi thường mất sách.',
            'endpoints': [
                'POST /api/v1/loans/ — Tạo phiếu mượn (tự động kiểm tra đủ 7 ràng buộc)',
                'POST /api/v1/loans/<id>/return — Trả sách & tự động tính phí trả muộn',
                'POST /api/v1/loans/<id>/pay-fine — Ghi nhận thanh toán phạt & mở khóa quyền mượn',
                'POST /api/v1/loans/<id>/renew — Gia hạn phiếu mượn (tối đa 2 lần)',
                'POST /api/v1/loans/<id>/lost — Báo mất sách & tính đền bù 100% giá bìa',
            ],
        },
        {
            'key': 'reports',
            'name': 'Reports & Alerts Service',
            'vn_name': 'Dịch vụ Thống kê, Báo cáo & Cảnh báo',
            'port': current_app.config['SERVICE_PORTS']['reports'],
            'url': current_app.config['SERVICE_URLS']['reports'],
            'purpose': 'Tổng hợp dữ liệu đa dịch vụ phục vụ Ban Giám hiệu & Thủ thư: tỷ lệ luân chuyển giáo trình, thống kê theo khoa, theo dõi quá hạn, công nợ phạt và cảnh báo sinh viên sắp ra trường còn giữ sách.',
            'endpoints': [
                'GET /api/v1/reports/dashboard — Tổng hợp số liệu điều hành',
                'GET /api/v1/reports/overdue — Báo cáo quá hạn & phí phạt dự kiến',
                'GET /api/v1/reports/faculty-loans — Thống kê lượt mượn theo khoa',
                'GET /api/v1/reports/alerts — Cảnh báo nghiệp vụ theo thời gian thực',
            ],
        },
    ]

    use_clients = current_app.config.get('USE_SERVICE_CLIENTS', False)
    for svc in service_meta:
        if not use_clients:
            svc['health'] = 'local'
        else:
            try:
                with urlopen(f"{svc['url'].rstrip('/')}/health", timeout=1.5) as resp:
                    payload = json.loads(resp.read().decode('utf-8'))
                    svc['health'] = 'ok' if payload.get('status') == 'ok' else 'error'
            except (URLError, TimeoutError, OSError, ValueError):
                svc['health'] = 'offline'

    return render_template(
        'dashboard/architecture.html',
        services=service_meta,
        borrow_rules=current_app.config.get('BORROW_RULES', {}),
        fine_per_day=current_app.config.get('FINE_PER_DAY', 2000),
        gateway_port=current_app.config['SERVICE_PORTS']['gateway'],
        app_role=current_app.config.get('APP_ROLE', 'monolith'),
    )
