"""
Loan Service - SOA Service Layer
Handles circulation (borrowing, returning, renewals), reservation hold queues,
overdue/damage/loss fees, and debt settlement.
"""
from datetime import datetime, date, timedelta
from flask import current_app
from sqlalchemy import or_, func
from app.extensions import db
from app.models.loan import Loan
from app.models.book import Book
from app.models.member import Member
from app.models.reservation import Reservation


class LoanService:
    """Service responsible for circulation, holds/reservations, and fine accounting."""

    @staticmethod
    def _generate_loan_code():
        now = datetime.now()
        last = Loan.query.order_by(Loan.id.desc()).first()
        seq = (last.id + 1) if last else 1
        code = f"PM{now.strftime('%y%m')}{seq:04d}"
        while Loan.query.filter_by(loan_code=code).first():
            seq += 1
            code = f"PM{now.strftime('%y%m')}{seq:04d}"
        return code

    @staticmethod
    def _generate_reservation_code():
        now = datetime.now()
        last = Reservation.query.order_by(Reservation.id.desc()).first()
        seq = (last.id + 1) if last else 1
        code = f"DC{now.strftime('%y%m')}{seq:04d}"
        while Reservation.query.filter_by(reservation_code=code).first():
            seq += 1
            code = f"DC{now.strftime('%y%m')}{seq:04d}"
        return code

    @staticmethod
    def _recalculate_member_unpaid_fine(member):
        if not member:
            return
        unpaid = db.session.query(func.sum(Loan.fine_amount)).filter(
            Loan.member_id == member.id,
            Loan.fine_paid == False,
            Loan.fine_amount > 0,
        ).scalar() or 0
        member.total_fine = float(unpaid)

    @staticmethod
    def expire_stale_reservations():
        """Expire 'ready' holds past expires_at and pass copy to next waiter or shelf."""
        today = date.today()
        stale = Reservation.query.filter(
            Reservation.status == 'ready',
            Reservation.expires_at.isnot(None),
            Reservation.expires_at < today,
        ).all()
        if not stale:
            return 0
        hold_days = current_app.config.get('RESERVATION_HOLD_DAYS', 3)
        for res in stale:
            res.status = 'expired'
            res.updated_at = datetime.utcnow()
            book = res.book
            if book:
                next_pending = Reservation.query.filter_by(
                    book_id=book.id, status='pending'
                ).order_by(Reservation.created_at.asc()).first()
                if next_pending:
                    next_pending.status = 'ready'
                    next_pending.notified_at = datetime.utcnow()
                    next_pending.expires_at = today + timedelta(days=hold_days)
                    next_pending.updated_at = datetime.utcnow()
                else:
                    book.available_copies = min(book.total_copies, (book.available_copies or 0) + 1)
        db.session.commit()
        return len(stale)

    @staticmethod
    def _release_copy_to_queue_or_shelf(book):
        """When a copy becomes available, assign to the first pending reservation or return to shelf."""
        if not book:
            return None
        hold_days = current_app.config.get('RESERVATION_HOLD_DAYS', 3)
        next_pending = Reservation.query.filter_by(
            book_id=book.id, status='pending'
        ).order_by(Reservation.created_at.asc()).first()
        if next_pending:
            next_pending.status = 'ready'
            next_pending.notified_at = datetime.utcnow()
            next_pending.expires_at = date.today() + timedelta(days=hold_days)
            next_pending.updated_at = datetime.utcnow()
            return next_pending
        book.available_copies = min(book.total_copies, (book.available_copies or 0) + 1)
        return None

    @staticmethod
    def get_all_loans(page=1, per_page=20, search=None, status=None,
                      member_id=None, book_id=None, sort_by='loan_date', order='desc'):
        query = Loan.query

        if search:
            s = f'%{search.strip()}%'
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
                query = query.filter(Loan.status == status)

        if member_id:
            query = query.filter(Loan.member_id == member_id)

        if book_id:
            query = query.filter(Loan.book_id == book_id)

        allowed_sorts = {
            'loan_date': Loan.loan_date,
            'due_date': Loan.due_date,
            'return_date': Loan.return_date,
            'created_at': Loan.created_at,
            'fine_amount': Loan.fine_amount,
        }
        sort_col = allowed_sorts.get(sort_by, Loan.loan_date)
        if order == 'desc':
            sort_col = sort_col.desc()
        query = query.order_by(sort_col, Loan.id.desc())

        return query.paginate(page=max(1, page), per_page=min(max(1, per_page), 60), error_out=False)

    @staticmethod
    def get_loan_by_id(loan_id):
        return db.get_or_404(Loan, loan_id)

    @staticmethod
    def _validate_reader_for_circulation(member):
        if not member:
            return "Độc giả không tồn tại."
        if member.status == 'graduated':
            return f"Độc giả '{member.full_name}' đã hoàn tất thủ tục ra trường, thẻ không còn hiệu lực mượn."
        if member.status == 'suspended':
            return f"Thẻ thư viện của '{member.full_name}' đang bị tạm khóa."
        if member.status != 'active':
            return f"Thẻ thư viện của '{member.full_name}' hiện không hoạt động."
        if not member.student_id:
            return f"Hồ sơ của '{member.full_name}' chưa có Mã số sinh viên / Mã cán bộ hợp lệ."
        if not member.is_membership_valid:
            return f"Thẻ thư viện của '{member.full_name}' đã hết hạn ngày {member.membership_end.strftime('%d/%m/%Y')}."
        if member.overdue_loans_count > 0:
            return (
                f"Độc giả '{member.full_name}' đang giữ {member.overdue_loans_count} tài liệu quá hạn chưa trả. "
                f"Vui lòng hoàn trả tài liệu quá hạn trước."
            )
        if member.unpaid_fine > 0:
            fine_str = f"{int(member.unpaid_fine):,}₫".replace(',', '.')
            return (
                f"Độc giả '{member.full_name}' còn khoản phí chưa thanh toán ({fine_str}). "
                f"Vui lòng tất toán công nợ trước khi giao dịch."
            )
        return None

    @staticmethod
    def create_loan(book_id, member_id, librarian_id, loan_duration=None,
                    notes=None, condition='good', reservation_id=None):
        LoanService.expire_stale_reservations()

        book = db.session.get(Book, book_id)
        if not book:
            return None, "Tài liệu không tồn tại trong kho thư viện."
        if book.status != 'available':
            return None, f"Tài liệu '{book.title}' hiện đang tạm ngưng phục vụ."
        if (book.circulation_type or 'borrowable') == 'reference_only':
            return None, f"Tài liệu '{book.title}' thuộc diện Chỉ đọc tại thư viện, không cho mượn mang về."

        member = db.session.get(Member, member_id)
        reader_err = LoanService._validate_reader_for_circulation(member)
        if reader_err:
            return None, reader_err

        max_loans = member.max_loans_allowed
        if member.active_loans_count >= max_loans:
            return None, f"Độc giả '{member.full_name}' đã đạt hạn mức mượn tối đa ({max_loans} cuốn)."

        existing = Loan.query.filter_by(
            book_id=book_id, member_id=member_id, status='borrowed'
        ).first()
        if existing:
            return None, f"Độc giả đang mượn tài liệu này (phiếu {existing.loan_code})."

        # Check if this reader has a matching active reservation
        matched_res = None
        if reservation_id:
            matched_res = db.session.get(Reservation, reservation_id)
            if not matched_res or matched_res.member_id != member_id or matched_res.book_id != book_id:
                return None, "Phiếu đặt giữ chỗ không khớp với độc giả hoặc tài liệu."
            if matched_res.status not in ('ready', 'pending'):
                return None, "Phiếu đặt giữ chỗ này không còn hiệu lực."
        else:
            matched_res = Reservation.query.filter(
                Reservation.book_id == book_id,
                Reservation.member_id == member_id,
                Reservation.status.in_(['ready', 'pending'])
            ).order_by(Reservation.created_at.asc()).first()

        consuming_held_copy = bool(matched_res and matched_res.status == 'ready')

        if not consuming_held_copy and (book.available_copies or 0) <= 0:
            return None, f"Tài liệu '{book.title}' hiện đã hết bản sao sẵn có trên kệ."

        duration = int(loan_duration) if loan_duration else member.loan_duration_days
        duration = min(max(1, duration), 60)
        loan_date = date.today()
        due_date = loan_date + timedelta(days=duration)
        if member.membership_end and due_date > member.membership_end:
            due_date = max(loan_date + timedelta(days=1), member.membership_end)

        loan = Loan(
            loan_code=LoanService._generate_loan_code(),
            book_id=book_id,
            member_id=member_id,
            librarian_id=librarian_id,
            loan_date=loan_date,
            due_date=due_date,
            status='borrowed',
            notes=(notes or '').strip() or None,
            condition_out=condition if condition in ('good', 'fair', 'poor') else 'good',
        )

        if not consuming_held_copy:
            book.available_copies -= 1

        db.session.add(loan)
        db.session.flush()

        if matched_res:
            matched_res.status = 'fulfilled'
            matched_res.fulfilled_loan_id = loan.id
            matched_res.updated_at = datetime.utcnow()

        db.session.commit()
        return loan, None

    @staticmethod
    def return_book(loan_id, condition_in='good', notes=None, waive_fine=False, pay_now=False):
        loan = db.get_or_404(Loan, loan_id)
        if loan.status != 'borrowed':
            return None, 0, f"Phiếu mượn không ở trạng thái đang mượn (hiện tại: {loan.status})."

        if condition_in == 'lost':
            lost_loan, err = LoanService.mark_as_lost(loan_id, notes=notes, pay_now=pay_now)
            if err:
                return None, 0, err
            return lost_loan, lost_loan.fine_amount, None

        if waive_fine:
            pay_now = False

        return_date = date.today()
        fine_per_day = current_app.config.get('FINE_PER_DAY', 2000)
        damage_ratio = current_app.config.get('DAMAGE_FINE_RATIO', 0.30)
        min_damage_fine = current_app.config.get('MIN_DAMAGE_FINE', 20000)

        overdue_fine = 0
        if return_date > loan.due_date:
            overdue_fine = (return_date - loan.due_date).days * fine_per_day

        damage_fine = 0
        if condition_in == 'damaged':
            cover_price = float(loan.book.price or 0) if loan.book else 0
            computed_damage = round((cover_price * damage_ratio) / 1000) * 1000 if cover_price > 0 else min_damage_fine
            damage_fine = max(min_damage_fine, computed_damage)

        raw_fine = overdue_fine + damage_fine
        final_fine = 0 if waive_fine else raw_fine

        reason = None
        if final_fine > 0:
            if overdue_fine > 0 and damage_fine > 0:
                reason = 'overdue_damaged'
            elif damage_fine > 0:
                reason = 'damaged'
            else:
                reason = 'overdue'

        loan.return_date = return_date
        loan.status = 'returned'
        loan.condition_in = condition_in if condition_in in ('good', 'fair', 'poor', 'damaged') else 'good'
        loan.fine_amount = final_fine
        loan.fine_reason = reason
        loan.fine_paid = waive_fine or (final_fine == 0) or bool(pay_now)
        if loan.fine_paid and final_fine > 0:
            loan.fine_paid_at = datetime.utcnow()
        loan.updated_at = datetime.utcnow()

        if notes:
            loan.notes = ((loan.notes or '') + f'\n[Trả sách] {notes.strip()}').strip()

        LoanService._release_copy_to_queue_or_shelf(loan.book)

        db.session.flush()
        LoanService._recalculate_member_unpaid_fine(loan.member)
        db.session.commit()
        return loan, final_fine, None

    @staticmethod
    def pay_fine(loan_id):
        loan = db.get_or_404(Loan, loan_id)
        if not loan.fine_amount or loan.fine_amount <= 0:
            return None, "Phiếu mượn này không có khoản phạt nào cần đóng."
        if loan.fine_paid:
            return None, "Khoản phạt của phiếu này đã được thanh toán."

        loan.fine_paid = True
        loan.fine_paid_at = datetime.utcnow()
        loan.updated_at = datetime.utcnow()
        db.session.flush()
        LoanService._recalculate_member_unpaid_fine(loan.member)
        db.session.commit()
        return loan, None

    @staticmethod
    def renew_loan(loan_id, extension_days=None):
        loan = db.get_or_404(Loan, loan_id)

        if loan.status != 'borrowed':
            return None, "Chỉ có thể gia hạn phiếu đang trong thời gian mượn."
        max_renewals = current_app.config.get('MAX_RENEWALS', 2)
        if loan.renewal_count >= max_renewals:
            return None, f"Phiếu mượn đã đạt giới hạn gia hạn tối đa ({max_renewals} lần)."
        if loan.is_overdue:
            return None, "Tài liệu đã quá hạn trả, không thể gia hạn. Vui lòng hoàn trả tại quầy."

        if loan.member:
            if loan.member.status != 'active' or not loan.member.is_membership_valid:
                return None, "Thẻ thư viện của độc giả đã hết hạn hoặc bị tạm khóa, không thể gia hạn."
            if loan.member.overdue_loans_count > 0:
                return None, "Độc giả đang giữ tài liệu khác quá hạn, không thể gia hạn."
            if loan.member.unpaid_fine > 0:
                return None, "Độc giả đang có công nợ phí chưa thanh toán, không thể gia hạn."

        pending_holds = Reservation.query.filter_by(book_id=loan.book_id, status='pending').count()
        if pending_holds > 0:
            return None, (
                f"Tài liệu này đang có {pending_holds} độc giả khác đặt chờ mượn, "
                f"không thể gia hạn để đảm bảo luân chuyển."
            )

        rules = current_app.config.get('BORROW_RULES', {})
        mtype = loan.member.member_type if loan.member else 'student'
        default_ext = rules.get(mtype, {}).get('renew_days', 7)
        days = int(extension_days) if extension_days else default_ext
        days = min(max(1, days), 30)

        new_due = loan.due_date + timedelta(days=days)
        if loan.member and loan.member.membership_end and new_due > loan.member.membership_end:
            new_due = max(loan.due_date, loan.member.membership_end)
            if new_due <= loan.due_date:
                return None, "Hạn thẻ độc giả không đủ thời gian để gia hạn thêm."

        loan.due_date = new_due
        loan.renewal_count += 1
        loan.updated_at = datetime.utcnow()

        db.session.commit()
        return loan, None

    @staticmethod
    def mark_as_lost(loan_id, notes=None, pay_now=False):
        loan = db.get_or_404(Loan, loan_id)
        if loan.status != 'borrowed':
            return None, "Phiếu lưu thông không ở trạng thái đang mượn."

        fine_per_day = current_app.config.get('FINE_PER_DAY', 2000)
        default_lost_fee = current_app.config.get('DEFAULT_LOST_FEE', 50000)
        today = date.today()

        overdue_fine = max(0, (today - loan.due_date).days * fine_per_day) if loan.due_date and today > loan.due_date else 0
        cover_price = float(loan.book.price or 0) if loan.book else 0
        replacement_fee = cover_price if cover_price > 0 else default_lost_fee
        total_compensation = replacement_fee + overdue_fine

        loan.status = 'lost'
        loan.condition_in = 'lost'
        loan.return_date = today
        loan.fine_amount = total_compensation
        loan.fine_reason = 'lost'
        loan.fine_paid = bool(pay_now) or total_compensation <= 0
        if loan.fine_paid and total_compensation > 0:
            loan.fine_paid_at = datetime.utcnow()
        loan.updated_at = datetime.utcnow()

        summary_note = f"[Báo mất — Đền bù {int(total_compensation):,}₫]".replace(',', '.')
        if notes:
            summary_note += f" {notes.strip()}"
        loan.notes = ((loan.notes or '') + ('\n' if loan.notes else '') + summary_note).strip()

        if loan.book:
            loan.book.total_copies = max(0, (loan.book.total_copies or 1) - 1)
            loan.book.available_copies = min(loan.book.available_copies or 0, loan.book.total_copies)
            if loan.book.total_copies == 0:
                loan.book.status = 'unavailable'

        db.session.flush()
        LoanService._recalculate_member_unpaid_fine(loan.member)
        db.session.commit()
        return loan, None

    # ---- Reservations / Holds ----

    @staticmethod
    def get_reservations(page=1, per_page=20, status=None, search=None, member_id=None, book_id=None):
        LoanService.expire_stale_reservations()
        query = Reservation.query

        if search:
            s = f'%{search.strip()}%'
            query = query.join(Member).join(Book).filter(
                or_(
                    Reservation.reservation_code.ilike(s),
                    Member.full_name.ilike(s),
                    Member.student_id.ilike(s),
                    Member.member_code.ilike(s),
                    Book.title.ilike(s),
                    Book.isbn.ilike(s),
                )
            )

        if status:
            if status == 'active':
                query = query.filter(Reservation.status.in_(['pending', 'ready']))
            else:
                query = query.filter(Reservation.status == status)

        if member_id:
            query = query.filter(Reservation.member_id == member_id)
        if book_id:
            query = query.filter(Reservation.book_id == book_id)

        query = query.order_by(
            Reservation.status.desc(),
            Reservation.created_at.asc()
        )
        return query.paginate(page=max(1, page), per_page=min(max(1, per_page), 60), error_out=False)

    @staticmethod
    def create_reservation(book_id, member_id, notes=None):
        LoanService.expire_stale_reservations()

        book = db.session.get(Book, book_id)
        if not book:
            return None, "Tài liệu không tồn tại."
        if book.status != 'available':
            return None, f"Tài liệu '{book.title}' hiện đang tạm ngưng phục vụ."
        if (book.circulation_type or 'borrowable') == 'reference_only':
            return None, f"Tài liệu '{book.title}' chỉ phục vụ đọc tại thư viện, không nhận đặt trước mang về."

        member = db.session.get(Member, member_id)
        reader_err = LoanService._validate_reader_for_circulation(member)
        if reader_err:
            return None, reader_err

        max_res = current_app.config.get('MAX_RESERVATIONS_PER_MEMBER', 3)
        active_res_count = Reservation.query.filter(
            Reservation.member_id == member_id,
            Reservation.status.in_(['pending', 'ready'])
        ).count()
        if active_res_count >= max_res:
            return None, f"Mỗi độc giả chỉ được đặt giữ chỗ tối đa {max_res} tài liệu cùng lúc."

        if Loan.query.filter_by(book_id=book_id, member_id=member_id, status='borrowed').first():
            return None, "Độc giả hiện đang mượn tài liệu này."

        dup_res = Reservation.query.filter(
            Reservation.book_id == book_id,
            Reservation.member_id == member_id,
            Reservation.status.in_(['pending', 'ready'])
        ).first()
        if dup_res:
            return None, f"Độc giả đã có phiếu đặt giữ chỗ ({dup_res.reservation_code}) cho tài liệu này."

        hold_days = current_app.config.get('RESERVATION_HOLD_DAYS', 3)
        if (book.available_copies or 0) > 0:
            res_status = 'ready'
            expires_at = date.today() + timedelta(days=hold_days)
            notified_at = datetime.utcnow()
            book.available_copies -= 1
        else:
            res_status = 'pending'
            expires_at = None
            notified_at = None

        res = Reservation(
            reservation_code=LoanService._generate_reservation_code(),
            book_id=book_id,
            member_id=member_id,
            status=res_status,
            expires_at=expires_at,
            notified_at=notified_at,
            notes=(notes or '').strip() or None,
        )
        db.session.add(res)
        db.session.commit()
        return res, None

    @staticmethod
    def cancel_reservation(reservation_id):
        res = db.get_or_404(Reservation, reservation_id)
        if res.status not in ('pending', 'ready'):
            return None, "Phiếu đặt chỗ không còn ở trạng thái chờ xử lý."

        was_ready = res.status == 'ready'
        res.status = 'cancelled'
        res.updated_at = datetime.utcnow()

        if was_ready and res.book:
            LoanService._release_copy_to_queue_or_shelf(res.book)

        db.session.commit()
        return res, None

    @staticmethod
    def fulfill_reservation(reservation_id, librarian_id):
        res = db.get_or_404(Reservation, reservation_id)
        if res.status not in ('ready', 'pending'):
            return None, "Phiếu đặt chỗ này đã được xử lý hoặc đã hết hạn."
        if res.status == 'pending' and (not res.book or (res.book.available_copies or 0) <= 0):
            return None, "Tài liệu hiện chưa có bản sao trống để bàn giao cho phiếu chờ này."
        return LoanService.create_loan(
            book_id=res.book_id,
            member_id=res.member_id,
            librarian_id=librarian_id,
            notes=f"Bàn giao từ phiếu đặt giữ chỗ {res.reservation_code}",
            condition='good',
            reservation_id=res.id,
        )

    # ---- Queries & Stats ----

    @staticmethod
    def get_overdue_loans():
        return Loan.query.filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).order_by(Loan.due_date.asc()).all()

    @staticmethod
    def get_today_due():
        return Loan.query.filter(
            Loan.status == 'borrowed',
            Loan.due_date == date.today()
        ).all()

    @staticmethod
    def get_statistics():
        LoanService.expire_stale_reservations()
        total = Loan.query.count()
        borrowed = Loan.query.filter_by(status='borrowed').count()
        returned = Loan.query.filter_by(status='returned').count()
        lost = Loan.query.filter_by(status='lost').count()
        overdue = Loan.query.filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).count()
        active_reservations = Reservation.query.filter(
            Reservation.status.in_(['pending', 'ready'])
        ).count()
        ready_reservations = Reservation.query.filter_by(status='ready').count()

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
            'active_reservations': active_reservations,
            'ready_reservations': ready_reservations,
            'total_fine': float(total_fine),
            'paid_fine': float(paid_fine),
            'unpaid_fine': float(unpaid_fine),
        }

    @staticmethod
    def get_monthly_stats(months=12):
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
