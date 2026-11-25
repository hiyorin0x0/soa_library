"""
Book Service - SOA Service Layer
Handles all business logic related to books
"""
import os
import uuid
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from sqlalchemy import or_, func
from app.extensions import db
from app.models.book import Book, Category


class BookService:
    """
    Service responsible for all book-related operations.
    Encapsulates business logic and data access for books.
    """

    @staticmethod
    def get_all_books(page=1, per_page=12, search=None, category_id=None,
                      status=None, circulation_type=None, sort_by='title', order='asc'):
        """Get paginated list of books with optional filters"""
        query = Book.query

        if search:
            search_term = f'%{search}%'
            query = query.filter(
                or_(
                    Book.title.ilike(search_term),
                    Book.author.ilike(search_term),
                    Book.isbn.ilike(search_term),
                    Book.publisher.ilike(search_term),
                    Book.department.ilike(search_term),
                )
            )

        if category_id:
            query = query.filter_by(category_id=category_id)

        if circulation_type:
            query = query.filter_by(circulation_type=circulation_type)

        if status:
            if status == 'available':
                query = query.filter(Book.available_copies > 0, Book.status == 'available')
            elif status == 'unavailable':
                query = query.filter(or_(Book.available_copies == 0, Book.status != 'available'))

        # Sorting
        sort_col = getattr(Book, sort_by, Book.title)
        if order == 'desc':
            sort_col = sort_col.desc()
        query = query.order_by(sort_col)

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_book_by_id(book_id):
        """Get a single book by ID"""
        return Book.query.get_or_404(book_id)

    @staticmethod
    def get_book_by_isbn(isbn):
        """Get a book by ISBN"""
        return Book.query.filter_by(isbn=isbn).first()

    @staticmethod
    def create_book(data, cover_file=None):
        """
        Create a new book.
        Args:
            data: dict of book attributes
            cover_file: uploaded file object for cover image
        Returns:
            (Book, error_message)
        """
        # Validate ISBN uniqueness
        if BookService.get_book_by_isbn(data.get('isbn')):
            return None, f"ISBN '{data.get('isbn')}' đã tồn tại trong hệ thống."

        cover_filename = None
        if cover_file and cover_file.filename:
            cover_filename = BookService._save_cover_image(cover_file)

        circulation_type = data.get('circulation_type') or 'borrowable'
        if circulation_type not in ('borrowable', 'reference_only'):
            circulation_type = 'borrowable'

        book = Book(
            isbn=data.get('isbn'),
            title=data.get('title'),
            author=data.get('author'),
            publisher=data.get('publisher'),
            publish_year=data.get('publish_year') or None,
            category_id=data.get('category_id') or None,
            description=data.get('description'),
            total_copies=int(data.get('total_copies', 1)),
            available_copies=int(data.get('total_copies', 1)),
            location=data.get('location'),
            cover_image=cover_filename,
            language=data.get('language', 'Tiếng Việt'),
            pages=data.get('pages') or None,
            price=float(data.get('price') or 0),
            circulation_type=circulation_type,
            department=data.get('department') or None,
            status='available',
        )

        db.session.add(book)
        db.session.commit()
        return book, None

    @staticmethod
    def update_book(book_id, data, cover_file=None):
        """Update an existing book"""
        book = Book.query.get_or_404(book_id)

        # Check ISBN conflict
        existing = BookService.get_book_by_isbn(data.get('isbn'))
        if existing and existing.id != book_id:
            return None, f"ISBN '{data.get('isbn')}' đã được sử dụng bởi sách khác."

        # Handle copies change
        old_total = book.total_copies
        new_total = int(data.get('total_copies', book.total_copies))
        diff = new_total - old_total
        new_available = max(0, book.available_copies + diff)

        if cover_file and cover_file.filename:
            # Delete old cover
            if book.cover_image:
                BookService._delete_cover_image(book.cover_image)
            book.cover_image = BookService._save_cover_image(cover_file)

        book.isbn = data.get('isbn', book.isbn)
        book.title = data.get('title', book.title)
        book.author = data.get('author', book.author)
        book.publisher = data.get('publisher', book.publisher)
        book.publish_year = data.get('publish_year') or book.publish_year
        book.category_id = data.get('category_id') or None
        book.description = data.get('description', book.description)
        book.total_copies = new_total
        book.available_copies = new_available
        book.location = data.get('location', book.location)
        book.language = data.get('language', book.language)
        book.pages = data.get('pages') or book.pages
        book.price = float(data.get('price') if data.get('price') not in (None, '') else book.price)
        if data.get('circulation_type') in ('borrowable', 'reference_only'):
            book.circulation_type = data.get('circulation_type')
        if 'department' in data:
            book.department = data.get('department') or None
        book.updated_at = datetime.utcnow()

        db.session.commit()
        return book, None

    @staticmethod
    def delete_book(book_id):
        """Delete a book (soft delete if has loans)"""
        book = Book.query.get_or_404(book_id)
        active_loans = book.loans.filter_by(status='borrowed').count()
        if active_loans > 0:
            return False, f"Sách đang được mượn ({active_loans} phiếu). Không thể xóa."

        if book.cover_image:
            BookService._delete_cover_image(book.cover_image)

        db.session.delete(book)
        db.session.commit()
        return True, None

    @staticmethod
    def search_books(query_str, limit=10):
        """Quick search for autocomplete"""
        if not query_str:
            return []
        search = f'%{query_str}%'
        books = Book.query.filter(
            or_(Book.title.ilike(search), Book.isbn.ilike(search), Book.author.ilike(search))
        ).limit(limit).all()
        return [{
            'id': b.id,
            'text': f"{b.title} - {b.author}",
            'isbn': b.isbn,
            'available': b.available_copies,
            'circulation_type': b.circulation_type or 'borrowable',
            'is_borrowable': b.is_borrowable,
            'location': b.location or '',
        } for b in books]

    @staticmethod
    def get_statistics():
        """Get book statistics"""
        total = Book.query.count()
        available = Book.query.filter(Book.available_copies > 0, Book.status == 'available').count()
        unavailable = total - available
        reference_only = Book.query.filter_by(circulation_type='reference_only').count()
        total_copies = db.session.query(func.sum(Book.total_copies)).scalar() or 0
        available_copies = db.session.query(func.sum(Book.available_copies)).scalar() or 0

        # By category
        by_category = db.session.query(
            Category.name, func.count(Book.id)
        ).join(Book, isouter=True).group_by(Category.id).all()

        return {
            'total_titles': total,
            'available_titles': available,
            'unavailable_titles': unavailable,
            'reference_only_titles': reference_only,
            'total_copies': int(total_copies),
            'available_copies': int(available_copies),
            'by_category': [{'name': c[0], 'count': c[1]} for c in by_category],
        }

    @staticmethod
    def get_popular_books(limit=10):
        """Get most borrowed books"""
        from app.models.loan import Loan
        result = db.session.query(
            Book, func.count(Loan.id).label('loan_count')
        ).join(Loan).group_by(Book.id).order_by(func.count(Loan.id).desc()).limit(limit).all()
        return [{'book': b.to_dict(), 'loan_count': lc} for b, lc in result]

    @staticmethod
    def get_all_categories():
        """Get all categories"""
        return Category.query.order_by(Category.name).all()

    @staticmethod
    def get_recent_loans(book_id, limit=10):
        """Return recent loan records for a book detail page."""
        from app.models.loan import Loan
        return Loan.query.filter_by(book_id=book_id).order_by(Loan.loan_date.desc()).limit(limit).all()

    @staticmethod
    def create_category(name, description=None, color='#6B7280'):
        """Create a new category"""
        if Category.query.filter_by(name=name).first():
            return None, f"Thể loại '{name}' đã tồn tại."
        cat = Category(name=name, description=description, color=color)
        db.session.add(cat)
        db.session.commit()
        return cat, None

    @staticmethod
    def _save_cover_image(file_obj):
        """Save cover image and return filename"""
        ext = os.path.splitext(secure_filename(file_obj.filename))[1].lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        upload_path = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_path, exist_ok=True)
        file_obj.save(os.path.join(upload_path, filename))
        return filename

    @staticmethod
    def _delete_cover_image(filename):
        """Delete cover image file"""
        try:
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
