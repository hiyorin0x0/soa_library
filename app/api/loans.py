"""Loans service REST API."""
from flask import Blueprint, jsonify, request
from app.services.loan_service import LoanService
from app.service_security import service_token_required

api_loans_bp = Blueprint('api_loans', __name__)


@api_loans_bp.route('/', methods=['GET'])
@service_token_required
def list_loans():
    pagination = LoanService.get_all_loans(
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 20, type=int), search=request.args.get('q', ''),
        status=request.args.get('status', ''), member_id=request.args.get('member_id', type=int),
        book_id=request.args.get('book_id', type=int))
    return jsonify({'status': 'success', 'data': [loan.to_dict() for loan in pagination.items],
                    'meta': {'page': pagination.page, 'pages': pagination.pages,
                             'total': pagination.total, 'per_page': pagination.per_page}})


@api_loans_bp.route('/', methods=['POST'])
@service_token_required
def create_loan():
    data = request.get_json(silent=True) or request.form
    raw_duration = data.get('loan_duration')
    loan_duration = int(raw_duration) if raw_duration not in (None, '') else None
    loan, error = LoanService.create_loan(
        book_id=int(data.get('book_id')), member_id=int(data.get('member_id')),
        librarian_id=int(data.get('librarian_id')),
        loan_duration=loan_duration, notes=data.get('notes'),
        condition=data.get('condition', 'good'))
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': loan.to_dict()}), 201


@api_loans_bp.route('/<int:loan_id>', methods=['GET'])
@service_token_required
def get_loan(loan_id):
    return jsonify({'status': 'success', 'data': LoanService.get_loan_by_id(loan_id).to_dict()})


@api_loans_bp.route('/<int:loan_id>/return', methods=['POST'])
@service_token_required
def return_loan(loan_id):
    data = request.get_json(silent=True) or request.form
    loan, fine, error = LoanService.return_book(
        loan_id, condition_in=data.get('condition_in', 'good'), notes=data.get('notes'),
        waive_fine=str(data.get('waive_fine', '')).lower() in ('1', 'true', 'on'),
        pay_now=str(data.get('pay_now', '')).lower() in ('1', 'true', 'on'))
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': loan.to_dict(), 'fine': fine})


@api_loans_bp.route('/<int:loan_id>/pay-fine', methods=['POST'])
@service_token_required
def pay_fine(loan_id):
    loan, error = LoanService.pay_fine(loan_id)
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': loan.to_dict()})


@api_loans_bp.route('/<int:loan_id>/renew', methods=['POST'])
@service_token_required
def renew_loan(loan_id):
    data = request.get_json(silent=True) or request.form
    raw_ext = data.get('extension_days')
    ext = int(raw_ext) if raw_ext not in (None, '') else None
    loan, error = LoanService.renew_loan(loan_id, ext)
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': loan.to_dict()})


@api_loans_bp.route('/<int:loan_id>/lost', methods=['POST'])
@service_token_required
def mark_lost(loan_id):
    data = request.get_json(silent=True) or request.form
    loan, error = LoanService.mark_as_lost(loan_id, data.get('notes'))
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': loan.to_dict()})


@api_loans_bp.route('/statistics', methods=['GET'])
@service_token_required
def statistics():
    return jsonify({'status': 'success', 'data': LoanService.get_statistics()})


@api_loans_bp.route('/overdue', methods=['GET'])
@service_token_required
def overdue():
    return jsonify({'status': 'success', 'data': [loan.to_dict() for loan in LoanService.get_overdue_loans()]})
