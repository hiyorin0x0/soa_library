"""Members service REST API."""
from flask import Blueprint, jsonify, request
from app.services.member_service import MemberService
from app.service_security import service_token_required

api_members_bp = Blueprint('api_members', __name__)


@api_members_bp.route('/', methods=['GET'])
@service_token_required
def list_members():
    pagination = MemberService.get_all_members(
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 15, type=int),
        search=request.args.get('q', ''),
        status=request.args.get('status', ''),
        member_type=request.args.get('type', ''),
        faculty=request.args.get('faculty', ''),
        sort_by=request.args.get('sort', 'full_name'),
        order=request.args.get('order', 'asc'),
    )
    return jsonify({
        'status': 'success',
        'data': [m.to_dict() for m in pagination.items],
        'meta': {
            'page': pagination.page,
            'pages': pagination.pages,
            'total': pagination.total,
            'per_page': pagination.per_page,
        },
    })


@api_members_bp.route('/', methods=['POST'])
@service_token_required
def create_member():
    member, error = MemberService.create_member(request.get_json(silent=True) or request.form)
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': member.to_dict()}), 201


@api_members_bp.route('/<int:member_id>', methods=['GET'])
@service_token_required
def get_member(member_id):
    return jsonify({'status': 'success', 'data': MemberService.get_member_by_id(member_id).to_dict()})


@api_members_bp.route('/<int:member_id>', methods=['PUT'])
@service_token_required
def update_member(member_id):
    member, error = MemberService.update_member(member_id, request.get_json(silent=True) or request.form)
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': member.to_dict()})


@api_members_bp.route('/<int:member_id>/renew-card', methods=['POST'])
@service_token_required
def renew_card(member_id):
    data = request.get_json(silent=True) or request.form
    months = int(data.get('months') or 12)
    member, error = MemberService.renew_card(member_id, months=months)
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': member.to_dict()})


@api_members_bp.route('/<int:member_id>', methods=['DELETE'])
@service_token_required
def delete_member(member_id):
    success, error = MemberService.delete_member(member_id)
    if not success:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'success': True})


@api_members_bp.route('/lookup', methods=['POST'])
@service_token_required
def lookup_portal():
    data = request.get_json(silent=True) or request.form
    result, error = MemberService.lookup_reader_portal(
        data.get('identifier', ''),
        data.get('verify', ''),
    )
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': result})


@api_members_bp.route('/by-code', methods=['GET'])
@service_token_required
def get_by_code():
    member = MemberService.get_member_by_code(request.args.get('code', ''))
    if not member:
        return jsonify({'status': 'error', 'message': 'Không tìm thấy độc giả.'}), 409
    return jsonify({'status': 'success', 'data': member.to_dict()})


@api_members_bp.route('/search', methods=['GET'])
@service_token_required
def search_members():
    return jsonify({'status': 'success', 'data': MemberService.search_members(
        request.args.get('q', ''), request.args.get('limit', 10, type=int))})


@api_members_bp.route('/statistics', methods=['GET'])
@service_token_required
def statistics():
    return jsonify({'status': 'success', 'data': MemberService.get_statistics()})


@api_members_bp.route('/faculties', methods=['GET'])
@service_token_required
def faculties():
    return jsonify({'status': 'success', 'data': MemberService.get_faculties()})


@api_members_bp.route('/clearance', methods=['GET'])
@service_token_required
def list_clearance():
    data = MemberService.list_clearance_candidates(
        search=request.args.get('q', ''),
        graduation_year=request.args.get('graduation_year', type=int),
        status_filter=request.args.get('state', ''),
        faculty=request.args.get('faculty', ''),
    )
    return jsonify({'status': 'success', 'data': data})


@api_members_bp.route('/<int:member_id>/clearance', methods=['GET'])
@service_token_required
def check_clearance(member_id):
    return jsonify({'status': 'success', 'data': MemberService.check_graduation_clearance(member_id)})


@api_members_bp.route('/<int:member_id>/clearance', methods=['POST'])
@service_token_required
def confirm_clearance(member_id):
    member, error = MemberService.confirm_graduation_clearance(member_id)
    if error:
        return jsonify({'status': 'error', 'message': error}), 409
    return jsonify({'status': 'success', 'data': member.to_dict()})
