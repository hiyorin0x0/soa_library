"""
Member Service - SOA Service Layer
Handles all business logic related to university library readers (students, postgrads, lecturers)
including mandatory student/staff card validation and graduation clearance.
"""
from datetime import datetime, date, timedelta
from sqlalchemy import or_, func
from app.extensions import db
from app.models.member import Member


CARD_DURATION_MONTHS = {
    'student': 48,   # 4 năm đại học
    'postgrad': 24,  # 2 năm cao học
    'lecturer': 60,  # 5 năm giảng viên / cán bộ
}


class MemberService:
    """
    Service responsible for all university library reader operations:
    - Registration tied to Student ID / Staff ID (free borrowing model)
    - Card validity & academic unit (faculty, class, cohort, graduation year)
    - Graduation clearance verification (must return all books & settle all fines)
    """

    @staticmethod
    def _generate_member_code(member_type='student'):
        """Generate unique library card code like SV260001 / HV260001 / GV260001"""
        prefix = {'student': 'SV', 'postgrad': 'HV', 'lecturer': 'GV'}.get(member_type, 'TV')
        year = datetime.now().year % 100
        last = Member.query.order_by(Member.id.desc()).first()
        seq = (last.id + 1) if last else 1
        return f"{prefix}{year:02d}{seq:04d}"

    @staticmethod
    def get_all_members(page=1, per_page=15, search=None, status=None,
                        member_type=None, faculty=None, sort_by='full_name', order='asc'):
        """Get paginated list of readers with filters"""
        query = Member.query

        if search:
            search_term = f'%{search}%'
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

        sort_col = getattr(Member, sort_by, Member.full_name)
        if order == 'desc':
            sort_col = sort_col.desc()
        query = query.order_by(sort_col)

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_member_by_id(member_id):
        return Member.query.get_or_404(member_id)

    @staticmethod
    def get_member_by_code(code):
        return Member.query.filter(
            or_(Member.member_code == code, Member.student_id == code)
        ).first()

    @staticmethod
    def get_faculties():
        rows = db.session.query(Member.faculty).filter(
            Member.faculty.isnot(None), Member.faculty != ''
        ).distinct().order_by(Member.faculty).all()
        return [r[0] for r in rows]

    @staticmethod
    def create_member(data):
        """
        Register a new university reader (free card; Student/Staff ID mandatory).
        Returns: (Member, error_message)
        """
        student_id = (data.get('student_id') or '').strip().upper()
        if not student_id:
            return None, "Bắt buộc nhập Mã số sinh viên (MSSV) hoặc Mã cán bộ để kích hoạt thẻ thư viện miễn phí."

        if Member.query.filter_by(student_id=student_id).first():
            return None, f"Mã sinh viên / cán bộ '{student_id}' đã được đăng ký thẻ thư viện."

        email = (data.get('email') or '').strip().lower()
        if not email:
            return None, "Bắt buộc nhập email của độc giả."
        if Member.query.filter_by(email=email).first():
            return None, f"Email '{email}' đã được đăng ký."

        member_type = data.get('member_type', 'student')
        if member_type not in ('student', 'postgrad', 'lecturer'):
            member_type = 'student'

        months = CARD_DURATION_MONTHS.get(member_type, 48)
        try:
            from dateutil.relativedelta import relativedelta
            end_date = date.today() + relativedelta(months=months)
        except ImportError:
            end_date = date.today() + timedelta(days=months * 30)

        grad_year = None
        if data.get('graduation_year'):
            try:
                grad_year = int(data['graduation_year'])
            except (ValueError, TypeError):
                grad_year = None

        member = Member(
            member_code=MemberService._generate_member_code(member_type),
            student_id=student_id,
            full_name=(data.get('full_name') or '').strip(),
            email=email,
            phone=(data.get('phone') or '').strip() or None,
            address=(data.get('address') or '').strip() or None,
            id_card=(data.get('id_card') or '').strip() or None,
            gender=data.get('gender', 'other'),
            member_type=member_type,
            faculty=(data.get('faculty') or '').strip() or None,
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
    def update_member(member_id, data):
        """Update an existing university reader"""
        member = Member.query.get_or_404(member_id)

        email = (data.get('email') or member.email).strip().lower()
        existing = Member.query.filter_by(email=email).first()
        if existing and existing.id != member_id:
            return None, f"Email '{email}' đã được sử dụng."

        student_id = (data.get('student_id') or member.student_id or '').strip().upper()
        if not student_id:
            return None, "Mã số sinh viên / Mã cán bộ không được để trống."
        existing_sid = Member.query.filter_by(student_id=student_id).first()
        if existing_sid and existing_sid.id != member_id:
            return None, f"Mã sinh viên / cán bộ '{student_id}' đã được sử dụng bởi độc giả khác."

        new_status = data.get('status', member.status)
        if new_status == 'graduated' and member.status != 'graduated':
            if not member.can_graduate:
                return None, (
                    f"Không thể chuyển sang trạng thái 'Đã ra trường': độc giả còn "
                    f"{member.active_loans_count} cuốn sách chưa trả và {int(member.unpaid_fine):,}đ phí phạt chưa đóng."
                ).replace(',', '.')
            member.clearance_date = date.today()

        member.student_id = student_id
        member.full_name = data.get('full_name', member.full_name)
        member.email = email
        member.phone = data.get('phone', member.phone)
        member.address = data.get('address', member.address)
        member.id_card = data.get('id_card', member.id_card)
        member.gender = data.get('gender', member.gender)
        if data.get('member_type') in ('student', 'postgrad', 'lecturer'):
            member.member_type = data.get('member_type')
        if 'faculty' in data:
            member.faculty = (data.get('faculty') or '').strip() or None
        if 'class_name' in data:
            member.class_name = (data.get('class_name') or '').strip() or None
        if 'cohort' in data:
            member.cohort = (data.get('cohort') or '').strip() or None
        if 'graduation_year' in data:
            try:
                member.graduation_year = int(data['graduation_year']) if data['graduation_year'] else None
            except (ValueError, TypeError):
                pass
        member.status = new_status
        member.notes = data.get('notes', member.notes)
        member.updated_at = datetime.utcnow()

        if data.get('date_of_birth'):
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
    def delete_member(member_id):
        """Delete reader if no active loans and no unpaid fines"""
        member = Member.query.get_or_404(member_id)
        active = member.loans.filter_by(status='borrowed').count()
        if active > 0:
            return False, f"Độc giả đang có {active} phiếu mượn chưa trả. Không thể xóa."
        if member.unpaid_fine > 0:
            return False, f"Độc giả còn nợ phí phạt {int(member.unpaid_fine):,}đ chưa thanh toán. Không thể xóa.".replace(',', '.')
        db.session.delete(member)
        db.session.commit()
        return True, None

    @staticmethod
    def check_graduation_clearance(member_id):
        """
        Check whether a student/reader satisfies all library graduation clearance rules:
        1. All borrowed books must be returned (0 active loans)
        2. All late/lost fines must be settled (0 unpaid fine)
        """
        from app.models.loan import Loan
        member = Member.query.get_or_404(member_id)
        active_loans = Loan.query.filter_by(member_id=member_id, status='borrowed').order_by(Loan.due_date).all()
        unpaid_fine_loans = Loan.query.filter(
            Loan.member_id == member_id,
            Loan.fine_paid == False,
            Loan.fine_amount > 0,
        ).order_by(Loan.return_date.desc()).all()
        total_unpaid = sum(float(l.fine_amount or 0) for l in unpaid_fine_loans)
        eligible = len(active_loans) == 0 and total_unpaid <= 0

        return {
            'member': member.to_dict(),
            'eligible': eligible,
            'already_cleared': member.status == 'graduated',
            'active_loans': [l.to_dict() for l in active_loans],
            'unpaid_fine_loans': [l.to_dict() for l in unpaid_fine_loans],
            'total_unpaid_fine': total_unpaid,
        }

    @staticmethod
    def confirm_graduation_clearance(member_id):
        """Confirm library obligation clearance for graduation."""
        member = Member.query.get_or_404(member_id)
        if member.status == 'graduated':
            return member, None

        active = member.active_loans_count
        unpaid = member.unpaid_fine
        if active > 0 or unpaid > 0:
            reasons = []
            if active > 0:
                reasons.append(f"còn {active} cuốn sách đang mượn chưa trả")
            if unpaid > 0:
                reasons.append(f"còn nợ {int(unpaid):,}đ tiền phạt/bồi thường chưa thanh toán".replace(',', '.'))
            return None, (
                f"Sinh viên {member.full_name} ({member.student_id or member.member_code}) "
                f"chưa đủ điều kiện xác nhận ra trường vì " + " và ".join(reasons) + "."
            )

        member.status = 'graduated'
        member.clearance_date = date.today()
        member.updated_at = datetime.utcnow()
        db.session.commit()
        return member, None

    @staticmethod
    def list_clearance_candidates(search=None, graduation_year=None, status_filter=None):
        """Return students/postgrads with their graduation clearance eligibility."""
        query = Member.query.filter(Member.member_type.in_(['student', 'postgrad']))

        if search:
            s = f'%{search}%'
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
        """Quick search for loan creation autocomplete"""
        if not query_str:
            return []
        s = f'%{query_str}%'
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
            'text': f"{m.student_id or m.member_code} - {m.full_name}",
            'code': m.member_code,
            'student_id': m.student_id or '',
            'faculty': m.faculty or '',
            'member_type': m.member_type,
            'active_loans': m.active_loans_count,
            'max_loans': m.max_loans_allowed,
            'loan_days': m.loan_duration_days,
            'overdue_loans': m.overdue_loans_count,
            'unpaid_fine': m.unpaid_fine,
        } for m in members]

    @staticmethod
    def get_statistics():
        """Get reader statistics"""
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

        from app.models.loan import Loan
        overdue_members = db.session.query(func.count(func.distinct(Loan.member_id))).filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).scalar() or 0

        # Graduating students blocked by unreturned books or unpaid fines
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
        """Get list of readers who have overdue books"""
        from app.models.loan import Loan
        return db.session.query(Member).join(Loan).filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).distinct().all()
