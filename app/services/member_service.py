"""
Member Service - SOA Service Layer
Handles university readers (students, postgrads, lecturers), card lifecycle,
self-service reader lookup, and graduation library clearance.
"""
import re
from datetime import datetime, date, timedelta
from sqlalchemy import or_, func
from app.extensions import db
from app.models.member import Member
from app.models.loan import Loan
from app.models.reservation import Reservation

CARD_DURATION_MONTHS = {
    'student': 48,
    'postgrad': 24,
    'lecturer': 60,
}

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class MemberService:
    """Service responsible for university reader operations and graduation clearance."""

    @staticmethod
    def _generate_member_code(member_type='student'):
        prefix = {'student': 'SV', 'postgrad': 'HV', 'lecturer': 'GV'}.get(member_type, 'TV')
        year = datetime.now().year % 100
        last = Member.query.order_by(Member.id.desc()).first()
        seq = (last.id + 1) if last else 1
        code = f"{prefix}{year:02d}{seq:04d}"
        while Member.query.filter_by(member_code=code).first():
            seq += 1
            code = f"{prefix}{year:02d}{seq:04d}"
        return code

    @staticmethod
    def _add_months(base_date, months):
        try:
            from dateutil.relativedelta import relativedelta
            return base_date + relativedelta(months=months)
        except ImportError:
            return base_date + timedelta(days=months * 30)

    @staticmethod
    def get_all_members(page=1, per_page=15, search=None, status=None,
                        member_type=None, faculty=None, sort_by='full_name', order='asc'):
        query = Member.query

        if search:
            search_term = f'%{search.strip()}%'
            query = query.filter(
                or_(
                    Member.full_name.ilike(search_term),
                    Member.member_code.ilike(search_term),
                    Member.student_id.ilike(search_term),
                    Member.email.ilike(search_term),
                    Member.phone.ilike(search_term),
                    Member.faculty.ilike(search_term),
                    Member.class_name.ilike(search_term),
                )
            )

        if status:
            query = query.filter_by(status=status)

        if member_type:
            query = query.filter_by(member_type=member_type)

        if faculty:
            query = query.filter_by(faculty=faculty)

        allowed_sorts = {
            'full_name': Member.full_name,
            'created_at': Member.created_at,
            'graduation_year': Member.graduation_year,
            'student_id': Member.student_id,
        }
        sort_col = allowed_sorts.get(sort_by, Member.full_name)
        if order == 'desc':
            sort_col = sort_col.desc()
        query = query.order_by(sort_col, Member.id.desc())

        return query.paginate(page=max(1, page), per_page=min(max(1, per_page), 60), error_out=False)

    @staticmethod
    def get_member_by_id(member_id):
        return db.get_or_404(Member, member_id)

    @staticmethod
    def get_member_by_code(code):
        if not code:
            return None
        clean = code.strip()
        return Member.query.filter(
            or_(func.upper(Member.member_code) == clean.upper(),
                func.upper(Member.student_id) == clean.upper())
        ).first()

    @staticmethod
    def lookup_reader_portal(identifier, email_or_phone):
        """Self-service lookup for students/lecturers on the OPAC portal."""
        ident = (identifier or '').strip()
        verify = (email_or_phone or '').strip().lower()
        if not ident or not verify:
            return None, "Vui lòng nhập Mã số sinh viên / Mã cán bộ và Email (hoặc SĐT) đã đăng ký."

        member = MemberService.get_member_by_code(ident)
        if not member:
            return None, "Không tìm thấy hồ sơ thẻ thư viện khớp với mã định danh vừa nhập."

        email_match = (member.email or '').lower() == verify
        phone_match = bool(member.phone) and member.phone.strip() == verify
        if not (email_match or phone_match):
            return None, "Thông tin xác thực Email / Số điện thoại không khớp với hồ sơ thẻ."

        active_loans = Loan.query.filter_by(member_id=member.id, status='borrowed').order_by(Loan.due_date.asc()).all()
        recent_history = Loan.query.filter(
            Loan.member_id == member.id,
            Loan.status != 'borrowed'
        ).order_by(Loan.return_date.desc(), Loan.id.desc()).limit(10).all()
        reservations = Reservation.query.filter(
            Reservation.member_id == member.id,
            Reservation.status.in_(['pending', 'ready'])
        ).order_by(Reservation.created_at.asc()).all()
        unpaid_loans = Loan.query.filter(
            Loan.member_id == member.id,
            Loan.fine_paid == False,
            Loan.fine_amount > 0
        ).all()

        return {
            'member': member.to_dict(),
            'active_loans': [l.to_dict() for l in active_loans],
            'recent_history': [l.to_dict() for l in recent_history],
            'reservations': [r.to_dict() for r in reservations],
            'unpaid_loans': [l.to_dict() for l in unpaid_loans],
        }, None

    @staticmethod
    def get_faculties():
        rows = db.session.query(Member.faculty).filter(
            Member.faculty.isnot(None), Member.faculty != ''
        ).distinct().order_by(Member.faculty).all()
        return [r[0] for r in rows]

    @staticmethod
    def create_member(data):
        student_id = (data.get('student_id') or '').strip().upper()
        if not student_id:
            return None, "Vui lòng nhập Mã số sinh viên (MSSV) hoặc Mã cán bộ."

        full_name = (data.get('full_name') or '').strip()
        if not full_name:
            return None, "Họ và tên độc giả không được để trống."

        if Member.query.filter(func.upper(Member.student_id) == student_id).first():
            return None, f"Mã định danh '{student_id}' đã được cấp thẻ thư viện."

        email = (data.get('email') or '').strip().lower()
        if not email or not _EMAIL_RE.match(email):
            return None, "Địa chỉ email không hợp lệ."
        if Member.query.filter(func.lower(Member.email) == email).first():
            return None, f"Email '{email}' đã được đăng ký cho độc giả khác."

        faculty = (data.get('faculty') or '').strip()
        if not faculty:
            return None, "Vui lòng nhập Khoa / Viện hoặc Đơn vị công tác."

        member_type = data.get('member_type', 'student')
        if member_type not in ('student', 'postgrad', 'lecturer'):
            member_type = 'student'

        grad_year = None
        if data.get('graduation_year') not in (None, ''):
            try:
                grad_year = int(data['graduation_year'])
                if grad_year < 2000 or grad_year > 2050:
                    return None, "Năm dự kiến tốt nghiệp không hợp lệ."
            except (ValueError, TypeError):
                return None, "Năm dự kiến tốt nghiệp không hợp lệ."
        elif member_type == 'student':
            cohort_str = (data.get('cohort') or '').strip().upper()
            m_cohort = re.match(r'^K(\d{2})$', cohort_str)
            grad_year = (2000 + int(m_cohort.group(1)) + 4) if m_cohort else (date.today().year + 4)
        elif member_type == 'postgrad':
            grad_year = date.today().year + 2

        if member_type == 'lecturer':
            grad_year = None

        months = CARD_DURATION_MONTHS.get(member_type, 48)
        end_date = MemberService._add_months(date.today(), months)

        member = Member(
            member_code=MemberService._generate_member_code(member_type),
            student_id=student_id,
            full_name=full_name,
            email=email,
            phone=(data.get('phone') or '').strip() or None,
            address=(data.get('address') or '').strip() or None,
            id_card=(data.get('id_card') or '').strip() or None,
            gender=data.get('gender') if data.get('gender') in ('male', 'female', 'other') else 'other',
            member_type=member_type,
            faculty=faculty,
            class_name=(data.get('class_name') or '').strip() or None,
            cohort=(data.get('cohort') or '').strip() or None,
            graduation_year=grad_year,
            membership_start=date.today(),
            membership_end=end_date,
            status='active',
            notes=(data.get('notes') or '').strip() or None,
        )

        if data.get('date_of_birth'):
            try:
                member.date_of_birth = datetime.strptime(str(data['date_of_birth']), '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass

        db.session.add(member)
        db.session.commit()
        return member, None

    @staticmethod
    def _release_member_reservations(member_id):
        """Cancel active reservations when a reader graduates or deactivates, releasing held copies."""
        active_res = Reservation.query.filter(
            Reservation.member_id == member_id,
            Reservation.status.in_(['pending', 'ready'])
        ).all()
        for res in active_res:
            was_ready = res.status == 'ready'
            res.status = 'cancelled'
            res.updated_at = datetime.utcnow()
            if was_ready and res.book:
                next_pending = Reservation.query.filter_by(
                    book_id=res.book_id, status='pending'
                ).order_by(Reservation.created_at.asc()).first()
                if next_pending:
                    next_pending.status = 'ready'
                    next_pending.notified_at = datetime.utcnow()
                    next_pending.expires_at = date.today() + timedelta(days=3)
                else:
                    res.book.available_copies = min(res.book.total_copies, (res.book.available_copies or 0) + 1)

    @staticmethod
    def update_member(member_id, data):
        member = db.get_or_404(Member, member_id)

        email = (data.get('email') or member.email).strip().lower()
        if not _EMAIL_RE.match(email):
            return None, "Địa chỉ email không hợp lệ."
        existing = Member.query.filter(func.lower(Member.email) == email).first()
        if existing and existing.id != member_id:
            return None, f"Email '{email}' đã được sử dụng."

        student_id = (data.get('student_id') or member.student_id or '').strip().upper()
        if not student_id:
            return None, "Mã số sinh viên / Mã cán bộ không được để trống."
        existing_sid = Member.query.filter(func.upper(Member.student_id) == student_id).first()
        if existing_sid and existing_sid.id != member_id:
            return None, f"Mã định danh '{student_id}' đã thuộc về độc giả khác."

        target_type = data.get('member_type') if data.get('member_type') in ('student', 'postgrad', 'lecturer') else member.member_type
        new_status = data.get('status', member.status)
        if new_status not in ('active', 'suspended', 'graduated', 'inactive'):
            new_status = member.status

        if new_status == 'graduated' and target_type == 'lecturer':
            return None, "Trạng thái 'Đã tốt nghiệp' chỉ áp dụng cho Sinh viên và Học viên cao học. Với Giảng viên nghỉ công tác, vui lòng chọn 'Ngưng hoạt động'."

        if new_status in ('graduated', 'inactive') and member.status != new_status:
            active_cnt = member.active_loans_count
            unpaid_val = member.unpaid_fine
            if active_cnt > 0 or unpaid_val > 0:
                return None, (
                    f"Không thể đóng thẻ: độc giả đang giữ {active_cnt} tài liệu chưa trả "
                    f"và nợ {int(unpaid_val):,}₫ phí chưa thanh toán."
                ).replace(',', '.')
            if new_status == 'graduated':
                member.clearance_date = date.today()
            MemberService._release_member_reservations(member.id)

        member.student_id = student_id
        full_name = (data.get('full_name') or member.full_name).strip()
        if not full_name:
            return None, "Họ và tên không được để trống."
        member.full_name = full_name
        member.email = email
        if 'phone' in data:
            member.phone = (data.get('phone') or '').strip() or None
        if 'address' in data:
            member.address = (data.get('address') or '').strip() or None
        if 'id_card' in data:
            member.id_card = (data.get('id_card') or '').strip() or None
        if data.get('gender') in ('male', 'female', 'other'):
            member.gender = data.get('gender')
        member.member_type = target_type
        if 'faculty' in data:
            member.faculty = (data.get('faculty') or '').strip() or None
        if 'class_name' in data:
            member.class_name = (data.get('class_name') or '').strip() or None
        if 'cohort' in data:
            member.cohort = (data.get('cohort') or '').strip() or None
        if target_type == 'lecturer':
            member.graduation_year = None
        elif 'graduation_year' in data:
            try:
                member.graduation_year = int(data['graduation_year']) if data['graduation_year'] else None
            except (ValueError, TypeError):
                pass
        member.status = new_status
        if 'notes' in data:
            member.notes = (data.get('notes') or '').strip() or None
        member.updated_at = datetime.utcnow()

        if 'date_of_birth' in data:
            if not data.get('date_of_birth'):
                member.date_of_birth = None
            else:
                try:
                    member.date_of_birth = datetime.strptime(str(data['date_of_birth']), '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass

        if data.get('membership_end'):
            try:
                member.membership_end = datetime.strptime(str(data['membership_end']), '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass

        db.session.commit()
        return member, None

    @staticmethod
    def renew_card(member_id, months=12):
        member = db.get_or_404(Member, member_id)
        if member.status == 'graduated':
            return None, "Thẻ đã thanh lý ra trường, không thể gia hạn."
        base = max(date.today(), member.membership_end) if member.membership_end else date.today()
        member.membership_end = MemberService._add_months(base, max(1, int(months or 12)))
        if member.status == 'inactive':
            member.status = 'active'
        member.updated_at = datetime.utcnow()
        db.session.commit()
        return member, None

    @staticmethod
    def delete_member(member_id):
        member = db.get_or_404(Member, member_id)
        active = member.loans.filter_by(status='borrowed').count()
        if active > 0:
            return False, f"Độc giả đang có {active} phiếu mượn chưa hoàn trả, không thể xóa."
        if member.unpaid_fine > 0:
            return False, f"Độc giả còn nợ {int(member.unpaid_fine):,}₫ chưa thanh toán, không thể xóa.".replace(',', '.')
        if member.loans.count() > 0:
            return False, (
                "Hồ sơ độc giả đã có lịch sử lưu thông. Vui lòng chuyển trạng thái thẻ sang "
                "'Ngưng hoạt động' hoặc 'Đã ra trường' để bảo toàn sổ đối chiếu."
            )
        MemberService._release_member_reservations(member.id)
        Reservation.query.filter_by(member_id=member.id).delete()
        db.session.delete(member)
        db.session.commit()
        return True, None

    @staticmethod
    def check_graduation_clearance(member_id):
        member = db.get_or_404(Member, member_id)
        active_loans = Loan.query.filter_by(member_id=member_id, status='borrowed').order_by(Loan.due_date).all()
        unpaid_fine_loans = Loan.query.filter(
            Loan.member_id == member_id,
            Loan.fine_paid == False,
            Loan.fine_amount > 0,
        ).order_by(Loan.return_date.desc()).all()
        total_unpaid = sum(float(l.fine_amount or 0) for l in unpaid_fine_loans)
        applicable = member.is_student_group
        eligible = applicable and len(active_loans) == 0 and total_unpaid <= 0

        return {
            'member': member.to_dict(),
            'applicable': applicable,
            'eligible': eligible,
            'already_cleared': member.status == 'graduated',
            'active_loans': [l.to_dict() for l in active_loans],
            'unpaid_fine_loans': [l.to_dict() for l in unpaid_fine_loans],
            'total_unpaid_fine': total_unpaid,
        }

    @staticmethod
    def confirm_graduation_clearance(member_id):
        member = db.get_or_404(Member, member_id)
        if not member.is_student_group:
            return None, "Thanh lý thẻ ra trường chỉ áp dụng cho Sinh viên và Học viên cao học."
        if member.status == 'graduated':
            return member, None

        active = member.active_loans_count
        unpaid = member.unpaid_fine
        if active > 0 or unpaid > 0:
            reasons = []
            if active > 0:
                reasons.append(f"còn giữ {active} cuốn sách chưa trả")
            if unpaid > 0:
                reasons.append(f"còn nợ {int(unpaid):,}₫ tiền phạt chưa đóng".replace(',', '.'))
            return None, (
                f"{member.full_name} ({member.student_id or member.member_code}) "
                f"chưa thể thanh lý thẻ thư viện do " + " và ".join(reasons) + "."
            )

        MemberService._release_member_reservations(member.id)
        member.status = 'graduated'
        member.clearance_date = date.today()
        member.updated_at = datetime.utcnow()
        db.session.commit()
        return member, None

    @staticmethod
    def list_clearance_candidates(search=None, graduation_year=None, status_filter=None, faculty=None):
        query = Member.query.filter(Member.member_type.in_(['student', 'postgrad']))

        if search:
            s = f'%{search.strip()}%'
            query = query.filter(
                or_(
                    Member.full_name.ilike(s),
                    Member.student_id.ilike(s),
                    Member.member_code.ilike(s),
                    Member.faculty.ilike(s),
                    Member.class_name.ilike(s),
                )
            )

        if graduation_year:
            query = query.filter_by(graduation_year=graduation_year)

        if faculty:
            query = query.filter_by(faculty=faculty)

        members = query.order_by(Member.graduation_year.asc(), Member.full_name.asc()).all()
        results = []
        for m in members:
            active_count = m.active_loans_count
            unpaid = m.unpaid_fine
            eligible = active_count == 0 and unpaid <= 0
            clearance_state = 'cleared' if m.status == 'graduated' else ('eligible' if eligible else 'blocked')
            if status_filter and clearance_state != status_filter:
                continue
            item = m.to_dict()
            item['clearance_state'] = clearance_state
            results.append(item)
        return results

    @staticmethod
    def search_members(query_str, limit=10):
        if not query_str:
            return []
        s = f'%{query_str.strip()}%'
        members = Member.query.filter(
            or_(
                Member.full_name.ilike(s),
                Member.student_id.ilike(s),
                Member.member_code.ilike(s),
                Member.email.ilike(s),
            )
        ).filter_by(status='active').limit(limit).all()
        return [{
            'id': m.id,
            'text': f"{m.student_id or m.member_code} — {m.full_name}",
            'full_name': m.full_name,
            'code': m.member_code,
            'student_id': m.student_id or '',
            'faculty': m.faculty or '',
            'class_name': m.class_name or '',
            'member_type': m.member_type,
            'active_loans': m.active_loans_count,
            'max_loans': m.max_loans_allowed,
            'loan_days': m.loan_duration_days,
            'overdue_loans': m.overdue_loans_count,
            'unpaid_fine': m.unpaid_fine,
            'is_valid_card': m.is_membership_valid,
        } for m in members]

    @staticmethod
    def get_statistics():
        total = Member.query.count()
        active = Member.query.filter_by(status='active').count()
        inactive = Member.query.filter_by(status='inactive').count()
        suspended = Member.query.filter_by(status='suspended').count()
        graduated = Member.query.filter_by(status='graduated').count()

        by_type = db.session.query(
            Member.member_type, func.count(Member.id)
        ).group_by(Member.member_type).all()

        by_faculty = db.session.query(
            Member.faculty, func.count(Member.id)
        ).filter(Member.faculty.isnot(None), Member.faculty != '').group_by(Member.faculty).order_by(func.count(Member.id).desc()).all()

        overdue_members = db.session.query(func.count(func.distinct(Loan.member_id))).filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).scalar() or 0

        current_year = date.today().year
        graduating = Member.query.filter(
            Member.member_type.in_(['student', 'postgrad']),
            Member.status == 'active',
            Member.graduation_year.isnot(None),
            Member.graduation_year <= current_year,
        ).all()
        graduating_blocked = sum(1 for m in graduating if not m.can_graduate)

        return {
            'total': total,
            'active': active,
            'inactive': inactive,
            'suspended': suspended,
            'graduated': graduated,
            'by_type': [{'type': t[0], 'count': t[1]} for t in by_type],
            'by_faculty': [{'faculty': f[0], 'count': f[1]} for f in by_faculty],
            'overdue_members': overdue_members,
            'graduating_blocked': graduating_blocked,
        }

    @staticmethod
    def get_members_with_overdue():
        return db.session.query(Member).join(Loan).filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).distinct().all()
