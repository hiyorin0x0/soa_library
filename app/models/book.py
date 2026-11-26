"""
Book Model
"""
from datetime import datetime
from app.extensions import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#6B7280')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    books = db.relationship('Book', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'book_count': self.books.count(),
        }

    def __repr__(self):
        return f'<Category {self.name}>'


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False, index=True)
    author = db.Column(db.String(200), nullable=False, index=True)
    publisher = db.Column(db.String(200))
    publish_year = db.Column(db.Integer)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    description = db.Column(db.Text)
    total_copies = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)
    location = db.Column(db.String(100))  # Shelf location
    cover_image = db.Column(db.String(300))
    language = db.Column(db.String(50), default='Tiếng Việt')
    pages = db.Column(db.Integer)
    price = db.Column(db.Float, default=0)  # Giá bìa làm căn cứ đền bù khi mất/hỏng (không bán)
    circulation_type = db.Column(db.String(30), default='borrowable')  # borrowable, reference_only
    department = db.Column(db.String(120))  # Khoa / Ngành phụ trách
    status = db.Column(db.String(20), default='available')  # available, unavailable
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    loans = db.relationship('Loan', backref='book', lazy='dynamic')
    reservations = db.relationship('Reservation', backref='book', lazy='dynamic')

    @property
    def is_available(self):
        return (self.available_copies or 0) > 0 and self.status == 'available'

    @property
    def is_borrowable(self):
        return (self.circulation_type or 'borrowable') == 'borrowable' and self.is_available

    @property
    def borrow_count(self):
        return self.loans.count()

    @property
    def active_loans_count(self):
        return self.loans.filter_by(status='borrowed').count()

    @property
    def active_reservations_count(self):
        from app.models.reservation import Reservation
        return self.reservations.filter(Reservation.status.in_(['pending', 'ready'])).count()

    @property
    def pending_reservations_count(self):
        return self.reservations.filter_by(status='pending').count()

    @property
    def ready_reservations_count(self):
        return self.reservations.filter_by(status='ready').count()

    def to_dict(self):
        return {
            'id': self.id,
            'isbn': self.isbn,
            'title': self.title,
            'author': self.author,
            'publisher': self.publisher,
            'publish_year': self.publish_year,
            'category': self.category.name if self.category else None,
            'category_color': self.category.color if self.category else '#1B365D',
            'category_id': self.category_id,
            'description': self.description,
            'total_copies': self.total_copies,
            'available_copies': self.available_copies,
            'active_loans_count': self.active_loans_count,
            'active_reservations_count': self.active_reservations_count,
            'pending_reservations_count': self.pending_reservations_count,
            'ready_reservations_count': self.ready_reservations_count,
            'location': self.location,
            'cover_image': self.cover_image,
            'language': self.language,
            'pages': self.pages,
            'price': self.price,
            'circulation_type': self.circulation_type or 'borrowable',
            'department': self.department,
            'status': self.status,
            'is_available': self.is_available,
            'is_borrowable': self.is_borrowable,
            'borrow_count': self.borrow_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Book {self.isbn}: {self.title}>'
