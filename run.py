"""
University Library Management System - SOA Architecture
Entry point for the application
"""
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.book import Book, Category
from app.models.member import Member
from app.models.loan import Loan
import subprocess
import os
import sys
import time

# Flask CLI imports this module, while the process runner below does not create a
# monolithic app in its gateway and service workers.
app = create_app(role='monolith') if __name__ != '__main__' else None


def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Book': Book,
        'Category': Category,
        'Member': Member,
        'Loan': Loan,
    }


if app is not None:
    app.shell_context_processor(make_shell_context)


def seed_db():
    """Seed the database with realistic Vietnamese University Library data."""
    from app.services.auth_service import AuthService
    from datetime import date, timedelta

    # 1. Staff accounts
    AuthService.create_user(
        username='admin',
        email='admin@thuvien.edu.vn',
        password='Admin@123',
        role='admin',
        full_name='Nguyễn Minh Tuấn (Quản trị)'
    )
    AuthService.create_user(
        username='librarian',
        email='thuthu@thuvien.edu.vn',
        password='Lib@123',
        role='librarian',
        full_name='Trần Thu Hà (Thủ thư)'
    )

    # 2. Academic Categories
    categories_data = [
        ('Giáo trình CNTT', 'Giáo trình chuyên ngành Công nghệ Thông tin, Mạng & Hệ thống', '#1A365D'),
        ('Kinh tế & Quản trị', 'Giáo trình Kinh tế học, Quản trị kinh doanh, Tài chính kế toán', '#8C2D2D'),
        ('Khoa học Cơ bản', 'Toán cao cấp, Xác suất thống kê, Vật lý đại cương', '#2B6CB0'),
        ('Kỹ thuật & Điện tử', 'Mạch điện tử, Hệ thống nhúng, Điều khiển tự động', '#276749'),
        ('Luận văn & Đồ án', 'Khóa luận tốt nghiệp, Luận văn thạc sĩ lưu trữ tại thư viện (Chỉ đọc tại chỗ)', '#744210'),
        ('Tài liệu Tham khảo', 'Sách chuyên khảo và tài liệu tham khảo quốc tế', '#4A5568'),
    ]
    for name, desc, color in categories_data:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name, description=desc, color=color))
    db.session.commit()

    cat_map = {c.name: c.id for c in Category.query.all()}

    # 3. University Library Books & Reference Materials
    sample_books = [
        {
            'isbn': '978-604-913-412-8',
            'title': 'Giáo trình Kiến trúc Hướng Dịch vụ (SOA) & Web Services',
            'author': 'PGS.TS. Nguyễn Văn Hiếu',
            'publisher': 'NXB Đại học Quốc gia',
            'publish_year': 2024,
            'cat': 'Giáo trình CNTT',
            'department': 'Khoa Công nghệ Thông tin',
            'pages': 348,
            'price': 115000,
            'location': 'T2-CNTT-01',
            'total_copies': 8,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Việt',
            'description': 'Trình bày nguyên lý thiết kế dịch vụ, phân rã nghiệp vụ, API Gateway, chuẩn REST/SOAP và triển khai hệ thống phân tán theo kiến trúc SOA.',
        },
        {
            'isbn': '978-604-913-205-6',
            'title': 'Giáo trình Cấu trúc Dữ liệu và Giải thuật',
            'author': 'TS. Đỗ Xuân Lôi',
            'publisher': 'NXB Đại học Quốc gia',
            'publish_year': 2023,
            'cat': 'Giáo trình CNTT',
            'department': 'Khoa Công nghệ Thông tin',
            'pages': 412,
            'price': 98000,
            'location': 'T2-CNTT-02',
            'total_copies': 10,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Việt',
            'description': 'Tài liệu học tập chính thức cho học phần Cấu trúc dữ liệu & Giải thuật bậc đại học.',
        },
        {
            'isbn': '978-604-913-318-3',
            'title': 'Hệ quản trị Cơ sở Dữ liệu Quan hệ',
            'author': 'TS. Lê Tiến Vương',
            'publisher': 'NXB Giáo dục Việt Nam',
            'publish_year': 2022,
            'cat': 'Giáo trình CNTT',
            'department': 'Khoa Công nghệ Thông tin',
            'pages': 380,
            'price': 92000,
            'location': 'T2-CNTT-05',
            'total_copies': 6,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Việt',
            'description': 'Thiết kế lược đồ ER, chuẩn hóa dữ liệu, tối ưu truy vấn SQL và quản lý giao dịch đồng thời.',
        },
        {
            'isbn': '978-0-13-235088-4',
            'title': 'Clean Code: A Handbook of Agile Software Craftsmanship',
            'author': 'Robert C. Martin',
            'publisher': 'Prentice Hall',
            'publish_year': 2008,
            'cat': 'Tài liệu Tham khảo',
            'department': 'Khoa Công nghệ Thông tin',
            'pages': 464,
            'price': 320000,
            'location': 'T3-TK-01',
            'total_copies': 4,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Anh',
            'description': 'Tài liệu tham khảo chuẩn mực về kỹ thuật viết mã nguồn sạch, kiểm thử và tái cấu trúc phần mềm.',
        },
        {
            'isbn': '978-1-491-95035-7',
            'title': 'Designing Data-Intensive Applications',
            'author': 'Martin Kleppmann',
            'publisher': "O'Reilly Media",
            'publish_year': 2017,
            'cat': 'Tài liệu Tham khảo',
            'department': 'Khoa Công nghệ Thông tin',
            'pages': 616,
            'price': 450000,
            'location': 'T3-TK-04',
            'total_copies': 3,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Anh',
            'description': 'Phân tích chuyên sâu về độ tin cậy, khả năng mở rộng và bảo trì các hệ thống phân tán hiện đại.',
        },
        {
            'isbn': '978-604-80-6112-4',
            'title': 'Giáo trình Kinh tế học Vi mô',
            'author': 'PGS.TS. Vũ Kim Dũng',
            'publisher': 'NXB Đại học Kinh tế Quốc dân',
            'publish_year': 2023,
            'cat': 'Kinh tế & Quản trị',
            'department': 'Khoa Kinh tế',
            'pages': 430,
            'price': 105000,
            'location': 'T2-KT-01',
            'total_copies': 7,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Việt',
            'description': 'Cung cầu thị trường, hành vi người tiêu dùng, lý thuyết sản xuất và cấu trúc cạnh tranh.',
        },
        {
            'isbn': '978-604-80-7245-8',
            'title': 'Quản trị Dự án Phần mềm & Chuyển đổi số',
            'author': 'TS. Phạm Quang Huy',
            'publisher': 'NXB Thông tin và Truyền thông',
            'publish_year': 2024,
            'cat': 'Kinh tế & Quản trị',
            'department': 'Khoa Kinh tế',
            'pages': 310,
            'price': 125000,
            'location': 'T2-KT-08',
            'total_copies': 5,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Việt',
            'description': 'Phương pháp quản lý phạm vi, tiến độ, rủi ro và chất lượng trong các dự án công nghệ thông tin.',
        },
        {
            'isbn': '978-604-0-29180-1',
            'title': 'Giáo trình Toán Cao cấp (Tập 1: Đại số & Hình học giải tích)',
            'author': 'GS.TS. Nguyễn Đình Trí',
            'publisher': 'NXB Giáo dục Việt Nam',
            'publish_year': 2022,
            'cat': 'Khoa học Cơ bản',
            'department': 'Khoa Khoa học Cơ bản',
            'pages': 396,
            'price': 78000,
            'location': 'T1-CB-01',
            'total_copies': 12,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Việt',
            'description': 'Giáo trình đại cương bắt buộc cho sinh viên năm nhất khối kỹ thuật và công nghệ.',
        },
        {
            'isbn': '978-604-0-31024-3',
            'title': 'Xác suất Thống kê và Ứng dụng trong Kỹ thuật',
            'author': 'PGS.TS. Tống Đình Quỳ',
            'publisher': 'NXB Bách Khoa Hà Nội',
            'publish_year': 2023,
            'cat': 'Khoa học Cơ bản',
            'department': 'Khoa Khoa học Cơ bản',
            'pages': 320,
            'price': 85000,
            'location': 'T1-CB-04',
            'total_copies': 9,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Việt',
            'description': 'Biến ngẫu nhiên, ước lượng tham số, kiểm định giả thuyết và hồi quy tuyến tính.',
        },
        {
            'isbn': '978-604-95-8410-2',
            'title': 'Thiết kế Hệ thống Nhúng với Vi điều khiển ARM',
            'author': 'TS. Hoàng Mạnh Hùng',
            'publisher': 'NXB Khoa học và Kỹ thuật',
            'publish_year': 2024,
            'cat': 'Kỹ thuật & Điện tử',
            'department': 'Khoa Điện - Điện tử',
            'pages': 365,
            'price': 135000,
            'location': 'T2-DT-02',
            'total_copies': 5,
            'circulation_type': 'borrowable',
            'language': 'Tiếng Việt',
            'description': 'Kiến trúc ARM Cortex-M, lập trình ngoại vi, giao tiếp I2C/SPI/UART và RTOS.',
        },
        # Reference-only materials (Chỉ đọc tại chỗ — enforces book constraint!)
        {
            'isbn': 'KLTN-2025-CNTT-014',
            'title': 'Khóa luận Tốt nghiệp: Xây dựng Hệ thống Quản lý Học vụ theo Kiến trúc Microservices',
            'author': 'Nguyễn Hoàng Long (GVHD: TS. Trần Văn Minh)',
            'publisher': 'Lưu trữ Nội bộ Trường Đại học',
            'publish_year': 2025,
            'cat': 'Luận văn & Đồ án',
            'department': 'Khoa Công nghệ Thông tin',
            'pages': 118,
            'price': 0,
            'location': 'P.DOC-LV-01',
            'total_copies': 2,
            'circulation_type': 'reference_only',
            'language': 'Tiếng Việt',
            'description': 'Bản lưu chiểu khóa luận tốt nghiệp xuất sắc. Theo quy chế thư viện, tài liệu lưu chiểu chỉ phục vụ đọc tại phòng đọc, không cho mượn mang về.',
        },
        {
            'isbn': 'LVTS-2025-KT-008',
            'title': 'Luận văn Thạc sĩ: Đánh giá Hiệu quả Chuyển đổi số tại các Doanh nghiệp vừa và nhỏ',
            'author': 'Lê Thị Thanh Tâm',
            'publisher': 'Lưu trữ Sau đại học',
            'publish_year': 2025,
            'cat': 'Luận văn & Đồ án',
            'department': 'Khoa Kinh tế',
            'pages': 142,
            'price': 0,
            'location': 'P.DOC-LV-05',
            'total_copies': 1,
            'circulation_type': 'reference_only',
            'language': 'Tiếng Việt',
            'description': 'Luận văn thạc sĩ bản gốc có chữ ký hội đồng. Chỉ phục vụ tra cứu tại chỗ.',
        },
        {
            'isbn': '978-0-262-03384-8',
            'title': 'Introduction to Algorithms (CLRS, 4th Edition — Bản tra cứu gốc)',
            'author': 'Thomas H. Cormen, Charles E. Leiserson',
            'publisher': 'MIT Press',
            'publish_year': 2022,
            'cat': 'Tài liệu Tham khảo',
            'department': 'Khoa Công nghệ Thông tin',
            'pages': 1312,
            'price': 1850000,
            'location': 'P.DOC-QH-01',
            'total_copies': 1,
            'circulation_type': 'reference_only',
            'language': 'Tiếng Anh',
            'description': 'Tài liệu nhập ngoại giá trị cao, bản duy nhất của thư viện. Chỉ phục vụ đọc tại chỗ.',
        },
    ]

    for b in sample_books:
        if not Book.query.filter_by(isbn=b['isbn']).first():
            book = Book(
                isbn=b['isbn'],
                title=b['title'],
                author=b['author'],
                publisher=b['publisher'],
                publish_year=b['publish_year'],
                category_id=cat_map.get(b['cat']),
                department=b['department'],
                pages=b['pages'],
                price=b['price'],
                location=b['location'],
                total_copies=b['total_copies'],
                available_copies=b['total_copies'],
                circulation_type=b['circulation_type'],
                language=b['language'],
                description=b['description'],
                status='available',
            )
            db.session.add(book)
    db.session.commit()

    # 4. University Readers (Students, Postgrads, Lecturers)
    today = date.today()
    current_year = today.year
    sample_members = [
        {
            'code': 'SV220001', 'student_id': '22110045', 'name': 'Nguyễn Văn An',
            'email': '22110045@sv.university.edu.vn', 'phone': '0901234561',
            'type': 'student', 'gender': 'male',
            'faculty': 'Khoa Công nghệ Thông tin', 'class_name': 'D22CQCN01',
            'cohort': 'K22', 'grad_year': current_year, 'status': 'active',
        },
        {
            'code': 'SV220002', 'student_id': '22110112', 'name': 'Trần Thị Minh Châu',
            'email': '22110112@sv.university.edu.vn', 'phone': '0912345672',
            'type': 'student', 'gender': 'female',
            'faculty': 'Khoa Công nghệ Thông tin', 'class_name': 'D22CQCN02',
            'cohort': 'K22', 'grad_year': current_year, 'status': 'active',
        },
        {
            'code': 'SV220003', 'student_id': '22120078', 'name': 'Lê Quốc Bảo',
            'email': '22120078@sv.university.edu.vn', 'phone': '0923456783',
            'type': 'student', 'gender': 'male',
            'faculty': 'Khoa Kinh tế', 'class_name': 'D22CQKT01',
            'cohort': 'K22', 'grad_year': current_year, 'status': 'active',
        },
        {
            'code': 'SV230004', 'student_id': '23110209', 'name': 'Phạm Ngọc Diệp',
            'email': '23110209@sv.university.edu.vn', 'phone': '0934567894',
            'type': 'student', 'gender': 'female',
            'faculty': 'Khoa Công nghệ Thông tin', 'class_name': 'D23CQCN01',
            'cohort': 'K23', 'grad_year': current_year + 1, 'status': 'active',
        },
        {
            'code': 'SV240005', 'student_id': '24130064', 'name': 'Hoàng Gia Huy',
            'email': '24130064@sv.university.edu.vn', 'phone': '0945678905',
            'type': 'student', 'gender': 'male',
            'faculty': 'Khoa Điện - Điện tử', 'class_name': 'D24CQDT01',
            'cohort': 'K24', 'grad_year': current_year + 2, 'status': 'active',
        },
        {
            'code': 'HV250006', 'student_id': 'CH250018', 'name': 'Võ Thanh Phương',
            'email': 'ch250018@sdh.university.edu.vn', 'phone': '0956789016',
            'type': 'postgrad', 'gender': 'female',
            'faculty': 'Khoa Kinh tế', 'class_name': 'CH25-QTKD',
            'cohort': 'CH25', 'grad_year': current_year + 1, 'status': 'active',
        },
        {
            'code': 'GV190007', 'student_id': 'GV001042', 'name': 'TS. Đặng Minh Khôi',
            'email': 'khoi.dm@university.edu.vn', 'phone': '0967890127',
            'type': 'lecturer', 'gender': 'male',
            'faculty': 'Khoa Công nghệ Thông tin', 'class_name': 'Bộ môn Kỹ thuật Phần mềm',
            'cohort': None, 'grad_year': None, 'status': 'active',
        },
        {
            'code': 'SV210008', 'student_id': '21110019', 'name': 'Bùi Thị Lan Anh',
            'email': '21110019@sv.university.edu.vn', 'phone': '0978901238',
            'type': 'student', 'gender': 'female',
            'faculty': 'Khoa Khoa học Cơ bản', 'class_name': 'D21CQTO01',
            'cohort': 'K21', 'grad_year': current_year - 1, 'status': 'graduated',
            'clearance_date': today - timedelta(days=45),
        },
    ]

    for m in sample_members:
        if not Member.query.filter_by(student_id=m['student_id']).first():
            member = Member(
                member_code=m['code'],
                student_id=m['student_id'],
                full_name=m['name'],
                email=m['email'],
                phone=m['phone'],
                gender=m['gender'],
                member_type=m['type'],
                faculty=m['faculty'],
                class_name=m['class_name'],
                cohort=m['cohort'],
                graduation_year=m['grad_year'],
                clearance_date=m.get('clearance_date'),
                membership_start=today - timedelta(days=180),
                membership_end=today + timedelta(days=730),
                status=m['status'],
            )
            db.session.add(member)
    db.session.commit()

    # 5. Sample Loans demonstrating all business rules (only if no loans exist yet)
    if Loan.query.count() == 0:
        librarian = User.query.filter_by(username='librarian').first()
        lib_id = librarian.id if librarian else 1

        def get_m(sid):
            return Member.query.filter_by(student_id=sid).first()

        def get_b(isbn):
            return Book.query.filter_by(isbn=isbn).first()

        an = get_m('22110045')       # Graduating student — holds 1 overdue book -> BLOCKED from graduation
        chau = get_m('22110112')     # Graduating student — returned all & paid -> ELIGIBLE for graduation
        bao = get_m('22120078')      # Graduating student — has 1 unpaid fine -> BLOCKED until paid
        diep = get_m('23110209')     # Active student — 1 on-time loan
        huy = get_m('24130064')      # Active student — 1 overdue loan
        phuong = get_m('CH250018')   # Postgrad — 1 active loan
        khoi = get_m('GV001042')     # Lecturer — 1 active loan

        b_soa = get_b('978-604-913-412-8')
        b_dsa = get_b('978-604-913-205-6')
        b_db = get_b('978-604-913-318-3')
        b_cc = get_b('978-0-13-235088-4')
        b_kt = get_b('978-604-80-6112-4')
        b_arm = get_b('978-604-95-8410-2')
        b_ddia = get_b('978-1-491-95035-7')

        sample_loans = [
            # Overdue loan for graduating student An (5 days late)
            Loan(
                loan_code='PM26110001', book_id=b_soa.id, member_id=an.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=19), due_date=today - timedelta(days=5),
                status='borrowed', condition_out='good', notes='Mượn phục vụ đồ án môn SOA',
            ),
            # Overdue loan for student Huy (9 days late)
            Loan(
                loan_code='PM26110002', book_id=b_arm.id, member_id=huy.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=23), due_date=today - timedelta(days=9),
                status='borrowed', condition_out='good', notes='Mượn thực hành vi điều khiển',
            ),
            # Returned late with UNPAID fine for graduating student Bao (12.000đ)
            Loan(
                loan_code='PM26100003', book_id=b_kt.id, member_id=bao.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=30), due_date=today - timedelta(days=16),
                return_date=today - timedelta(days=10), status='returned',
                condition_out='good', condition_in='good',
                fine_amount=12000, fine_paid=False, fine_reason='overdue',
                notes='Trả muộn 6 ngày — chưa đóng phạt',
            ),
            # Returned on time for graduating student Chau (eligible for clearance!)
            Loan(
                loan_code='PM26100004', book_id=b_db.id, member_id=chau.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=25), due_date=today - timedelta(days=11),
                return_date=today - timedelta(days=12), status='returned',
                condition_out='good', condition_in='good',
                fine_amount=0, fine_paid=True,
            ),
            # Active on-time loan for Diep
            Loan(
                loan_code='PM26110005', book_id=b_dsa.id, member_id=diep.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=4), due_date=today + timedelta(days=10),
                status='borrowed', condition_out='good',
            ),
            # Active on-time loan for Postgrad Phuong (21 days duration)
            Loan(
                loan_code='PM26110006', book_id=b_kt.id, member_id=phuong.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=6), due_date=today + timedelta(days=15),
                status='borrowed', condition_out='good',
            ),
            # Active on-time loan for Lecturer Khoi (30 days duration)
            Loan(
                loan_code='PM26110007', book_id=b_ddia.id, member_id=khoi.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=3), due_date=today + timedelta(days=27),
                status='borrowed', condition_out='good', notes='Tài liệu biên soạn bài giảng',
            ),
            # Returned with PAID fine for Diep
            Loan(
                loan_code='PM26090008', book_id=b_cc.id, member_id=diep.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=50), due_date=today - timedelta(days=36),
                return_date=today - timedelta(days=34), status='returned',
                condition_out='good', condition_in='good',
                fine_amount=4000, fine_paid=True, fine_reason='overdue',
            ),
        ]

        for l in sample_loans:
            db.session.add(l)
            if l.status == 'borrowed':
                bk = Book.query.get(l.book_id)
                if bk and bk.available_copies > 0:
                    bk.available_copies -= 1

        bao.total_fine = 12000
        db.session.commit()

    print("[OK] University Library database seeded successfully!")
    print("   Admin: admin / Admin@123")
    print("   Librarian: librarian / Lib@123")


