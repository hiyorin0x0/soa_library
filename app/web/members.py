"""
Members Web Routes
"""
import csv
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required
from app.service_clients import members_client, loans_client
from app.service_access import service_router
from app.services.member_service import MemberService as LocalMemberService
from app.services.loan_service import LoanService as LocalLoanService
from app.services.auth_service import PermissionService

MemberService = service_router(LocalMemberService, members_client)
LoanService = service_router(LocalLoanService, loans_client)

members_bp = Blueprint('members', __name__)


@members_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    member_type = request.args.get('type', '')
    faculty = request.args.get('faculty', '')

    pagination = MemberService.get_all_members(
        page=page, search=search, status=status,
        member_type=member_type, faculty=faculty,
    )
    faculties = MemberService.get_faculties()
    stats = MemberService.get_statistics()

    return render_template(
        'members/index.html',
        pagination=pagination,
        members=pagination.items,
        faculties=faculties,
        stats=stats,
        search=search,
        selected_status=status,
        selected_type=member_type,
        selected_faculty=faculty,
    )


@members_bp.route('/clearance')
@login_required
def clearance():
    search = request.args.get('search', '')
    graduation_year = request.args.get('graduation_year', type=int)
    state = request.args.get('state', '')
    faculty = request.args.get('faculty', '')
    candidates = MemberService.list_clearance_candidates(
        search=search, graduation_year=graduation_year, status_filter=state, faculty=faculty,
    )
    faculties = MemberService.get_faculties()
    return render_template(
        'members/clearance.html',
        candidates=candidates,
        faculties=faculties,
        search=search,
        selected_year=graduation_year,
        selected_state=state,
        selected_faculty=faculty,
    )


@members_bp.route('/clearance/export')
@login_required
def export_clearance():
    candidates = MemberService.list_clearance_candidates(
        search=request.args.get('search', ''),
        graduation_year=request.args.get('graduation_year', type=int),
        status_filter=request.args.get('state', ''),
        faculty=request.args.get('faculty', ''),
    )
    buf = io.StringIO()
    buf.write('\ufeff')
    writer = csv.writer(buf)
    writer.writerow(['MSSV', 'Mã thẻ', 'Họ và tên', 'Đối tượng', 'Khoa', 'Lớp', 'Năm TN', 'Sách đang giữ', 'Phí chưa thanh toán (VNĐ)', 'Trạng thái xét duyệt'])
    state_labels = {'cleared': 'Đã hoàn tất', 'eligible': 'Đủ điều kiện', 'blocked': 'Đang vướng nghĩa vụ'}
    for c in candidates:
        writer.writerow([
            c.student_id or '',
            c.member_code,
            c.full_name,
            c.member_type,
            c.faculty or '',
            c.class_name or '',
            c.graduation_year or '',
            c.active_loans_count,
            int(c.unpaid_fine or 0),
            state_labels.get(c.clearance_state, c.clearance_state),
        ])
    return Response(
        buf.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="xet-hoan-tat-ra-truong.csv"'},
    )


@members_bp.route('/<int:member_id>/clearance', methods=['POST'])
@login_required
def confirm_clearance(member_id):
    member, error = MemberService.confirm_graduation_clearance(member_id)
    if error:
        flash(error, 'danger')
    else:
        flash(
            f'Đã xác nhận hoàn tất nghĩa vụ thư viện cho {member.full_name} ({member.student_id or member.member_code}).',
            'success',
        )
    if request.form.get('next') == 'clearance':
        return redirect(url_for('members.clearance'))
    return redirect(url_for('members.detail', member_id=member_id))


@members_bp.route('/<int:member_id>/renew-card', methods=['POST'])
@login_required
def renew_card(member_id):
    months = request.form.get('months', 12, type=int)
    member, error = MemberService.renew_card(member_id, months=months)
    if error:
        flash(error, 'danger')
    else:
        flash(f'Đã gia hạn thẻ của {member.full_name} thêm {months} tháng.', 'success')
    return redirect(url_for('members.detail', member_id=member_id))


@members_bp.route('/<int:member_id>')
@login_required
def detail(member_id):
    member = MemberService.get_member_by_id(member_id)
    clearance_info = MemberService.check_graduation_clearance(member_id)
    page = request.args.get('page', 1, type=int)
    loans_pagination = LoanService.get_all_loans(page=page, member_id=member_id, per_page=10)
    reservations = LoanService.get_reservations(member_id=member_id, status='active', per_page=10).items
    return render_template(
        'members/detail.html',
        member=member,
        clearance_info=clearance_info,
        loans_pagination=loans_pagination,
        reservations=reservations,
    )


@members_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        member, error = MemberService.create_member(request.form)
        if error:
            flash(error, 'danger')
            return render_template('members/create.html', form_data=request.form)
        flash(f'Đã cấp thẻ thư viện {member.member_code} cho {member.full_name}.', 'success')
        return redirect(url_for('members.detail', member_id=member.id))

    return render_template('members/create.html', form_data={})


@members_bp.route('/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(member_id):
    member = MemberService.get_member_by_id(member_id)

    if request.method == 'POST':
        updated, error = MemberService.update_member(member_id, request.form)
        if error:
            flash(error, 'danger')
        else:
            flash(f'Đã cập nhật hồ sơ của "{updated.full_name}".', 'success')
            return redirect(url_for('members.detail', member_id=member_id))

    return render_template('members/edit.html', member=member)


@members_bp.route('/<int:member_id>/delete', methods=['POST'])
@login_required
@PermissionService.require_admin
def delete(member_id):
    member = MemberService.get_member_by_id(member_id)
    name = member.full_name
    success, error = MemberService.delete_member(member_id)
    if error:
        flash(error, 'danger')
        return redirect(url_for('members.detail', member_id=member_id))
    flash(f'Đã xóa hồ sơ "{name}".', 'success')
    return redirect(url_for('members.index'))
