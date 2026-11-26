"""
Loans, Reservations & Reports Web Routes
"""
import csv
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, current_app
from flask_login import login_required, current_user
from app.service_clients import loans_client, reports_client
from app.service_access import service_router
from app.services.loan_service import LoanService as LocalLoanService
from app.services.report_service import ReportService as LocalReportService

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

    return render_template(
        'loans/index.html',
        pagination=pagination,
        loans=pagination.items,
        search=search,
        selected_status=status,
        stats=stats,
    )


@loans_bp.route('/export')
@login_required
def export_loans():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    pagination = LoanService.get_all_loans(page=1, per_page=60, search=search, status=status)
    buf = io.StringIO()
    buf.write('\ufeff')
    writer = csv.writer(buf)
    writer.writerow(['Mã phiếu', 'MSSV / Mã CB', 'Độc giả', 'Khoa', 'ISBN', 'Tài liệu', 'Ngày mượn', 'Hạn trả', 'Ngày trả', 'Trạng thái', 'Phí (VNĐ)', 'Thanh toán'])
    for l in pagination.items:
        writer.writerow([
            l.loan_code,
            l.member.student_id if l.member else '',
            l.member.full_name if l.member else '',
            l.member.faculty if l.member else '',
            l.book.isbn if l.book else '',
            l.book.title if l.book else '',
            str(l.loan_date or ''),
            str(l.due_date or ''),
            str(l.return_date or ''),
            l.status,
            int(l.fine_amount or 0),
            'Đã thu' if l.fine_paid else ('Chưa thu' if (l.fine_amount or 0) > 0 else '—'),
        ])
    return Response(
        buf.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="so-luu-thong-thu-vien.csv"'},
    )


@loans_bp.route('/reservations')
@login_required
def reservations():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    pagination = LoanService.get_reservations(page=page, per_page=20, status=status, search=search)
    stats = LoanService.get_statistics()
    return render_template(
        'loans/reservations.html',
        pagination=pagination,
        reservations=pagination.items,
        selected_status=status,
        search=search,
        stats=stats,
    )


@loans_bp.route('/reservations/create', methods=['POST'])
@login_required
def create_reservation():
    book_id = request.form.get('book_id', type=int)
    member_id = request.form.get('member_id', type=int)
    notes = request.form.get('notes', '')
    if not book_id or not member_id:
        flash('Vui lòng chọn độc giả và tài liệu cần đặt giữ chỗ.', 'danger')
        return redirect(url_for('loans.reservations'))

    res, error = LoanService.create_reservation(book_id=book_id, member_id=member_id, notes=notes)
    if error:
        flash(error, 'danger')
    else:
        flash(f'Đã tạo phiếu đặt chỗ {res.reservation_code}.', 'success')
    return redirect(url_for('loans.reservations'))


@loans_bp.route('/reservations/<int:reservation_id>/fulfill', methods=['POST'])
@login_required
def fulfill_reservation(reservation_id):
    loan, error = LoanService.fulfill_reservation(reservation_id, current_user.id)
    if error:
        flash(error, 'danger')
        return redirect(url_for('loans.reservations'))
    flash(f'Đã bàn giao sách và tạo phiếu mượn {loan.loan_code}.', 'success')
    return redirect(url_for('loans.detail', loan_id=loan.id))


