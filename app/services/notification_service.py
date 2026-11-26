"""
Notification Service - SOA Service Layer
Handles in-app notifications and email alerts
"""
from datetime import datetime, date
from app.extensions import db


class NotificationService:
    """
    Service for sending notifications about overdue books, 
    membership expiry, and other library events.
    """

    _notifications = []  # In-memory store for demo

    @staticmethod
    def get_system_alerts():
        """Get system-wide alerts for the dashboard"""
        from app.models.loan import Loan
        from app.models.member import Member

        alerts = []

        # Overdue books alert
        overdue_count = Loan.query.filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).count()
        if overdue_count > 0:
            alerts.append({
                'type': 'danger',
                'icon': 'exclamation-triangle',
                'message': f'{overdue_count} phiếu mượn đang quá hạn',
                'link': '/loans?status=overdue',
            })

        # Due today
        due_today = Loan.query.filter(
            Loan.status == 'borrowed',
            Loan.due_date == date.today()
        ).count()
        if due_today > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'clock',
                'message': f'{due_today} sách đến hạn trả hôm nay',
                'link': '/loans?status=due_today',
            })

        # Expiring memberships (within 14 days)
        from sqlalchemy import and_
        from datetime import timedelta
        expiring = Member.query.filter(
            and_(
                Member.membership_end >= date.today(),
                Member.membership_end <= date.today() + timedelta(days=14),
                Member.status == 'active',
            )
        ).count()
        if expiring > 0:
            alerts.append({
                'type': 'info',
                'icon': 'id-card',
                'message': f'{expiring} thẻ sinh viên / độc giả sắp hết hạn trong 14 ngày',
                'link': '/members',
            })

        # Ready reservations waiting pickup at circulation desk
        from app.models.reservation import Reservation
        ready_holds = Reservation.query.filter_by(status='ready').count()
        if ready_holds > 0:
            alerts.append({
                'type': 'info',
                'icon': 'bookmark',
                'message': f'{ready_holds} sách đặt trước đang giữ tại quầy chờ sinh viên đến nhận',
                'link': '/loans/reservations?status=ready',
            })

        # Graduating students blocked from clearance
        graduating_students = Member.query.filter(
            Member.member_type.in_(['student', 'postgrad']),
            Member.status == 'active',
            Member.graduation_year.isnot(None),
            Member.graduation_year <= date.today().year,
        ).all()
        blocked_count = sum(1 for m in graduating_students if not m.can_graduate)
        if blocked_count > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'graduation-cap',
                'message': f'{blocked_count} sinh viên khóa cuối chưa trả hết sách / chưa đóng phạt để thanh lý thẻ',
                'link': '/members/clearance?state=blocked',
            })

        return alerts

    @staticmethod
    def send_overdue_reminders():
        """Send email reminders for overdue books"""
        from app.models.loan import Loan
        from app.extensions import mail
        from flask import current_app
        from flask_mail import Message

        overdue_loans = Loan.query.filter(
            Loan.status == 'borrowed',
            Loan.due_date < date.today()
        ).all()

        sent = 0
        for loan in overdue_loans:
            try:
                member = loan.member
                if member and member.email:
                    fine_per_day = current_app.config.get('FINE_PER_DAY', 2000)
                    fine = loan.days_overdue * fine_per_day
                    msg = Message(
                        subject=f"[Thư viện Đại học] Nhắc nhở trả tài liệu quá hạn - {loan.book.title}",
                        recipients=[member.email],
                        body=f"""
Kính gửi {member.full_name} ({member.student_id or member.member_code}),

Bạn đang có tài liệu quá hạn trả tại Thư viện Trường Đại học:
- Tên tài liệu: {loan.book.title}
- Mã phiếu mượn: {loan.loan_code}
- Ngày mượn: {loan.loan_date.strftime('%d/%m/%Y')}
- Hạn trả: {loan.due_date.strftime('%d/%m/%Y')}
- Số ngày quá hạn: {loan.days_overdue} ngày
- Phí phạt dự kiến: {fine:,.0f}đ (2.000đ/ngày)

Lưu ý: Quyền mượn mới và xác nhận hoàn trả sách ra trường sẽ bị tạm khóa cho đến khi bạn hoàn trả đầy đủ tài liệu và thanh toán phí phạt.

Trân trọng,
Thư viện Trường Đại học
                        """
                    )
                    mail.send(msg)
                    sent += 1
            except Exception as e:
                current_app.logger.error(f"Failed to send reminder for loan {loan.id}: {e}")

        return sent
