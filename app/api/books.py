"""Books service REST API."""
from flask import Blueprint, jsonify, request
from app.services.book_service import BookService
from app.service_security import service_token_required

api_books_bp = Blueprint('api_books', __name__)


def serialize_book(book):
    payload = book.to_dict()
    payload['category_info'] = book.category.to_dict() if book.category else None
    return payload


@api_books_bp.route('/', methods=['GET'])
@service_token_required
def list_books():
    pagination = BookService.get_all_books(
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 12, type=int),
        search=request.args.get('q', ''), category_id=request.args.get('category', type=int),
        status=request.args.get('status', ''),
        circulation_type=request.args.get('circulation_type', ''),
        sort_by=request.args.get('sort', 'title'),
        order=request.args.get('order', 'asc'))
    return jsonify({'status': 'success', 'data': [serialize_book(b) for b in pagination.items],
                    'meta': {'page': pagination.page, 'pages': pagination.pages,
                             'total': pagination.total, 'per_page': pagination.per_page}})


@api_books_bp.route('/', methods=['POST'])
@service_token_required
def create_book():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    book, error = BookService.create_book(data, request.files.get('cover_image'))
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': serialize_book(book)}), 201


@api_books_bp.route('/<int:book_id>', methods=['GET'])
@service_token_required
def get_book(book_id):
    return jsonify({'status': 'success', 'data': serialize_book(BookService.get_book_by_id(book_id))})


@api_books_bp.route('/<int:book_id>', methods=['PUT'])
@service_token_required
def update_book(book_id):
    data = request.form if request.form else (request.get_json(silent=True) or {})
    book, error = BookService.update_book(book_id, data, request.files.get('cover_image'))
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': serialize_book(book)})


@api_books_bp.route('/<int:book_id>', methods=['DELETE'])
@service_token_required
def delete_book(book_id):
    success, error = BookService.delete_book(book_id)
    if not success:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'success': True})


@api_books_bp.route('/search', methods=['GET'])
@service_token_required
def search_books():
    return jsonify({'status': 'success', 'data': BookService.search_books(
        request.args.get('q', ''), request.args.get('limit', 10, type=int))})


@api_books_bp.route('/statistics', methods=['GET'])
@service_token_required
def statistics():
    return jsonify({'status': 'success', 'data': BookService.get_statistics()})


@api_books_bp.route('/popular', methods=['GET'])
@service_token_required
def popular():
    return jsonify({'status': 'success', 'data': BookService.get_popular_books(
        request.args.get('limit', 10, type=int))})


@api_books_bp.route('/categories', methods=['GET'])
@service_token_required
def list_categories():
    return jsonify({'status': 'success', 'data': [c.to_dict() for c in BookService.get_all_categories()]})


@api_books_bp.route('/categories', methods=['POST'])
@service_token_required
def create_category():
    data = request.get_json(silent=True) or request.form
    category, error = BookService.create_category(data.get('name', '').strip(),
                                                 data.get('description'), data.get('color', '#6B7280'))
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': category.to_dict()}), 201
