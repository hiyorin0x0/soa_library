"""
Public QNU OPAC (Online Public Access Catalog) & Reader Self-Service Routes
Thư viện – Trung tâm Số và Học liệu, Trường Đại học Quy Nhơn
"""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.service_clients import books_client, members_client, loans_client
from app.service_access import service_router
from app.services.book_service import BookService as LocalBookService
from app.services.member_service import MemberService as LocalMemberService
from app.services.loan_service import LoanService as LocalLoanService

BookService = service_router(LocalBookService, books_client)
MemberService = service_router(LocalMemberService, members_client)
LoanService = service_router(LocalLoanService, loans_client)

opac_bp = Blueprint('opac', __name__)

QNU_ROOMS = [
    {'code': 'P.GT', 'name': 'Phòng Giáo trình', 'floor': 'Tầng 1 · Tòa nhà Thư viện 15 tầng'},
    {'code': 'P.M', 'name': 'Phòng Mượn về nhà', 'floor': 'Tầng 1 · Tòa nhà Thư viện 15 tầng'},
    {'code': 'P.DM1', 'name': 'Phòng Đọc Mở 1', 'floor': 'Tầng 2 · Tài liệu tham khảo Tiếng Việt'},
    {'code': 'P.DM2', 'name': 'Phòng Đọc Mở 2', 'floor': 'Tầng 3 · Ngoại văn, Báo chí & Luận văn'},
]


def get_qnu_open_status():
    """Real QNU Library opening hours (Mon-Fri 07:30-11:30 & 13:45-16:45, Sat-Sun 07:30-11:30 & 14:00-17:00)."""
    now = datetime.now()
    mins = now.hour * 60 + now.minute
    is_weekend = now.weekday() >= 5

    morning_open, morning_close = 7 * 60 + 30, 11 * 60 + 30
    aft_open = 14 * 60 if is_weekend else (13 * 60 + 45)
    aft_close = 17 * 60 if is_weekend else (16 * 60 + 45)

    if morning_open <= mins <= morning_close or aft_open <= mins <= aft_close:
        return {'is_open': True, 'label': 'Đang mở cửa phục vụ'}
    if morning_close < mins < aft_open:
        reopen = '14:00' if is_weekend else '13:45'
        return {'is_open': False, 'label': f'Nghỉ trưa · Mở lại lúc {reopen}'}
    return {'is_open': False, 'label': 'Ngoài giờ mở cửa · Mở lại 07:30'}


def parse_qnu_location(loc, circulation_type='borrowable'):
    loc_str = (loc or '').strip()
    for r in QNU_ROOMS:
        if loc_str.upper().startswith(r['code']):
            return {
                'room_name': r['name'],
                'floor': r['floor'],
                'shelf': loc_str,
            }
    if circulation_type == 'reference_only':
        return {'room_name': 'Phòng Đọc Mở 2', 'floor': 'Tầng 3 · Tòa nhà Thư viện 15 tầng', 'shelf': loc_str or 'P.DM2'}
    return {'room_name': 'Phòng Giáo trình & Mượn', 'floor': 'Tầng 1 · Tòa nhà Thư viện 15 tầng', 'shelf': loc_str or 'P.GT'}


@opac_bp.context_processor
def inject_qnu_context():
    return {
        'qnu_status': get_qnu_open_status(),
        'qnu_rooms': QNU_ROOMS,
    }


@opac_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    circulation_type = request.args.get('type', '')
    status = request.args.get('availability', '')
    room = request.args.get('room', '')
    sort_by = request.args.get('sort', 'title')
    view_mode = request.args.get('view', 'grid')
    if view_mode not in ('grid', 'list'):
        view_mode = 'grid'

    pagination = BookService.get_all_books(
        page=page,
        per_page=12,
        search=search,
        category_id=category_id,
        status=status,
        circulation_type=circulation_type,
        room=room,
        sort_by=sort_by,
        order='desc' if sort_by in ('publish_year', 'created_at', 'available_copies') else 'asc',
    )
    categories = BookService.get_all_categories()
    stats = BookService.get_statistics()
    facets = BookService.get_opac_facets(
        search=search,
        category_id=category_id,
        availability=status,
        room=room,
    )

    is_default_home = (page == 1 and not search and not category_id and not circulation_type and not status and not room)
    featured_books = BookService.get_popular_books(limit=6) if is_default_home else []

    return render_template(
        'opac/index.html',
        pagination=pagination,
        books=pagination.items,
        categories=categories,
        stats=stats,
        facets=facets,
        featured_books=featured_books,
        is_default_home=is_default_home,
        search=search,
        selected_category=category_id,
        selected_type=circulation_type,
        selected_availability=status,
        selected_room=room,
        sort_by=sort_by,
        view_mode=view_mode,
    )


@opac_bp.route('/book/<int:book_id>')
def book_detail(book_id):
    book = BookService.get_book_by_id(book_id)
    loc_info = parse_qnu_location(book.location, getattr(book, 'circulation_type', 'borrowable'))
    related_books = []
    if getattr(book, 'category_id', None):
        same_cat = BookService.get_all_books(page=1, per_page=5, category_id=book.category_id).items
        related_books = [b for b in same_cat if b.id != book.id][:4]
    return render_template(
        'opac/detail.html',
        book=book,
        loc_info=loc_info,
        related_books=related_books,
    )


@opac_bp.route('/book/<int:book_id>/reserve', methods=['POST'])
def reserve_book(book_id):
    identifier = request.form.get('identifier', '').strip()
    verify = request.form.get('verify', '').strip()
    notes = request.form.get('notes', '').strip()

    portal_data, err = MemberService.lookup_reader_portal(identifier, verify)
    if err:
        flash(err, 'danger')
        return redirect(url_for('opac.book_detail', book_id=book_id))

    member = portal_data['member']
    member_id = member['id'] if isinstance(member, dict) else member.id
    res, res_err = LoanService.create_reservation(book_id=book_id, member_id=member_id, notes=notes)
    if res_err:
        flash(res_err, 'danger')
    else:
        code = res['reservation_code'] if isinstance(res, dict) else res.reservation_code
        rstatus = res['status'] if isinstance(res, dict) else res.status
        if rstatus == 'ready':
            flash(f'Đặt giữ sách thành công (Mã phiếu: {code}). Mời bạn đến Tầng 1 Tòa nhà Thư viện nhận sách trong vòng 3 ngày.', 'success')
        else:
            flash(f'Đã đăng ký chờ mượn (Mã phiếu: {code}). Thư viện sẽ ưu tiên giữ bản sao ngay khi có người trả.', 'success')
    return redirect(url_for('opac.book_detail', book_id=book_id))


@opac_bp.route('/reader', methods=['GET', 'POST'])
def reader_lookup():
    result = None
    identifier = ''
    verify = ''
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        verify = request.form.get('verify', '').strip()
        result, error = MemberService.lookup_reader_portal(identifier, verify)
        if error:
            flash(error, 'danger')

    return render_template(
        'opac/reader.html',
        result=result,
        identifier=identifier,
        verify=verify,
    )
