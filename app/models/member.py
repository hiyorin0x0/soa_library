"""
Member Model
"""
from datetime import datetime, date
from app.extensions import db


class Member(db.Model):
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    member_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    student_id = db.Column(db.String(30), unique=True, index=True)  # MSSV / Mã cán bộ bắt buộc
    full_name = db.Column(db.String(200), nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    id_card = db.Column(db.String(20))  # CCCD/CMND
    gender = db.Column(db.String(10), default='other')  # male, female, other
    member_type = db.Column(db.String(20), default='student')  # student, postgrad, lecturer
    faculty = db.Column(db.String(150))  # Khoa / Viện
    class_name = db.Column(db.String(60))  # Lớp / Bộ môn
    cohort = db.Column(db.String(30))  # Khóa học (VD: K22)
    graduation_year = db.Column(db.Integer)  # Năm dự kiến tốt nghiệp
    clearance_date = db.Column(db.Date)  # Ngày xác nhận hoàn trả sách ra trường
    status = db.Column(db.String(20), default='active')  # active, suspended, graduated, inactive
    membership_start = db.Column(db.Date, default=date.today)
    membership_end = db.Column(db.Date)
    avatar = db.Column(db.String(300))
    notes = db.Column(db.Text)
    total_fine = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    loans = db.relationship('Loan', backref='member', lazy='dynamic')

    @property
    def active_loans_count(self):
        from app.models.loan import Loan
        return self.loans.filter_by(status='borrowed').count()

    @property
    def overdue_loans_count(self):
        from app.models.loan import Loan
        return self.loans.filter(Loan.status == 'borrowed', Loan.due_date < date.today()).count()

    @property
    def unpaid_fine(self):
        from sqlalchemy import func
        from app.models.loan import Loan
        val = db.session.query(func.sum(Loan.fine_amount)).filter(
            Loan.member_id == self.id,
            Loan.fine_paid == False,
            Loan.fine_amount > 0,
        ).scalar()
        return float(val or 0)

    @property
    def max_loans_allowed(self):
        return {'student': 5, 'postgrad': 7, 'lecturer': 10}.get(self.member_type, 5)

    @property
    def loan_duration_days(self):
        return {'student': 14, 'postgrad': 21, 'lecturer': 30}.get(self.member_type, 14)

    @property
    def can_graduate(self):
        return self.active_loans_count == 0 and self.unpaid_fine <= 0

    @property
    def total_loans_count(self):
        return self.loans.count()

    @property
    def is_membership_valid(self):
        if self.membership_end:
            return date.today() <= self.membership_end
        return True

    @property
    def age(self):
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'member_code': self.member_code,
            'student_id': self.student_id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'id_card': self.id_card,
            'gender': self.gender,
            'member_type': self.member_type,
            'faculty': self.faculty,
            'class_name': self.class_name,
            'cohort': self.cohort,
            'graduation_year': self.graduation_year,
            'clearance_date': self.clearance_date.isoformat() if self.clearance_date else None,
            'status': self.status,
            'membership_start': self.membership_start.isoformat() if self.membership_start else None,
            'membership_end': self.membership_end.isoformat() if self.membership_end else None,
            'notes': self.notes,
            'active_loans_count': self.active_loans_count,
            'overdue_loans_count': self.overdue_loans_count,
            'total_loans_count': self.total_loans_count,
            'max_loans_allowed': self.max_loans_allowed,
            'loan_duration_days': self.loan_duration_days,
            'total_fine': self.total_fine,
            'unpaid_fine': self.unpaid_fine,
            'can_graduate': self.can_graduate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Member {self.member_code}: {self.full_name}>'
