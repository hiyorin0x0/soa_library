"""Reporting service REST API."""
from flask import Blueprint, jsonify, request
from app.services.report_service import ReportService
from app.services.notification_service import NotificationService
from app.service_security import service_token_required

api_reports_bp = Blueprint('api_reports', __name__)


@api_reports_bp.route('/dashboard', methods=['GET'])
@service_token_required
def dashboard():
    return jsonify({'status': 'success', 'data': ReportService.get_dashboard_summary()})


@api_reports_bp.route('/monthly-loans', methods=['GET'])
@service_token_required
def monthly_loans():
    months = min(max(request.args.get('months', 12, type=int), 1), 60)
    return jsonify({'status': 'success', 'data': ReportService.get_monthly_loan_chart(months)})


@api_reports_bp.route('/top-books', methods=['GET'])
@service_token_required
def top_books():
    limit = min(max(request.args.get('limit', 10, type=int), 1), 100)
    period = min(max(request.args.get('period', 30, type=int), 1), 3650)
    return jsonify({'status': 'success', 'data': ReportService.get_top_books(limit, period)})


@api_reports_bp.route('/top-members', methods=['GET'])
@service_token_required
def top_members():
    limit = min(max(request.args.get('limit', 10, type=int), 1), 100)
    return jsonify({'status': 'success', 'data': ReportService.get_top_members(limit=limit)})


@api_reports_bp.route('/category-distribution', methods=['GET'])
@service_token_required
def category_distribution():
    return jsonify({'status': 'success', 'data': ReportService.get_category_distribution()})


@api_reports_bp.route('/overdue', methods=['GET'])
@service_token_required
def overdue_report():
    return jsonify({'status': 'success', 'data': ReportService.get_overdue_report()})


@api_reports_bp.route('/fines', methods=['GET'])
@service_token_required
def fines():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    return jsonify({'status': 'success', 'data': ReportService.get_fine_report(month, year)})


@api_reports_bp.route('/alerts', methods=['GET'])
@service_token_required
def alerts():
    return jsonify({'status': 'success', 'data': NotificationService.get_system_alerts()})


@api_reports_bp.route('/faculty-loans', methods=['GET'])
@service_token_required
def faculty_loans():
    return jsonify({'status': 'success', 'data': ReportService.get_faculty_loan_stats()})
