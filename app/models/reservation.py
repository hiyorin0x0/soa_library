"""
Reservation Model - Holds & Queue Management for University Library Circulation
"""
from datetime import datetime, date
from app.extensions import db


class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    reservation_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False, index=True)
    fulfilled_loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=True)

    # pending: waiting for returned copy | ready: copy held at desk | fulfilled | cancelled | expired
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    expires_at = db.Column(db.Date, nullable=True)
    notified_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_active(self):
        return self.status in ('pending', 'ready')

    @property
    def days_until_expiry(self):
        if self.status == 'ready' and self.expires_at:
            return (self.expires_at - date.today()).days
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'reservation_code': self.reservation_code,
            'book_id': self.book_id,
            'member_id': self.member_id,
            'fulfilled_loan_id': self.fulfilled_loan_id,
            'status': self.status,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'notified_at': self.notified_at.isoformat() if self.notified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'days_until_expiry': self.days_until_expiry,
            'notes': self.notes,
            'book': {
                'id': self.book.id,
                'isbn': self.book.isbn,
                'title': self.book.title,
                'author': self.book.author,
                'location': self.book.location,
                'available_copies': self.book.available_copies,
                'total_copies': self.book.total_copies,
            } if self.book else None,
            'member': {
                'id': self.member.id,
                'member_code': self.member.member_code,
                'student_id': self.member.student_id,
                'full_name': self.member.full_name,
                'email': self.member.email,
                'faculty': self.member.faculty,
                'class_name': self.member.class_name,
                'member_type': self.member.member_type,
            } if self.member else None,
        }

    def __repr__(self):
        return f'<Reservation {self.reservation_code} ({self.status})>'
