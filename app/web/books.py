"""
Books Web Routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.service_clients import books_client, loans_client
from app.service_access import service_router
from app.services.book_service import BookService as LocalBookService
from app.services.loan_service import LoanService as LocalLoanService
from app.services.auth_service import PermissionService

BookService = service_router(LocalBookService, books_client)
LoanService = service_router(LocalLoanService, loans_client)

books_bp = Blueprint('books', __name__)


@books_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_id = request.args.get('category', type=int)
    status = request.args.get('status', '')
    circulation_type = request.args.get('circulation_type', '')
    sort_by = request.args.get('sort', 'title')
    order = request.args.get('order', 'asc')

    pagination = BookService.get_all_books(
        page=page, search=search, category_id=category_id,
        status=status, circulation_type=circulation_type,
        sort_by=sort_by, order=order,
    )
    categories = BookService.get_all_categories()
    stats = BookService.get_statistics()

    return render_template(
        'books/index.html',
        pagination=pagination,
        books=pagination.items,
        categories=categories,
        stats=stats,
        search=search,
        selected_category=category_id,
        selected_status=status,
        selected_circulation=circulation_type,
        sort_by=sort_by,
        order=order,
    )


@books_bp.route('/<int:book_id>')
@login_required
def detail(book_id):
    book = BookService.get_book_by_id(book_id)
    recent_loans = BookService.get_recent_loans(book_id)
    reservations = LoanService.get_reservations(book_id=book_id, status='active', per_page=10).items
    return render_template(
        'books/detail.html',
        book=book,
        recent_loans=recent_loans,
        reservations=reservations,
    )


@books_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    categories = BookService.get_all_categories()

    if request.method == 'POST':
        cover_file = request.files.get('cover_image')
        book, error = BookService.create_book(request.form, cover_file)
        if error:
            flash(error, 'danger')
            return render_template('books/create.html', categories=categories, form_data=request.form)
        flash(f'Đã biên mục tài liệu "{book.title}".', 'success')
        return redirect(url_for('books.detail', book_id=book.id))

    return render_template('books/create.html', categories=categories, form_data={})


@books_bp.route('/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(book_id):
    book = BookService.get_book_by_id(book_id)
    categories = BookService.get_all_categories()

    if request.method == 'POST':
        cover_file = request.files.get('cover_image')
        updated, error = BookService.update_book(book_id, request.form, cover_file)
        if error:
            flash(error, 'danger')
        else:
            flash(f'Đã cập nhật thông tin "{updated.title}".', 'success')
            return redirect(url_for('books.detail', book_id=book_id))

    return render_template('books/edit.html', book=book, categories=categories)


@books_bp.route('/<int:book_id>/delete', methods=['POST'])
@login_required
@PermissionService.require_admin
def delete(book_id):
    book = BookService.get_book_by_id(book_id)
    title = book.title
    success, error = BookService.delete_book(book_id)
    if error:
        flash(error, 'danger')
        return redirect(url_for('books.detail', book_id=book_id))
    flash(f'Đã xóa tài liệu "{title}" khỏi danh mục.', 'success')
    return redirect(url_for('books.index'))


@books_bp.route('/categories')
@login_required
def categories():
    cats = BookService.get_all_categories()
    return render_template('books/categories.html', categories=cats)


@books_bp.route('/categories/create', methods=['POST'])
@login_required
def create_category():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '')
    color = request.form.get('color', '#1B365D')
    cat, error = BookService.create_category(name, description, color)
    if error:
        flash(error, 'danger')
    else:
        flash(f'Đã tạo danh mục "{cat.name}".', 'success')
    return redirect(url_for('books.categories'))


@books_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@PermissionService.require_admin
def delete_category(category_id):
    success, error = BookService.delete_category(category_id)
    if error:
        flash(error, 'danger')
    else:
        flash('Đã xóa danh mục.', 'success')
    return redirect(url_for('books.categories'))
