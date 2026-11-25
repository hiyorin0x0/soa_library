"""
Loan Model
"""
from datetime import datetime, date
from app.extensions import db


class Loan(db.Model):
    __tablename__ = 'loans'

    id = db.Column(db.Integer, primary_key=True)
    loan_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False, index=True)
    librarian_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    loan_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date)
    
    status = db.Column(db.String(20), default='borrowed', index=True)
    # Status: borrowed, returned, overdue, lost, renewed
    
    renewal_count = db.Column(db.Integer, default=0)
    fine_amount = db.Column(db.Float, default=0)
    fine_paid = db.Column(db.Boolean, default=False)
    fine_reason = db.Column(db.String(50))  # overdue, lost, damaged
    fine_paid_at = db.Column(db.DateTime)
    
    notes = db.Column(db.Text)
    condition_out = db.Column(db.String(50), default='good')  # good, fair, poor
    condition_in = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_overdue(self):
        if self.status == 'borrowed' and self.due_date:
            return date.today() > self.due_date
        return False

    @property
    def days_overdue(self):
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

    @property
    def days_remaining(self):
        if self.status == 'borrowed' and self.due_date:
            delta = (self.due_date - date.today()).days
            return delta
        return 0

    def calculate_fine(self, fine_per_day=2000):
        """Calculate fine based on overdue days"""
        if self.is_overdue:
            return self.days_overdue * fine_per_day
        return 0

    def to_dict(self):
        return {
            'id': self.id,
            'loan_code': self.loan_code,
            'book_id': self.book_id,
            'member_id': self.member_id,
            'librarian_id': self.librarian_id,
            'book': self.book.to_dict() if self.book else None,
            'member': {
                'id': self.member.id,
                'member_code': self.member.member_code,
                'student_id': self.member.student_id,
                'full_name': self.member.full_name,
                'email': self.member.email,
                'phone': self.member.phone,
                'faculty': self.member.faculty,
                'class_name': self.member.class_name,
                'member_type': self.member.member_type,
            } if self.member else None,
            'loan_date': self.loan_date.isoformat() if self.loan_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status,
            'renewal_count': self.renewal_count,
            'fine_amount': self.fine_amount,
            'fine_paid': self.fine_paid,
            'fine_reason': self.fine_reason,
            'fine_paid_at': self.fine_paid_at.isoformat() if self.fine_paid_at else None,
            'condition_out': self.condition_out,
            'condition_in': self.condition_in,
            'is_overdue': self.is_overdue,
            'days_overdue': self.days_overdue,
            'days_remaining': self.days_remaining,
            'notes': self.notes,
        }

    def __repr__(self):
        return f'<Loan {self.loan_code}>'
