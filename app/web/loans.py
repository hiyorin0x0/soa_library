"""
Loans Web Routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.service_clients import loans_client, reports_client
from app.service_access import service_router
from app.services.loan_service import LoanService as LocalLoanService
from app.services.report_service import ReportService as LocalReportService
from app.services.auth_service import PermissionService

LoanService = service_router(LocalLoanService, loans_client)
ReportService = service_router(LocalReportService, reports_client)

loans_bp = Blueprint('loans', __name__)


@loans_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')

    pagination = LoanService.get_all_loans(
        page=page, search=search, status=status
    )
    stats = LoanService.get_statistics()

    return render_template('loans/index.html',
                           pagination=pagination, loans=pagination.items,
                           search=search, selected_status=status, stats=stats)


@loans_bp.route('/<int:loan_id>')
@login_required
def detail(loan_id):
    loan = LoanService.get_loan_by_id(loan_id)
    return render_template('loans/detail.html', loan=loan)


@loans_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        book_id = request.form.get('book_id', type=int)
        member_id = request.form.get('member_id', type=int)
        notes = request.form.get('notes', '')
        condition = request.form.get('condition', 'good')

        if not book_id or not member_id:
            flash('Vui lòng chọn đầy đủ độc giả (MSSV/MCB) và tài liệu cần mượn.', 'danger')
            return render_template('loans/create.html')

        loan, error = LoanService.create_loan(
            book_id=book_id, member_id=member_id, librarian_id=current_user.id,
            loan_duration=None, notes=notes, condition=condition,
        )

        if error:
            flash(error, 'danger')
        else:
            flash(f'Tạo phiếu mượn {loan.loan_code} thành công! Hạn trả: {loan.due_date.strftime("%d/%m/%Y")}', 'success')
            return redirect(url_for('loans.detail', loan_id=loan.id))

    return render_template('loans/create.html')


@loans_bp.route('/<int:loan_id>/return', methods=['GET', 'POST'])
@login_required
def return_book(loan_id):
    loan = LoanService.get_loan_by_id(loan_id)

    if request.method == 'POST':
        condition_in = request.form.get('condition_in', 'good')
        notes = request.form.get('notes', '')
        waive_fine = bool(request.form.get('waive_fine'))
        pay_now = bool(request.form.get('pay_now'))

        returned_loan, fine, error = LoanService.return_book(
            loan_id, condition_in=condition_in, notes=notes,
            waive_fine=waive_fine, pay_now=pay_now
        )

        if error:
            flash(error, 'danger')
        else:
            if fine > 0 and not waive_fine:
                if pay_now:
                    flash(f'Trả sách và thanh toán phí phạt {fine:,.0f}đ thành công!'.replace(',', '.'), 'success')
                else:
                    flash(f'Đã ghi nhận trả sách. Công nợ phí phạt trả muộn: {fine:,.0f}đ (chưa thanh toán).'.replace(',', '.'), 'warning')
            else:
                flash('Trả sách thành công!', 'success')
            return redirect(url_for('loans.detail', loan_id=loan_id))

    from flask import current_app
    fine_per_day = current_app.config.get('FINE_PER_DAY', 2000)
    estimated_fine = loan.days_overdue * fine_per_day if loan.is_overdue else 0
    return render_template('loans/return.html', loan=loan, estimated_fine=estimated_fine, fine_per_day=fine_per_day)


@loans_bp.route('/<int:loan_id>/pay-fine', methods=['POST'])
@login_required
def pay_fine(loan_id):
    loan, error = LoanService.pay_fine(loan_id)
    if error:
        flash(error, 'danger')
    else:
        flash(f'Đã xác nhận thanh toán phí phạt {loan.fine_amount:,.0f}đ cho phiếu {loan.loan_code}.'.replace(',', '.'), 'success')
    return redirect(url_for('loans.detail', loan_id=loan_id))


@loans_bp.route('/<int:loan_id>/renew', methods=['POST'])
@login_required
def renew(loan_id):
    loan, error = LoanService.renew_loan(loan_id)
    if error:
        flash(error, 'danger')
    else:
        flash(f'Gia hạn thành công! Hạn trả mới: {loan.due_date.strftime("%d/%m/%Y")}', 'success')
    return redirect(url_for('loans.detail', loan_id=loan_id))


@loans_bp.route('/<int:loan_id>/lost', methods=['POST'])
@login_required
def mark_lost(loan_id):
    notes = request.form.get('notes', '')
    loan, error = LoanService.mark_as_lost(loan_id, notes)
    if error:
        flash(error, 'danger')
    else:
        if loan.fine_amount:
            flash(f'Đã ghi nhận mất sách và tạo khoản đền bù {loan.fine_amount:,.0f}đ (100% giá bìa).'.replace(',', '.'), 'warning')
        else:
            flash('Đã ghi nhận mất sách.', 'warning')
    return redirect(url_for('loans.detail', loan_id=loan_id))


@loans_bp.route('/overdue')
@login_required
def overdue():
    overdue_list = ReportService.get_overdue_report()
    return render_template('loans/overdue.html', overdue_list=overdue_list)


@loans_bp.route('/reports')
@login_required
def reports():
    monthly_data = ReportService.get_monthly_loan_chart()
    top_books = ReportService.get_top_books(limit=10)
    top_members = ReportService.get_top_members(limit=10)
    category_dist = ReportService.get_category_distribution()
    faculty_stats = ReportService.get_faculty_loan_stats()
    loan_stats = LoanService.get_statistics()

    return render_template('loans/reports.html',
                           monthly_data=monthly_data,
                           top_books=top_books,
                           top_members=top_members,
                           category_dist=category_dist,
                           faculty_stats=faculty_stats,
                           loan_stats=loan_stats)
