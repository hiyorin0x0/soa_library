"""
Book Service - SOA Service Layer
Handles all business logic related to catalog items and academic categories
"""
import os
import uuid
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from sqlalchemy import or_, func
from app.extensions import db
from app.models.book import Book, Category
from app.models.loan import Loan
from app.models.reservation import Reservation


class BookService:
    """Service responsible for catalog management, inventory invariants, and categories."""

    @staticmethod
    def get_all_books(page=1, per_page=12, search=None, category_id=None,
                      status=None, circulation_type=None, department=None,
                      room=None, sort_by='title', order='asc'):
        query = Book.query

        if search:
            search_term = f'%{search.strip()}%'
            query = query.filter(
                or_(
                    Book.title.ilike(search_term),
                    Book.author.ilike(search_term),
                    Book.isbn.ilike(search_term),
                    Book.publisher.ilike(search_term),
                    Book.department.ilike(search_term),
                    Book.location.ilike(search_term),
                )
            )

        if category_id:
            query = query.filter_by(category_id=category_id)

        if circulation_type:
            query = query.filter_by(circulation_type=circulation_type)

        if department:
            query = query.filter_by(department=department)

        if room:
            query = query.filter(Book.location.ilike(f'{room.strip()}%'))

        if status:
            if status == 'available':
                query = query.filter(Book.available_copies > 0, Book.status == 'available')
            elif status == 'unavailable':
                query = query.filter(or_(Book.available_copies <= 0, Book.status != 'available'))
            elif status == 'suspended':
                query = query.filter(Book.status != 'available')

        allowed_sorts = {
            'title': Book.title,
            'publish_year': Book.publish_year,
            'created_at': Book.created_at,
            'available_copies': Book.available_copies,
            'price': Book.price,
        }
        sort_col = allowed_sorts.get(sort_by, Book.title)
        if order == 'desc':
            sort_col = sort_col.desc()
        query = query.order_by(sort_col, Book.id.desc())

        return query.paginate(page=max(1, page), per_page=min(max(1, per_page), 60), error_out=False)

    @staticmethod
    def get_book_by_id(book_id):
        return db.get_or_404(Book, book_id)

    @staticmethod
    def get_book_by_isbn(isbn):
        if not isbn:
            return None
        return Book.query.filter_by(isbn=isbn.strip()).first()

    @staticmethod
    def get_departments():
        rows = db.session.query(Book.department).filter(
            Book.department.isnot(None), Book.department != ''
        ).distinct().order_by(Book.department).all()
        return [r[0] for r in rows]

    @staticmethod
    def create_book(data, cover_file=None):
        isbn = (data.get('isbn') or '').strip()
        title = (data.get('title') or '').strip()
        author = (data.get('author') or '').strip()

        if not isbn or not title or not author:
            return None, "Vui lòng nhập đầy đủ mã ISBN/lưu chiểu, nhan đề và tác giả."

        if BookService.get_book_by_isbn(isbn):
            return None, f"Mã ISBN / lưu chiểu '{isbn}' đã tồn tại trong danh mục."

        try:
            total_copies = int(data.get('total_copies', 1))
        except (ValueError, TypeError):
            return None, "Số lượng bản sao không hợp lệ."
        if total_copies < 1:
            return None, "Tổng số bản sao nhập kho phải tối thiểu là 1."

        try:
            price = float(data.get('price') or 0)
        except (ValueError, TypeError):
            return None, "Giá bìa không hợp lệ."
        if price < 0:
            return None, "Giá bìa không được là số âm."

        publish_year = None
        if data.get('publish_year') not in (None, ''):
            try:
                publish_year = int(data['publish_year'])
                if publish_year < 1800 or publish_year > datetime.now().year + 2:
                    return None, "Năm xuất bản không hợp lệ."
            except (ValueError, TypeError):
                return None, "Năm xuất bản không hợp lệ."

        pages = None
        if data.get('pages') not in (None, ''):
            try:
                pages = max(1, int(data['pages']))
            except (ValueError, TypeError):
                pages = None

        cover_filename = None
        if cover_file and getattr(cover_file, 'filename', ''):
            cover_filename, err = BookService._save_cover_image(cover_file)
            if err:
                return None, err

        circulation_type = data.get('circulation_type') or 'borrowable'
        if circulation_type not in ('borrowable', 'reference_only'):
            circulation_type = 'borrowable'

        category_id = None
        if data.get('category_id') not in (None, ''):
            try:
                category_id = int(data['category_id'])
            except (ValueError, TypeError):
                category_id = None

        book = Book(
            isbn=isbn,
            title=title,
            author=author,
            publisher=(data.get('publisher') or '').strip() or None,
            publish_year=publish_year,
            category_id=category_id,
            description=(data.get('description') or '').strip() or None,
            total_copies=total_copies,
            available_copies=total_copies,
            location=(data.get('location') or '').strip() or None,
            cover_image=cover_filename,
            language=(data.get('language') or 'Tiếng Việt').strip(),
            pages=pages,
            price=price,
            circulation_type=circulation_type,
            department=(data.get('department') or '').strip() or None,
            status='available',
        )

        db.session.add(book)
        db.session.commit()
        return book, None

    @staticmethod
    def update_book(book_id, data, cover_file=None):
        book = db.get_or_404(Book, book_id)

        isbn = (data.get('isbn') or book.isbn).strip()
        title = (data.get('title') or book.title).strip()
        author = (data.get('author') or book.author).strip()
        if not isbn or not title or not author:
            return None, "Mã ISBN, nhan đề và tác giả không được để trống."

        existing = BookService.get_book_by_isbn(isbn)
        if existing and existing.id != book_id:
            return None, f"Mã ISBN / lưu chiểu '{isbn}' đã được sử dụng bởi tài liệu khác."

        borrowed_count = Loan.query.filter_by(book_id=book.id, status='borrowed').count()
        ready_holds = Reservation.query.filter_by(book_id=book.id, status='ready').count()
        in_use = borrowed_count + ready_holds

        try:
            new_total = int(data.get('total_copies', book.total_copies))
        except (ValueError, TypeError):
            return None, "Tổng số bản sao không hợp lệ."

        if new_total < max(1, in_use) and new_total != 0:
            if new_total < in_use:
                return None, (
                    f"Không thể giảm tổng số bản xuống {new_total} vì hiện đang có "
                    f"{borrowed_count} bản đang cho mượn và {ready_holds} bản đang giữ tại quầy."
                )
        if new_total < 0:
            return None, "Tổng số bản sao không được âm."
        if new_total < in_use:
            return None, f"Tổng số bản phải tối thiểu bằng số bản đang lưu thông ({in_use} bản)."

        new_circulation = data.get('circulation_type') or book.circulation_type or 'borrowable'
        if new_circulation == 'reference_only' and in_use > 0:
            return None, (
                f"Không thể chuyển sang 'Chỉ đọc tại chỗ' khi đang có {in_use} bản được mượn hoặc giữ chỗ."
            )

        if cover_file and getattr(cover_file, 'filename', ''):
            new_cover, err = BookService._save_cover_image(cover_file)
            if err:
                return None, err
            if book.cover_image:
                BookService._delete_cover_image(book.cover_image)
            book.cover_image = new_cover

        book.isbn = isbn
        book.title = title
        book.author = author
        if 'publisher' in data:
            book.publisher = (data.get('publisher') or '').strip() or None
        if 'publish_year' in data:
            if data.get('publish_year') in (None, ''):
                book.publish_year = None
            else:
                try:
                    book.publish_year = int(data['publish_year'])
                except (ValueError, TypeError):
                    return None, "Năm xuất bản không hợp lệ."
        if 'category_id' in data:
            try:
                book.category_id = int(data['category_id']) if data.get('category_id') else None
            except (ValueError, TypeError):
                book.category_id = None
        if 'description' in data:
            book.description = (data.get('description') or '').strip() or None

        book.total_copies = new_total
        book.available_copies = max(0, new_total - in_use)

        if 'location' in data:
            book.location = (data.get('location') or '').strip() or None
        if 'language' in data and data.get('language'):
            book.language = data.get('language').strip()
        if 'pages' in data:
            try:
                book.pages = int(data['pages']) if data.get('pages') else None
            except (ValueError, TypeError):
                pass
        if 'price' in data and data.get('price') not in (None, ''):
            try:
                price_val = float(data['price'])
                if price_val < 0:
                    return None, "Giá bìa không được âm."
                book.price = price_val
            except (ValueError, TypeError):
                return None, "Giá bìa không hợp lệ."

        if new_circulation in ('borrowable', 'reference_only'):
            book.circulation_type = new_circulation
        if 'department' in data:
            book.department = (data.get('department') or '').strip() or None
        if data.get('status') in ('available', 'unavailable'):
            book.status = data.get('status')
        elif new_total == 0:
            book.status = 'unavailable'

        book.updated_at = datetime.utcnow()
        db.session.commit()
        return book, None

    @staticmethod
    def delete_book(book_id):
        book = db.get_or_404(Book, book_id)
        active_loans = book.loans.filter_by(status='borrowed').count()
        if active_loans > 0:
            return False, f"Tài liệu đang có {active_loans} phiếu mượn chưa hoàn trả, không thể xóa."

        active_res = book.reservations.filter(Reservation.status.in_(['pending', 'ready'])).count()
        if active_res > 0:
            return False, f"Tài liệu đang có {active_res} yêu cầu đặt giữ chỗ đang hiệu lực."

        if book.loans.count() > 0:
            return False, (
                "Tài liệu đã có lịch sử lưu thông trong sổ kế toán thư viện. "
                "Vui lòng chuyển trạng thái sang 'Tạm ngưng lưu thông' thay vì xóa vĩnh viễn."
            )

        Reservation.query.filter_by(book_id=book.id).delete()
        if book.cover_image:
            BookService._delete_cover_image(book.cover_image)

        db.session.delete(book)
        db.session.commit()
        return True, None

    @staticmethod
    def search_books(query_str, limit=10):
        if not query_str:
            return []
        search = f'%{query_str.strip()}%'
        books = Book.query.filter(
            or_(Book.title.ilike(search), Book.isbn.ilike(search), Book.author.ilike(search))
        ).limit(limit).all()
        return [{
            'id': b.id,
            'text': f"{b.title} — {b.author}",
            'title': b.title,
            'author': b.author,
            'isbn': b.isbn,
            'available': b.available_copies,
            'total': b.total_copies,
            'circulation_type': b.circulation_type or 'borrowable',
            'status': b.status,
            'is_borrowable': b.is_borrowable,
            'location': b.location or '',
            'department': b.department or '',
            'price': b.price or 0,
        } for b in books]

    @staticmethod
    def get_statistics():
        total = Book.query.count()
        available = Book.query.filter(Book.available_copies > 0, Book.status == 'available').count()
        unavailable = total - available
        reference_only = Book.query.filter_by(circulation_type='reference_only').count()
        borrowable = total - reference_only
        total_copies = db.session.query(func.sum(Book.total_copies)).scalar() or 0
        available_copies = db.session.query(func.sum(Book.available_copies)).scalar() or 0

        by_category = db.session.query(
            Category.name, func.count(Book.id)
        ).join(Book, isouter=True).group_by(Category.id).all()

        return {
            'total_titles': total,
            'borrowable_titles': borrowable,
            'available_titles': available,
            'unavailable_titles': unavailable,
            'reference_only_titles': reference_only,
            'total_copies': int(total_copies),
            'available_copies': int(available_copies),
            'by_category': [{'name': c[0], 'count': c[1]} for c in by_category],
        }

    @staticmethod
    def get_opac_facets(search=None, category_id=None, availability=None, room=None):
        """Compute accurate circulation-type counts without self-filtering distortion."""
        base = Book.query
        if search:
            term = f'%{search.strip()}%'
            base = base.filter(
                or_(
                    Book.title.ilike(term),
                    Book.author.ilike(term),
                    Book.isbn.ilike(term),
                    Book.publisher.ilike(term),
                    Book.department.ilike(term),
                    Book.location.ilike(term),
                )
            )
        if category_id:
            base = base.filter_by(category_id=category_id)
        if room:
            base = base.filter(Book.location.ilike(f'{room.strip()}%'))
        if availability == 'available':
            base = base.filter(Book.available_copies > 0, Book.status == 'available')

        total = base.count()
        ref_count = base.filter(Book.circulation_type == 'reference_only').count()
        borrow_count = total - ref_count
        return {
            'all': total,
            'borrowable': borrow_count,
            'reference_only': ref_count,
        }

    @staticmethod
    def get_popular_books(limit=10):
        result = db.session.query(
            Book, func.count(Loan.id).label('loan_count')
        ).join(Loan).group_by(Book.id).order_by(func.count(Loan.id).desc()).limit(limit).all()
        return [{'book': b.to_dict(), 'loan_count': lc} for b, lc in result]

    @staticmethod
    def get_all_categories():
        return Category.query.order_by(Category.name).all()

    @staticmethod
    def get_recent_loans(book_id, limit=10):
        return Loan.query.filter_by(book_id=book_id).order_by(Loan.loan_date.desc(), Loan.id.desc()).limit(limit).all()

    @staticmethod
    def create_category(name, description=None, color='#1B365D'):
        name = (name or '').strip()
        if not name:
            return None, "Tên danh mục không được để trống."
        if Category.query.filter(func.lower(Category.name) == name.lower()).first():
            return None, f"Danh mục '{name}' đã tồn tại."
        cat = Category(name=name, description=(description or '').strip() or None, color=color or '#1B365D')
        db.session.add(cat)
        db.session.commit()
        return cat, None

    @staticmethod
    def delete_category(category_id):
        cat = db.get_or_404(Category, category_id)
        count = cat.books.count()
        if count > 0:
            return False, f"Danh mục '{cat.name}' đang chứa {count} đầu tài liệu, không thể xóa."
        db.session.delete(cat)
        db.session.commit()
        return True, None

    @staticmethod
    def _save_cover_image(file_obj):
        raw_name = secure_filename(file_obj.filename or '')
        ext = os.path.splitext(raw_name)[1].lower().lstrip('.')
        allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'webp'})
        if not ext or ext not in allowed:
            return None, f"Định dạng ảnh không hợp lệ. Chỉ chấp nhận: {', '.join(sorted(allowed))}."
        filename = f"{uuid.uuid4().hex}.{ext}"
        upload_path = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_path, exist_ok=True)
        file_obj.save(os.path.join(upload_path, filename))
        return filename, None

    @staticmethod
    def _delete_cover_image(filename):
        try:
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
