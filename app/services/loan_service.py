"""
Loan Service - SOA Service Layer
Handles all business logic for university library borrowing, returning, renewals,
automatic overdue/loss penalties, and fine settlement.
"""
from datetime import datetime, date, timedelta
from sqlalchemy import or_, func
from app.extensions import db
from app.models.loan import Loan
from app.models.book import Book
from app.models.member import Member


class LoanService:
    """
    Service responsible for all circulation (loan/return/fine) operations.
    Enforces university library rules:
    - Free borrowing for valid university readers (Student/Staff ID required)
    - Reference-only materials cannot leave the library
    - Role-based quotas & durations (Student: 5/14d, Postgrad: 7/21d, Lecturer: 10/30d)
    - Borrowing blocked while reader holds overdue books or unpaid fines
    - Automatic late fee calculation (2.000đ/day) and 100% cover-price compensation for lost books
    """

    @staticmethod
    def _generate_loan_code():
        """Generate unique loan code like PM26110001"""
        now = datetime.now()
        last = Loan.query.order_by(Loan.id.desc()).first()
        seq = (last.id + 1) if last else 1
        return f"PM{now.strftime('%y%m')}{seq:04d}"

    @staticmethod
    def _recalculate_member_unpaid_fine(member):
        """Sync Member.total_fine to reflect total unpaid fines accurately."""
        unpaid = db.session.query(func.sum(Loan.fine_amount)).filter(
            Loan.member_id == member.id,
            Loan.fine_paid == False,
            Loan.fine_amount > 0,
        ).scalar() or 0
        member.total_fine = float(unpaid)

    @staticmethod
    def get_all_loans(page=1, per_page=20, search=None, status=None,
                      member_id=None, book_id=None, sort_by='loan_date', order='desc'):
        """Get paginated list of loans with filters"""
        query = Loan.query

        if search:
            s = f'%{search}%'
            query = query.join(Member).join(Book).filter(
                or_(
                    Loan.loan_code.ilike(s),
                    Member.full_name.ilike(s),
                    Member.member_code.ilike(s),
                    Member.student_id.ilike(s),
                    Book.title.ilike(s),
                    Book.isbn.ilike(s),
                )
            )

        if status:
            if status == 'overdue':
                query = query.filter(Loan.status == 'borrowed', Loan.due_date < date.today())
            elif status == 'due_today':
                query = query.filter(Loan.status == 'borrowed', Loan.due_date == date.today())
            elif status == 'unpaid_fine':
                query = query.filter(Loan.fine_amount > 0, Loan.fine_paid == False)
            else:
                query = query.filter_by(status=status)

        if member_id:
            query = query.filter_by(member_id=member_id)

        if book_id:
            query = query.filter_by(book_id=book_id)

        sort_col = getattr(Loan, sort_by, Loan.loan_date)
        if order == 'desc':
            sort_col = sort_col.desc()
        query = query.order_by(sort_col)

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_loan_by_id(loan_id):
        return Loan.query.get_or_404(loan_id)

    @staticmethod
    def create_loan(book_id, member_id, librarian_id, loan_duration=None, notes=None, condition='good'):
        """
        Create a new free loan transaction under university library rules.
        Returns: (Loan, error_message)
        """
        book = Book.query.get(book_id)
        if not book:
            return None, "Tài liệu không tồn tại trong kho thư viện."
        if book.status != 'available':
            return None, f"Tài liệu '{book.title}' hiện đang tạm ngưng lưu thông."
        if (book.circulation_type or 'borrowable') == 'reference_only':
            return None, (
                f"Tài liệu '{book.title}' thuộc diện CHỈ ĐỌC TẠI CHỖ "
                f"(luận văn / tài liệu quý hiếm), không được phép mượn về nhà."
            )
        if book.available_copies <= 0:
            return None, f"Tài liệu '{book.title}' hiện đã hết bản sao trên kệ."

        member = Member.query.get(member_id)
        if not member:
            return None, "Độc giả không tồn tại."
        if member.status == 'graduated':
            return None, f"Độc giả '{member.full_name}' đã hoàn tất thủ tục ra trường, thẻ thư viện không còn hiệu lực mượn."
        if member.status == 'suspended':
            return None, f"Thẻ thư viện của '{member.full_name}' đang bị tạm khóa do vi phạm quy định."
        if member.status != 'active':
            return None, f"Thẻ thư viện của '{member.full_name}' không còn hoạt động (trạng thái: {member.status})."
        if not member.student_id:
            return None, f"Độc giả '{member.full_name}' chưa cập nhật Mã số sinh viên / Mã cán bộ hợp lệ."
        if not member.is_membership_valid:
            return None, f"Thẻ thư viện của '{member.full_name}' đã hết hạn ngày {member.membership_end.strftime('%d/%m/%Y')}."

        # Rule: block borrowing if reader has overdue books
        if member.overdue_loans_count > 0:
            return None, (
                f"Chặn mượn mới: Độc giả '{member.full_name}' đang có {member.overdue_loans_count} cuốn sách quá hạn chưa trả. "
                f"Vui lòng hoàn trả sách quá hạn trước khi mượn thêm."
            )

        # Rule: block borrowing if reader has unpaid fines
        if member.unpaid_fine > 0:
            fine_str = f"{int(member.unpaid_fine):,}đ".replace(',', '.')
            return None, (
                f"Chặn mượn mới: Độc giả '{member.full_name}' đang nợ phí phạt/bồi thường {fine_str} chưa thanh toán. "
                f"Vui lòng thanh toán công nợ trước khi tạo phiếu mượn."
            )

        # Rule: role-based quota
        max_loans = member.max_loans_allowed
        if member.active_loans_count >= max_loans:
            return None, (
                f"Độc giả '{member.full_name}' đã đạt hạn mức tối đa ({max_loans} cuốn cùng lúc theo đối tượng thẻ)."
            )

        # Rule: cannot borrow two copies of the exact same title concurrently
        existing = Loan.query.filter_by(
            book_id=book_id, member_id=member_id, status='borrowed'
        ).first()
        if existing:
            return None, f"Độc giả đang mượn đầu sách này (mã phiếu: {existing.loan_code})."

        duration = int(loan_duration) if loan_duration else member.loan_duration_days
        loan_date = date.today()
        due_date = loan_date + timedelta(days=duration)

        loan = Loan(
            loan_code=LoanService._generate_loan_code(),
            book_id=book_id,
            member_id=member_id,
            librarian_id=librarian_id,
            loan_date=loan_date,
            due_date=due_date,
            status='borrowed',
            notes=notes,
            condition_out=condition,
        )

        book.available_copies -= 1
        db.session.add(loan)
        db.session.commit()
        return loan, None

    @staticmethod
    def return_book(loan_id, condition_in='good', notes=None, waive_fine=False, pay_now=False):
        """
        Process a book return.
        Automatically computes late fine (FINE_PER_DAY * days_late).
        Returns: (Loan, fine_amount, error_message)
        """
        from flask import current_app
        loan = Loan.query.get_or_404(loan_id)

        if loan.status != 'borrowed':
            return None, 0, f"Phiếu mượn này không ở trạng thái 'đang mượn' (hiện tại: {loan.status})."

        return_date = date.today()
        fine_per_day = current_app.config.get('FINE_PER_DAY', 2000)

        fine = 0
        if return_date > loan.due_date:
            days_late = (return_date - loan.due_date).days
            fine = days_late * fine_per_day

        loan.return_date = return_date
        loan.status = 'returned'
        loan.condition_in = condition_in
        loan.fine_amount = 0 if waive_fine else fine
        loan.fine_reason = 'overdue' if (fine > 0 and not waive_fine) else None
        loan.fine_paid = waive_fine or (fine == 0) or pay_now
        if pay_now and fine > 0 and not waive_fine:
            loan.fine_paid_at = datetime.utcnow()
        loan.updated_at = datetime.utcnow()

        if notes:
            loan.notes = ((loan.notes or '') + f'\n[Trả sách] {notes}').strip()

        book = loan.book
        if condition_in != 'lost':
            book.available_copies = min(book.total_copies, book.available_copies + 1)

        db.session.flush()
        LoanService._recalculate_member_unpaid_fine(loan.member)
        db.session.commit()
        return loan, (0 if waive_fine else fine), None

    @staticmethod
    def pay_fine(loan_id):
        """Record payment of an unpaid overdue/lost fine for a loan."""
        loan = Loan.query.get_or_404(loan_id)
        if not loan.fine_amount or loan.fine_amount <= 0:
            return None, "Phiếu mượn này không có khoản phí phạt nào cần thanh toán."
        if loan.fine_paid:
            return None, "Khoản phí phạt của phiếu mượn này đã được thanh toán trước đó."

        loan.fine_paid = True
        loan.fine_paid_at = datetime.utcnow()
        loan.updated_at = datetime.utcnow()
        db.session.flush()
        LoanService._recalculate_member_unpaid_fine(loan.member)
        db.session.commit()
        return loan, None

    @staticmethod
    def renew_loan(loan_id, extension_days=None):
        """
        Renew an active loan.
        Rules: max 2 renewals, not overdue, reader has no unpaid fines.
        """
        from flask import current_app
        loan = Loan.query.get_or_404(loan_id)

        if loan.status != 'borrowed':
            return None, "Phiếu mượn không ở trạng thái đang mượn."
        if loan.renewal_count >= 2:
            return None, "Phiếu mượn đã đạt giới hạn gia hạn tối đa (2 lần)."
        if loan.is_overdue:
            return None, "Sách đã quá hạn trả, không được phép gia hạn. Vui lòng trả sách và xử lý phạt trước."
        if loan.member and loan.member.unpaid_fine > 0:
            return None, "Độc giả đang có khoản phạt chưa thanh toán, không thể gia hạn."

        rules = current_app.config.get('BORROW_RULES', {})
        mtype = loan.member.member_type if loan.member else 'student'
        default_ext = rules.get(mtype, {}).get('renew_days', 7)
        days = int(extension_days) if extension_days else default_ext

        loan.due_date = loan.due_date + timedelta(days=days)
        loan.renewal_count += 1
        loan.updated_at = datetime.utcnow()

        db.session.commit()
        return loan, None

    @staticmethod
    def mark_as_lost(loan_id, notes=None):
        """
        Mark a borrowed book as lost.
        Charges 100% cover price as compensation (if price > 0) and reduces total_copies by 1.
        """
        loan = Loan.query.get_or_404(loan_id)
        if loan.status != 'borrowed':
            return None, "Phiếu mượn không ở trạng thái đang mượn."

        compensation = float(loan.book.price or 0) if loan.book else 0
        loan.status = 'lost'
        loan.return_date = date.today()
        loan.fine_amount = compensation
        loan.fine_reason = 'lost' if compensation > 0 else None
        loan.fine_paid = compensation <= 0
        loan.updated_at = datetime.utcnow()
        if notes:
            loan.notes = ((loan.notes or '') + f'\n[Báo mất - Đền bù {int(compensation):,}đ] {notes}'.replace(',', '.')).strip()

        if loan.book:
            loan.book.total_copies = max(0, (loan.book.total_copies or 1) - 1)
            if loan.book.total_copies == 0:
                loan.book.status = 'unavailable'

        db.session.flush()
        if loan.member:
            LoanService._recalculate_member_unpaid_fine(loan.member)
        db.session.commit()
        return loan, None

    @staticmethod
    def get_overdue_loans():
        """Get all overdue loans"""
        return Loan.query.filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).order_by(Loan.due_date).all()

    @staticmethod
    def get_today_due():
        """Get loans due today"""
        return Loan.query.filter(
            Loan.status == 'borrowed',
            Loan.due_date == date.today()
        ).all()

    @staticmethod
    def get_statistics():
        """Get loan statistics"""
        total = Loan.query.count()
        borrowed = Loan.query.filter_by(status='borrowed').count()
        returned = Loan.query.filter_by(status='returned').count()
        lost = Loan.query.filter_by(status='lost').count()
        overdue = Loan.query.filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).count()

        total_fine = db.session.query(func.sum(Loan.fine_amount)).scalar() or 0
        unpaid_fine = db.session.query(func.sum(Loan.fine_amount)).filter(
            Loan.fine_paid == False, Loan.fine_amount > 0
        ).scalar() or 0
        paid_fine = float(total_fine) - float(unpaid_fine)

        return {
            'total': total,
            'borrowed': borrowed,
            'returned': returned,
            'lost': lost,
            'overdue': overdue,
            'total_fine': float(total_fine),
            'paid_fine': float(paid_fine),
            'unpaid_fine': float(unpaid_fine),
        }

    @staticmethod
    def get_monthly_stats(months=12):
        """Get monthly loan statistics for chart"""
        from sqlalchemy import extract
        result = []
        today = date.today()

        for i in range(months - 1, -1, -1):
            month = today.month - i
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            target = date(year, month, 1)

            count = Loan.query.filter(
                extract('year', Loan.loan_date) == target.year,
                extract('month', Loan.loan_date) == target.month,
            ).count()

            result.append({
                'month': target.strftime('%m/%Y'),
                'count': count,
            })

        return result