@loans_bp.route('/reservations/<int:reservation_id>/cancel', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    res, error = LoanService.cancel_reservation(reservation_id)
    if error:
        flash(error, 'danger')
    else:
        flash(f'Đã hủy phiếu đặt chỗ {res.reservation_code}.', 'info')
    next_url = request.form.get('next')
    if next_url:
        return redirect(next_url)
    return redirect(url_for('loans.reservations'))


@loans_bp.route('/<int:loan_id>')
@login_required
def detail(loan_id):
    loan = LoanService.get_loan_by_id(loan_id)
    fine_per_day = current_app.config.get('FINE_PER_DAY', 2000)
    return render_template('loans/detail.html', loan=loan, fine_per_day=fine_per_day)


@loans_bp.route('/<int:loan_id>/print')
@login_required
def print_slip(loan_id):
    loan = LoanService.get_loan_by_id(loan_id)
    return render_template('loans/print_slip.html', loan=loan)


@loans_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        book_id = request.form.get('book_id', type=int)
        member_id = request.form.get('member_id', type=int)
        notes = request.form.get('notes', '')
        condition = request.form.get('condition', 'good')

        if not book_id or not member_id:
            flash('Vui lòng chọn độc giả và tài liệu cần mượn.', 'danger')
            return render_template('loans/create.html')

        loan, error = LoanService.create_loan(
            book_id=book_id,
            member_id=member_id,
            librarian_id=current_user.id,
            loan_duration=None,
            notes=notes,
            condition=condition,
        )

        if error:
            flash(error, 'danger')
            return render_template('loans/create.html', prefill_book_id=book_id, prefill_member_id=member_id)
        else:
            due_str = loan.due_date.strftime('%d/%m/%Y') if hasattr(loan.due_date, 'strftime') else str(loan.due_date)
            flash(f'Đã phát hành phiếu mượn {loan.loan_code} • Hạn hoàn trả: {due_str}.', 'success')
            return redirect(url_for('loans.detail', loan_id=loan.id))

    return render_template('loans/create.html', prefill_book_id=None, prefill_member_id=None)


@loans_bp.route('/<int:loan_id>/return', methods=['GET', 'POST'])
@login_required
def return_book(loan_id):
    loan = LoanService.get_loan_by_id(loan_id)

    if request.method == 'POST':
        condition_in = request.form.get('condition_in', 'good')
        notes = request.form.get('notes', '')
        fee_action = request.form.get('fee_action', 'pay_now')
        waive_fine = fee_action == 'waive'
        pay_now = fee_action == 'pay_now'

        returned_loan, fine, error = LoanService.return_book(
            loan_id,
            condition_in=condition_in,
            notes=notes,
            waive_fine=waive_fine,
            pay_now=pay_now,
        )

        if error:
            flash(error, 'danger')
        else:
            if fine > 0 and not waive_fine:
                if pay_now:
                    flash(f'Đã tiếp nhận tài liệu và thu {fine:,.0f}₫ phí lưu thông.'.replace(',', '.'), 'success')
                else:
                    flash(f'Đã tiếp nhận tài liệu. Ghi nhận công nợ {fine:,.0f}₫ chưa thanh toán.'.replace(',', '.'), 'warning')
            else:
                flash('Đã tiếp nhận hoàn trả tài liệu vào kho.', 'success')
            return redirect(url_for('loans.detail', loan_id=loan_id))

    fine_per_day = current_app.config.get('FINE_PER_DAY', 2000)
    damage_ratio = current_app.config.get('DAMAGE_FINE_RATIO', 0.30)
    min_damage_fine = current_app.config.get('MIN_DAMAGE_FINE', 20000)
    estimated_fine = loan.days_overdue * fine_per_day if loan.is_overdue else 0
    cover_price = float(loan.book.price or 0) if loan.book else 0
    damage_fee = max(min_damage_fine, round((cover_price * damage_ratio) / 1000) * 1000) if cover_price > 0 else min_damage_fine

    return render_template(
        'loans/return.html',
        loan=loan,
        estimated_fine=estimated_fine,
        fine_per_day=fine_per_day,
        damage_fee=damage_fee,
    )


@loans_bp.route('/<int:loan_id>/pay-fine', methods=['POST'])
@login_required
def pay_fine(loan_id):
    loan, error = LoanService.pay_fine(loan_id)
    if error:
        flash(error, 'danger')
    else:
        flash(f'Đã gạch nợ khoản phí {loan.fine_amount:,.0f}₫ của phiếu {loan.loan_code}.'.replace(',', '.'), 'success')
    return redirect(url_for('loans.detail', loan_id=loan_id))


@loans_bp.route('/<int:loan_id>/renew', methods=['POST'])
@login_required
def renew(loan_id):
    loan, error = LoanService.renew_loan(loan_id)
    if error:
        flash(error, 'danger')
    else:
        due_str = loan.due_date.strftime('%d/%m/%Y') if hasattr(loan.due_date, 'strftime') else str(loan.due_date)
        flash(f'Đã gia hạn phiếu {loan.loan_code} đến ngày {due_str}.', 'success')
    return redirect(url_for('loans.detail', loan_id=loan_id))


@loans_bp.route('/<int:loan_id>/lost', methods=['POST'])
@login_required
def mark_lost(loan_id):
    notes = request.form.get('notes', '')
    pay_now = bool(request.form.get('pay_now'))
    loan, error = LoanService.mark_as_lost(loan_id, notes, pay_now=pay_now)
    if error:
        flash(error, 'danger')
    else:
        flash(f'Đã ghi nhận báo mất và hạch toán bồi thường {loan.fine_amount:,.0f}₫.'.replace(',', '.'), 'warning')
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

    return render_template(
        'loans/reports.html',
        monthly_data=monthly_data,
        top_books=top_books,
        top_members=top_members,
        category_dist=category_dist,
        faculty_stats=faculty_stats,
        loan_stats=loan_stats,
    )
