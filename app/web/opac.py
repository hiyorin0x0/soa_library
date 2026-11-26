"""
Public University OPAC (Online Public Access Catalog) & Reader Self-Service Routes
"""
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


@opac_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    circulation_type = request.args.get('type', '')
    status = request.args.get('availability', '')
    sort_by = request.args.get('sort', 'title')

    pagination = BookService.get_all_books(
        page=page,
        per_page=12,
        search=search,
        category_id=category_id,
        status=status,
        circulation_type=circulation_type,
        sort_by=sort_by,
        order='desc' if sort_by in ('publish_year', 'created_at') else 'asc',
    )
    categories = BookService.get_all_categories()
    stats = BookService.get_statistics()
    facets = BookService.get_opac_facets(
        search=search,
        category_id=category_id,
        availability=status,
    )

    return render_template(
        'opac/index.html',
        pagination=pagination,
        books=pagination.items,
        categories=categories,
        stats=stats,
        facets=facets,
        search=search,
        selected_category=category_id,
        selected_type=circulation_type,
        selected_availability=status,
        sort_by=sort_by,
    )


@opac_bp.route('/book/<int:book_id>')
def book_detail(book_id):
    book = BookService.get_book_by_id(book_id)
    return render_template('opac/detail.html', book=book)


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
            flash(f'Đặt giữ sách thành công (Mã phiếu: {code}). Tài liệu đã được giữ tại quầy lưu thông trong 3 ngày.', 'success')
        else:
            flash(f'Đăng ký xếp hàng chờ thành công (Mã phiếu: {code}). Thư viện sẽ giữ bản sao ngay khi có người hoàn trả.', 'success')
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