if app is not None:
    app.cli.command(name='seed-db')(seed_db)

if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    args = sys.argv[1:]
    mode = args[0] if args else 'all'

    if mode == 'seed':
        seed_app = create_app(role='monolith')
        with seed_app.app_context():
            db.create_all()
            seed_db()
        raise SystemExit(0)

    if mode == 'reset-seed':
        seed_app = create_app(role='monolith')
        with seed_app.app_context():
            db.drop_all()
            db.create_all()
            seed_db()
        raise SystemExit(0)

    if mode == 'service':
        if len(args) != 2:
            raise SystemExit('Usage: python run.py service <books|members|loans|reports>')
        from app.service_app import create_service_app
        service_name = args[1]
        service_app = create_service_app(service_name)
        with service_app.app_context():
            db.create_all()
        service_app.run(host=os.environ.get('SERVICE_BIND_HOST', '127.0.0.1'),
                        port=service_app.config['SERVICE_PORTS'][service_name],
                        debug=False, use_reloader=False, threaded=True)
        raise SystemExit(0)

    if mode == 'gateway':
        gateway = create_app(role='gateway')
        with gateway.app_context():
            db.create_all()
        gateway.run(host=os.environ.get('GATEWAY_BIND_HOST', '0.0.0.0'),
                    port=gateway.config['SERVICE_PORTS']['gateway'],
                    debug=gateway.config.get('DEBUG', False), use_reloader=False, threaded=True)
        raise SystemExit(0)

    if mode != 'all':
        raise SystemExit('Usage: python run.py [all|gateway|service <name>|seed|reset-seed]')

    bootstrap_app = create_app(role='gateway')
    with bootstrap_app.app_context():
        db.create_all()

    service_names = ('books', 'members', 'loans', 'reports')
    children = []
    try:
        for service_name in service_names:
            children.append(subprocess.Popen(
                [sys.executable, os.path.join(BASE_DIR, 'run.py'), 'service', service_name],
                cwd=BASE_DIR))
        children.append(subprocess.Popen(
            [sys.executable, os.path.join(BASE_DIR, 'run.py'), 'gateway'], cwd=BASE_DIR))
        print('University Library SOA services are starting:')
        ports = bootstrap_app.config['SERVICE_PORTS']
        print(f"  Gateway: http://localhost:{ports['gateway']}")
        print(f"  Books:   http://localhost:{ports['books']}/health")
        print(f"  Members: http://localhost:{ports['members']}/health")
        print(f"  Loans:   http://localhost:{ports['loans']}/health")
        print(f"  Reports: http://localhost:{ports['reports']}/health")
        print('Press Ctrl+C to stop all processes.')
        while True:
            failed = next((child for child in children if child.poll() not in (None, 0)), None)
            if failed:
                raise RuntimeError(f'A service process exited with code {failed.returncode}.')
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nStopping all University Library SOA services...')
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
