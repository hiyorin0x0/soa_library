"""
Report Service - SOA Service Layer
Handles all reporting and analytics functionality
"""
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from app.extensions import db
from app.models.book import Book, Category
from app.models.member import Member
from app.models.loan import Loan
from app.services.book_service import BookService
from app.services.member_service import MemberService
from app.services.loan_service import LoanService


class ReportService:
    """
    Service responsible for generating reports and analytics.
    """

    @staticmethod
    def get_dashboard_summary():
        """Get summary statistics for dashboard"""
        book_stats = BookService.get_statistics()
        member_stats = MemberService.get_statistics()
        loan_stats = LoanService.get_statistics()

        # Recent activity
        recent_loans = Loan.query.order_by(Loan.created_at.desc()).limit(10).all()
        overdue_loans = LoanService.get_overdue_loans()
        due_today = LoanService.get_today_due()

        return {
            'books': book_stats,
            'members': member_stats,
            'loans': loan_stats,
            'recent_loans': [l.to_dict() for l in recent_loans],
            'overdue_count': len(overdue_loans),
            'due_today_count': len(due_today),
        }

    @staticmethod
    def get_monthly_loan_chart(months=12):
        """Get monthly loan data for chart"""
        result = []
        today = date.today()

        for i in range(months - 1, -1, -1):
            month = today.month - i
            year = today.year
            while month <= 0:
                month += 12
                year -= 1

            borrowed = db.session.query(func.count(Loan.id)).filter(
                extract('year', Loan.loan_date) == year,
                extract('month', Loan.loan_date) == month,
            ).scalar() or 0

            returned = db.session.query(func.count(Loan.id)).filter(
                extract('year', Loan.return_date) == year,
                extract('month', Loan.return_date) == month,
                Loan.status == 'returned',
            ).scalar() or 0

            result.append({
                'month': f"{month:02d}/{year}",
                'borrowed': borrowed,
                'returned': returned,
            })

        return result

    @staticmethod
    def get_top_books(limit=10, period_days=30):
        """Get top borrowed books in a period"""
        since = date.today() - timedelta(days=period_days)
        result = db.session.query(
            Book, func.count(Loan.id).label('count')
        ).join(Loan).filter(
            Loan.loan_date >= since
        ).group_by(Book.id).order_by(func.count(Loan.id).desc()).limit(limit).all()

        return [{'book': b.to_dict(), 'count': c} for b, c in result]

    @staticmethod
    def get_top_members(limit=10, period_days=30):
        """Get most active members"""
        since = date.today() - timedelta(days=period_days)
        result = db.session.query(
            Member, func.count(Loan.id).label('count')
        ).join(Loan).filter(
            Loan.loan_date >= since
        ).group_by(Member.id).order_by(func.count(Loan.id).desc()).limit(limit).all()

        return [{'member': m.to_dict(), 'count': c} for m, c in result]

    @staticmethod
    def get_category_distribution():
        """Get book distribution by category"""
        result = db.session.query(
            Category.name, Category.color, func.count(Book.id).label('book_count'),
            func.sum(Book.total_copies).label('total_copies'),
        ).outerjoin(Book, Book.category_id == Category.id).group_by(Category.id).all()

        return [{
            'name': r.name,
            'color': r.color,
            'book_count': r.book_count,
            'total_copies': int(r.total_copies or 0),
        } for r in result]

    @staticmethod
    def get_fine_report(month=None, year=None):
        """Get fine collection report"""
        query = Loan.query.filter(Loan.fine_amount > 0)

        if month and year:
            query = query.filter(
                extract('year', Loan.return_date) == year,
                extract('month', Loan.return_date) == month,
            )

        loans = query.all()
        total_fine = sum(l.fine_amount for l in loans)
        paid_fine = sum(l.fine_amount for l in loans if l.fine_paid)
        unpaid_fine = total_fine - paid_fine

        return {
            'total_fine': total_fine,
            'paid_fine': paid_fine,
            'unpaid_fine': unpaid_fine,
            'loans': [l.to_dict() for l in loans],
        }

    @staticmethod
    def get_overdue_report():
        """Get detailed overdue report"""
        overdue = LoanService.get_overdue_loans()
        from flask import current_app
        fine_per_day = current_app.config.get('FINE_PER_DAY', 2000)

        return [{
            'loan': l.to_dict(),
            'days_overdue': l.days_overdue,
            'estimated_fine': l.days_overdue * fine_per_day,
        } for l in overdue]

    @staticmethod
    def get_faculty_loan_stats():
        """Loan activity grouped by university faculty."""
        rows = db.session.query(
            Member.faculty,
            func.count(Loan.id).label('loan_count'),
        ).join(Loan, Loan.member_id == Member.id).filter(
            Member.faculty.isnot(None), Member.faculty != ''
        ).group_by(Member.faculty).order_by(func.count(Loan.id).desc()).all()
        return [{'faculty': r.faculty, 'loan_count': r.loan_count} for r in rows]
