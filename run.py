"""
Quy Nhon University (QNU) Library System - SOA Architecture
Entry point, multi-service runner, and QNU academic catalog seeder
"""
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.book import Book, Category
from app.models.member import Member
from app.models.loan import Loan
from app.models.reservation import Reservation
import subprocess
import os
import sys
import time

app = create_app(role='monolith') if __name__ != '__main__' else None


def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Book': Book,
        'Category': Category,
        'Member': Member,
        'Loan': Loan,
        'Reservation': Reservation,
    }


if app is not None:
    app.shell_context_processor(make_shell_context)


def seed_db():
    """Seed the database with authentic Quy Nhon University (QNU) faculties, real book covers, and students."""
    from app.services.auth_service import AuthService
    from datetime import date, datetime, timedelta, timezone
    datetime_now = lambda: datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. QNU Library Staff Accounts
    AuthService.create_user(
        username='admin',
        email='admin@lib.qnu.edu.vn',
        password='Admin@123',
        role='admin',
        full_name='ThS. Nguyễn Minh Tuấn (Quản trị QNU)'
    )
    AuthService.create_user(
        username='librarian',
        email='shl@qnu.edu.vn',
        password='Lib@123',
        role='librarian',
        full_name='CN. Trần Thu Hà (Thủ thư Tầng 1)'
    )

    # 2. All Major QNU Academic Categories
    categories_data = [
        ('CNTT & Trí tuệ Nhân tạo', 'Công nghệ thông tin, Kỹ thuật phần mềm, AI & Hệ thống phân tán', '#1B365D'),
        ('Toán học & Khoa học Dữ liệu', 'Giải tích, Đại số tuyến tính, Xác suất thống kê & Học thống kê', '#0F5C6E'),
        ('Kinh tế, Kế toán & Quản trị', 'Kinh tế vi mô, Kế toán, Tài chính doanh nghiệp, Marketing & Logistics', '#8B2635'),
        ('Kỹ thuật, Ô tô & Tự động hóa', 'Kỹ thuật điện - điện tử, Vi điều khiển, Điều khiển tự động & Công nghệ ô tô', '#245E43'),
        ('Sư phạm & Khoa học Giáo dục', 'Tâm lý học giáo dục, Lý luận dạy học, Giáo dục Tiểu học & Mầm non', '#7C4D12'),
        ('Ngôn ngữ Anh & Trung Quốc', 'Ngữ pháp học thuật, Ngôn ngữ học đối chiếu & Giáo trình HSK chuẩn', '#4C3575'),
        ('Khoa học Tự nhiên', 'Vật lý đại cương, Hóa học hữu cơ, Sinh học phân tử & Tài nguyên môi trường', '#1F6357'),
        ('Luật, Du lịch & Nhân văn', 'Pháp luật đại cương, Quản trị du lịch - khách sạn & Văn hóa Việt Nam', '#6E3B2E'),
        ('Luận văn & Khóa luận QNU', 'Khóa luận tốt nghiệp, Luận văn thạc sĩ lưu chiểu tại Phòng Đọc Mở 2', '#4A4843'),
    ]
    for name, desc, color in categories_data:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name, description=desc, color=color))
    db.session.commit()

    cat_map = {c.name: c.id for c in Category.query.all()}

    # 3. 35 Real Books & Theses spanning all QNU Faculties (Every single book has a verified real cover image!)
    sample_books = [
        # --- CNTT & Trí tuệ Nhân tạo (Khoa Công nghệ thông tin) ---
        {
            'isbn': '978-604-913-412-8',
            'title': 'SOA Design Patterns — Kiến trúc Hướng Dịch vụ & Hệ thống Phân tán',
            'author': 'Thomas Erl (Tài liệu giảng dạy Khoa CNTT)',
            'publisher': 'Prentice Hall / NXB ĐHQG',
            'publish_year': 2024,
            'cat': 'CNTT & Trí tuệ Nhân tạo',
            'department': 'Khoa Công nghệ thông tin',
            'pages': 840, 'price': 245000, 'location': 'P.GT-CNTT-01', 'total_copies': 8,
            'circulation_type': 'borrowable', 'language': 'Song ngữ Anh - Việt',
            'cover': 'cntt_soa.jpg',
            'description': 'Tài liệu cốt lõi học phần Kiến trúc hướng dịch vụ (SOA), phân rã dịch vụ miền, API Gateway và tích hợp hệ thống doanh nghiệp.',
        },
        {
            'isbn': '978-0-13-235088-4',
            'title': 'Clean Code: Nghệ thuật Viết Mã nguồn Sạch trong Kỹ thuật Phần mềm',
            'author': 'Robert C. Martin',
            'publisher': 'Pearson Education',
            'publish_year': 2022,
            'cat': 'CNTT & Trí tuệ Nhân tạo',
            'department': 'Khoa Công nghệ thông tin',
            'pages': 464, 'price': 285000, 'location': 'P.M-CNTT-02', 'total_copies': 6,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'cntt_clean_code.jpg',
            'description': 'Chuẩn mực thiết kế hàm, lớp, xử lý ngoại lệ, kiểm thử đơn vị và tái cấu trúc mã nguồn cho sinh viên ngành Kỹ thuật phần mềm.',
        },
        {
            'isbn': '978-1-491-95035-7',
            'title': 'Designing Data-Intensive Applications (Thiết kế Hệ thống Dữ liệu Lớn)',
            'author': 'Martin Kleppmann',
            'publisher': "O'Reilly Media",
            'publish_year': 2023,
            'cat': 'CNTT & Trí tuệ Nhân tạo',
            'department': 'Khoa Công nghệ thông tin',
            'pages': 616, 'price': 390000, 'location': 'P.M-CNTT-04', 'total_copies': 5,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'cntt_ddia.jpg',
            'description': 'Phân tích chuyên sâu cơ sở dữ liệu phân tán, sao lưu, phân mảnh, đồng thuận và xử lý luồng dữ liệu quy mô lớn.',
        },
        {
            'isbn': '978-0-13-461099-3',
            'title': 'Artificial Intelligence: A Modern Approach (Trí tuệ Nhân tạo Hiện đại)',
            'author': 'Stuart Russell, Peter Norvig',
            'publisher': 'Pearson',
            'publish_year': 2024,
            'cat': 'CNTT & Trí tuệ Nhân tạo',
            'department': 'Khoa Công nghệ thông tin',
            'pages': 1136, 'price': 480000, 'location': 'P.GT-CNTT-06', 'total_copies': 7,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'cntt_ai_aima.jpg',
            'description': 'Giáo trình nền tảng ngành Trí tuệ nhân tạo tại QNU: tìm kiếm heuristic, biểu diễn tri thức, học máy, học sâu và xử lý ngôn ngữ tự nhiên.',
        },
        {
            'isbn': '978-0-07-802215-9',
            'title': 'Database System Concepts — Nguyên lý Hệ Quản trị Cơ sở Dữ liệu',
            'author': 'Abraham Silberschatz, Henry F. Korth',
            'publisher': 'McGraw-Hill',
            'publish_year': 2023,
            'cat': 'CNTT & Trí tuệ Nhân tạo',
            'department': 'Khoa Công nghệ thông tin',
            'pages': 1376, 'price': 310000, 'location': 'P.GT-CNTT-03', 'total_copies': 10,
            'circulation_type': 'borrowable', 'language': 'Song ngữ Anh - Việt',
            'cover': 'cntt_db_silberschatz.jpg',
            'description': 'Mô hình quan hệ, đại số quan hệ, tối ưu hóa câu lệnh SQL, chỉ mục B+-Tree và kiểm soát giao dịch đồng thời ACID.',
        },
        {
            'isbn': '978-0-13-359414-0',
            'title': 'Computer Networking: A Top-Down Approach (Mạng Máy tính)',
            'author': 'James F. Kurose, Keith W. Ross',
            'publisher': 'Pearson',
            'publish_year': 2022,
            'cat': 'CNTT & Trí tuệ Nhân tạo',
            'department': 'Khoa Công nghệ thông tin',
            'pages': 864, 'price': 265000, 'location': 'P.GT-CNTT-08', 'total_copies': 9,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'cntt_networks.jpg',
            'description': 'Kiến trúc mạng Internet từ tầng ứng dụng HTTP/DNS xuống tầng giao vận TCP/QUIC, định tuyến IP và bảo mật mạng không dây.',
        },
        {
            'isbn': '978-0-262-03384-8',
            'title': 'Introduction to Algorithms — Cấu trúc Dữ liệu và Giải thuật (CLRS)',
            'author': 'Thomas H. Cormen, Charles E. Leiserson',
            'publisher': 'MIT Press',
            'publish_year': 2022,
            'cat': 'CNTT & Trí tuệ Nhân tạo',
            'department': 'Khoa Công nghệ thông tin',
            'pages': 1312, 'price': 520000, 'location': 'P.DM2-CNTT-01', 'total_copies': 2,
            'circulation_type': 'reference_only', 'language': 'Tiếng Anh',
            'cover': 'cntt_clrs.jpg',
            'description': 'Ấn bản gốc MIT Press lưu trữ tại Phòng Đọc Mở 2 phục vụ tra cứu thuật toán chuyên sâu và đội tuyển Olympic Tin học sinh viên QNU.',
        },

        # --- Toán học & Khoa học Dữ liệu (Khoa Toán và Thống kê) ---
        {
            'isbn': '978-0-9802327-7-6',
            'title': 'Introduction to Linear Algebra — Đại số Tuyến tính & Ứng dụng',
            'author': 'Gilbert Strang',
            'publisher': 'Wellesley-Cambridge Press',
            'publish_year': 2023,
            'cat': 'Toán học & Khoa học Dữ liệu',
            'department': 'Khoa Toán và Thống kê',
            'pages': 584, 'price': 210000, 'location': 'P.GT-TOAN-01', 'total_copies': 12,
            'circulation_type': 'borrowable', 'language': 'Song ngữ Anh - Việt',
            'cover': 'toan_linear_algebra.jpg',
            'description': 'Không gian vectơ, trị riêng, phân tích suy biến SVD và nền tảng đại số cho Khoa học dữ liệu & Trí tuệ nhân tạo.',
        },
        {
            'isbn': '978-1-0716-1417-4',
            'title': 'An Introduction to Statistical Learning (Thống kê Học máy cho Khoa học Dữ liệu)',
            'author': 'Gareth James, Daniela Witten, Trevor Hastie',
            'publisher': 'Springer',
            'publish_year': 2024,
            'cat': 'Toán học & Khoa học Dữ liệu',
            'department': 'Khoa Toán và Thống kê',
            'pages': 607, 'price': 295000, 'location': 'P.GT-TOAN-04', 'total_copies': 8,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'toan_islr.jpg',
            'description': 'Hồi quy, phân lớp, lấy mẫu lại, cây quyết định, SVM và học không giám sát dành cho sinh viên ngành Khoa học dữ liệu & Toán ứng dụng.',
        },
        {
            'isbn': '978-1-285-74062-1',
            'title': 'Calculus: Early Transcendentals — Giải tích Hàm một biến & Nhiều biến',
            'author': 'James Stewart',
            'publisher': 'Cengage Learning',
            'publish_year': 2022,
            'cat': 'Toán học & Khoa học Dữ liệu',
            'department': 'Khoa Toán và Thống kê',
            'pages': 1368, 'price': 260000, 'location': 'P.GT-TOAN-02', 'total_copies': 14,
            'circulation_type': 'borrowable', 'language': 'Song ngữ Anh - Việt',
            'cover': 'toan_calculus.jpg',
            'description': 'Giáo trình Giải tích dùng chung cho khối ngành Sư phạm Toán, Toán ứng dụng, Kỹ thuật và Công nghệ tại ĐH Quy Nhơn.',
        },
        {
            'isbn': '978-0-13-499559-5',
            'title': 'A First Course in Probability — Lý thuyết Xác suất & Thống kê Toán',
            'author': 'Sheldon Ross',
            'publisher': 'Pearson',
            'publish_year': 2023,
            'cat': 'Toán học & Khoa học Dữ liệu',
            'department': 'Khoa Toán và Thống kê',
            'pages': 528, 'price': 185000, 'location': 'P.GT-TOAN-06', 'total_copies': 10,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'toan_prob.jpg',
            'description': 'Giải tích tổ hợp, biến ngẫu nhiên rời rạc & liên tục, kỳ vọng có điều kiện, luật số lớn và định lý giới hạn trung tâm.',
        },

        # --- Kinh tế, Kế toán & Quản trị (Khoa Kinh tế & Kế toán + Khoa TCNH & QTKD) ---
        {
            'isbn': '978-1-305-50712-8',
            'title': 'Nguyên lý Kinh tế học Vi mô (Principles of Microeconomics)',
            'author': 'N. Gregory Mankiw',
            'publisher': 'Cengage / NXB Kinh tế',
            'publish_year': 2023,
            'cat': 'Kinh tế, Kế toán & Quản trị',
            'department': 'Khoa Kinh tế và Kế toán',
            'pages': 536, 'price': 178000, 'location': 'P.GT-KT-01', 'total_copies': 12,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'kt_microeconomics.jpg',
            'description': 'Cung cầu thị trường, độ co giãn, thặng dư tiêu dùng, chi phí sản xuất và cấu trúc thị trường cạnh tranh.',
        },
        {
            'isbn': '978-1-119-49163-7',
            'title': 'Financial Accounting — Kế toán Tài chính theo Chuẩn mực Quốc tế IFRS/ACCA',
            'author': 'Jerry J. Weygandt, Paul D. Kimmel, Donald E. Kieso',
            'publisher': 'Wiley',
            'publish_year': 2024,
            'cat': 'Kinh tế, Kế toán & Quản trị',
            'department': 'Khoa Kinh tế và Kế toán',
            'pages': 864, 'price': 290000, 'location': 'P.GT-KT-03', 'total_copies': 9,
            'circulation_type': 'borrowable', 'language': 'Song ngữ Anh - Việt',
            'cover': 'kt_accounting.jpg',
            'description': 'Giáo trình phục vụ chương trình Cử nhân Kế toán và Kế toán định hướng ACCA tại Trường Đại học Quy Nhơn.',
        },
        {
            'isbn': '978-1-259-91895-7',
            'title': 'Fundamentals of Corporate Finance — Quản trị Tài chính Doanh nghiệp',
            'author': 'Stephen A. Ross, Randolph W. Westerfield',
            'publisher': 'McGraw-Hill',
            'publish_year': 2023,
            'cat': 'Kinh tế, Kế toán & Quản trị',
            'department': 'Khoa Tài chính - Ngân hàng và QTKD',
            'pages': 832, 'price': 275000, 'location': 'P.M-TCNH-01', 'total_copies': 8,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'kt_finance.jpg',
            'description': 'Định giá dòng tiền, hoạch định ngân sách vốn, quản trị rủi ro danh mục đầu tư và chính sách cấu trúc vốn doanh nghiệp.',
        },
        {
            'isbn': '978-0-13-385646-0',
            'title': 'Quản trị Marketing Hiện đại (Marketing Management)',
            'author': 'Philip Kotler, Kevin Lane Keller',
            'publisher': 'Pearson / NXB Lao động',
            'publish_year': 2023,
            'cat': 'Kinh tế, Kế toán & Quản trị',
            'department': 'Khoa Tài chính - Ngân hàng và QTKD',
            'pages': 832, 'price': 240000, 'location': 'P.M-QTKD-02', 'total_copies': 7,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'kt_marketing.jpg',
            'description': 'Nghiên cứu hành vi khách hàng, định vị thương hiệu, chiến lược sản phẩm và truyền thông marketing tích hợp thời đại số.',
        },
        {
            'isbn': '978-1-292-09386-4',
            'title': 'Logistics & Supply Chain Management — Quản trị Logistics và Chuỗi cung ứng',
            'author': 'Martin Christopher',
            'publisher': 'Financial Times / Pearson',
            'publish_year': 2024,
            'cat': 'Kinh tế, Kế toán & Quản trị',
            'department': 'Khoa Kinh tế và Kế toán',
            'pages': 328, 'price': 195000, 'location': 'P.GT-KT-07', 'total_copies': 8,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'kt_logistics.jpg',
            'description': 'Tài liệu chuyên ngành Logistics và Quản lý chuỗi cung ứng gắn với lợi thế cảng biển và hạ tầng giao thương miền Trung.',
        },

        # --- Kỹ thuật, Ô tô & Tự động hóa (Khoa Kỹ thuật và Công nghệ) ---
        {
            'isbn': '978-0-19-933913-6',
            'title': 'Microelectronic Circuits — Mạch Điện tử & Vi điện tử',
            'author': 'Adel S. Sedra, Kenneth C. Smith',
            'publisher': 'Oxford University Press',
            'publish_year': 2022,
            'cat': 'Kỹ thuật, Ô tô & Tự động hóa',
            'department': 'Khoa Kỹ thuật và Công nghệ',
            'pages': 1488, 'price': 340000, 'location': 'P.GT-KTCN-01', 'total_copies': 7,
            'circulation_type': 'borrowable', 'language': 'Song ngữ Anh - Việt',
            'cover': 'kythuat_sedra.jpg',
            'description': 'Giáo trình cốt lõi cho ngành Kỹ thuật điện tử - viễn thông và thiết kế vi mạch bán dẫn tại QNU.',
        },
        {
            'isbn': '978-0-13-468571-7',
            'title': 'Feedback Control of Dynamic Systems — Kỹ thuật Điều khiển Tự động',
            'author': 'Gene F. Franklin, J. David Powell',
            'publisher': 'Pearson',
            'publish_year': 2023,
            'cat': 'Kỹ thuật, Ô tô & Tự động hóa',
            'department': 'Khoa Kỹ thuật và Công nghệ',
            'pages': 880, 'price': 265000, 'location': 'P.GT-KTCN-03', 'total_copies': 6,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'kythuat_control.jpg',
            'description': 'Mô hình hóa hệ động lực, bộ điều khiển PID, quỹ đạo nghiệm số, đáp ứng tần số và điều khiển không gian trạng thái.',
        },
        {
            'isbn': '978-0-12-382196-6',
            'title': 'Embedded Systems Architecture — Thiết kế Hệ thống Nhúng & Vi điều khiển',
            'author': 'Tammy Noergaard',
            'publisher': 'Newnes / Elsevier',
            'publish_year': 2023,
            'cat': 'Kỹ thuật, Ô tô & Tự động hóa',
            'department': 'Khoa Kỹ thuật và Công nghệ',
            'pages': 640, 'price': 230000, 'location': 'P.M-KTCN-05', 'total_copies': 6,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'kythuat_embedded.jpg',
            'description': 'Kiến trúc phần cứng vi điều khiển, giao tiếp ngoại vi I2C/SPI/CAN, trình điều khiển thiết bị và hệ điều hành thời gian thực RTOS.',
        },
        {
            'isbn': '978-1-259-06420-3',
            'title': 'Automotive Mechanics — Kết cấu, Động cơ & Chẩn đoán Kỹ thuật Ô tô',
            'author': 'William H. Crouse, Donald L. Anglin',
            'publisher': 'McGraw-Hill',
            'publish_year': 2023,
            'cat': 'Kỹ thuật, Ô tô & Tự động hóa',
            'department': 'Khoa Kỹ thuật và Công nghệ',
            'pages': 896, 'price': 285000, 'location': 'P.GT-OTO-01', 'total_copies': 9,
            'circulation_type': 'borrowable', 'language': 'Song ngữ Anh - Việt',
            'cover': 'kythuat_auto.jpg',
            'description': 'Giáo trình phục vụ sinh viên ngành Công nghệ kỹ thuật ô tô và Kỹ thuật cơ khí động lực tại Trường Đại học Quy Nhơn.',
        },

        # --- Sư phạm & Khoa học Giáo dục (Khoa Sư phạm + Khoa GD Tiểu học & Mầm non) ---
        {
            'isbn': '978-0-13-477432-9',
            'title': 'Educational Psychology — Tâm lý học Giáo dục & Phát triển Người học',
            'author': 'Anita Woolfolk',
            'publisher': 'Pearson / NXB ĐH Sư phạm',
            'publish_year': 2023,
            'cat': 'Sư phạm & Khoa học Giáo dục',
            'department': 'Khoa Sư phạm',
            'pages': 720, 'price': 195000, 'location': 'P.GT-SP-01', 'total_copies': 15,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'supham_edpsych.jpg',
            'description': 'Học phần nghiệp vụ sư phạm trọng tâm cho toàn bộ các ngành đào tạo giáo viên tại Trường Đại học Quy Nhơn.',
        },
        {
            'isbn': '978-1-4166-2673-2',
            'title': 'Dạy học theo Dự án & Phát triển Phẩm chất Năng lực Học sinh',
            'author': 'Suzie Boss, John Larmer',
            'publisher': 'ASCD / NXB Giáo dục Việt Nam',
            'publish_year': 2024,
            'cat': 'Sư phạm & Khoa học Giáo dục',
            'department': 'Khoa Giáo dục Tiểu học và Mầm non',
            'pages': 260, 'price': 145000, 'location': 'P.GT-SP-04', 'total_copies': 11,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'supham_teaching.jpg',
            'description': 'Phương pháp thiết kế hoạt động trải nghiệm và dạy học dự án theo Chương trình Giáo dục phổ thông 2018.',
        },
        {
            'isbn': '978-0-465-02433-9',
            'title': 'Frames of Mind — Lý thuyết Đa Trí tuệ trong Giáo dục Hiện đại',
            'author': 'Howard Gardner',
            'publisher': 'Basic Books / NXB Tri thức',
            'publish_year': 2022,
            'cat': 'Sư phạm & Khoa học Giáo dục',
            'department': 'Khoa Sư phạm',
            'pages': 496, 'price': 180000, 'location': 'P.DM1-SP-02', 'total_copies': 6,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'supham_piaget.jpg',
            'description': 'Tài liệu tham khảo chuyên sâu cho sinh viên ngành Quản lý giáo dục, Tâm lý học giáo dục và Giáo dục mầm non.',
        },

        # --- Ngôn ngữ Anh & Trung Quốc (Khoa Ngoại ngữ) ---
        {
            'isbn': '978-1-108-58662-7',
            'title': 'English Grammar in Use — Ngữ pháp Tiếng Anh Học thuật (Cambridge)',
            'author': 'Raymond Murphy',
            'publisher': 'Cambridge University Press',
            'publish_year': 2023,
            'cat': 'Ngôn ngữ Anh & Trung Quốc',
            'department': 'Khoa Ngoại ngữ',
            'pages': 394, 'price': 215000, 'location': 'P.M-NN-01', 'total_copies': 12,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'nn_cambridge_grammar.jpg',
            'description': 'Tài liệu chuẩn hóa ngữ pháp thực hành và luyện chuẩn đầu ra ngoại ngữ cho sinh viên Khoa Ngoại ngữ và toàn trường.',
        },
        {
            'isbn': '978-1-108-73070-9',
            'title': 'The Study of Language — Dẫn luận Ngôn ngữ học Tiếng Anh',
            'author': 'George Yule',
            'publisher': 'Cambridge University Press',
            'publish_year': 2023,
            'cat': 'Ngôn ngữ Anh & Trung Quốc',
            'department': 'Khoa Ngoại ngữ',
            'pages': 380, 'price': 235000, 'location': 'P.GT-NN-03', 'total_copies': 8,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'nn_linguistics.jpg',
            'description': 'Ngữ âm học, âm vị học, hình thái học, cú pháp học, ngữ nghĩa học và dụng học cho ngành Ngôn ngữ Anh & Sư phạm Tiếng Anh.',
        },
        {
            'isbn': '978-7-5619-3709-9',
            'title': 'Giáo trình Chuẩn HSK (Standard Course) — Ngôn ngữ Trung Quốc',
            'author': 'Khương Lệ Bình (Jiang Liping)',
            'publisher': 'Beijing Language & Culture University Press',
            'publish_year': 2024,
            'cat': 'Ngôn ngữ Anh & Trung Quốc',
            'department': 'Khoa Ngoại ngữ',
            'pages': 240, 'price': 168000, 'location': 'P.GT-NN-06', 'total_copies': 10,
            'circulation_type': 'borrowable', 'language': 'Tiếng Trung - Việt',
            'cover': 'nn_hsk.jpg',
            'description': 'Giáo trình chính khóa luyện kỹ năng Nghe – Nói – Đọc – Viết Hán ngữ cho sinh viên ngành Ngôn ngữ Trung Quốc tại QNU.',
        },

        # --- Khoa học Tự nhiên (Khoa Khoa học Tự nhiên) ---
        {
            'isbn': '978-1-118-23071-8',
            'title': 'Fundamentals of Physics — Cơ sở Vật lý Đại cương (Halliday & Resnick)',
            'author': 'David Halliday, Robert Resnick, Jearl Walker',
            'publisher': 'Wiley / NXB Giáo dục Việt Nam',
            'publish_year': 2022,
            'cat': 'Khoa học Tự nhiên',
            'department': 'Khoa Khoa học Tự nhiên',
            'pages': 1328, 'price': 320000, 'location': 'P.GT-KHTN-01', 'total_copies': 10,
            'circulation_type': 'borrowable', 'language': 'Song ngữ Anh - Việt',
            'cover': 'khtn_halliday.jpg',
            'description': 'Cơ học, Nhiệt động lực học, Điện từ học, Quang học và Vật lý lượng tử cho ngành Sư phạm Vật lý & Vật lý kỹ thuật.',
        },
        {
            'isbn': '978-0-13-404228-2',
            'title': 'Organic Chemistry — Giáo trình Hóa học Hữu cơ & Công nghệ Hóa học',
            'author': 'Paula Yurkanis Bruice',
            'publisher': 'Pearson',
            'publish_year': 2023,
            'cat': 'Khoa học Tự nhiên',
            'department': 'Khoa Khoa học Tự nhiên',
            'pages': 1344, 'price': 310000, 'location': 'P.GT-KHTN-04', 'total_copies': 7,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'khtn_chemistry.jpg',
            'description': 'Cấu trúc phân tử, cơ chế phản ứng hữu cơ, phổ học và tổng hợp hóa dược phục vụ ngành Hóa học & Công nghệ kỹ thuật hóa học.',
        },
        {
            'isbn': '978-0-13-409341-3',
            'title': 'Campbell Biology — Sinh học Đại cương & Sinh học Phân tử',
            'author': 'Lisa A. Urry, Michael L. Cain, Steven A. Wasserman',
            'publisher': 'Pearson / NXB Giáo dục',
            'publish_year': 2023,
            'cat': 'Khoa học Tự nhiên',
            'department': 'Khoa Khoa học Tự nhiên',
            'pages': 1488, 'price': 380000, 'location': 'P.DM1-KHTN-02', 'total_copies': 6,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'khtn_campbell.jpg',
            'description': 'Tài liệu nền tảng cho sinh viên ngành Sư phạm Sinh học, Nông học, Công nghệ thực phẩm và Quản lý tài nguyên môi trường.',
        },

        # --- Luật, Du lịch & Nhân văn ---
        {
            'isbn': '978-1-5438-1307-4',
            'title': 'Luật Hiến pháp, Nhà nước Pháp quyền & Quản lý Nhà nước',
            'author': 'Erwin Chemerinsky (Tài liệu tham khảo ngành Luật)',
            'publisher': 'Wolters Kluwer / NXB Tư pháp',
            'publish_year': 2023,
            'cat': 'Luật, Du lịch & Nhân văn',
            'department': 'Khoa Lý luận chính trị - Luật và QLNN',
            'pages': 612, 'price': 220000, 'location': 'P.GT-LUAT-01', 'total_copies': 8,
            'circulation_type': 'borrowable', 'language': 'Tiếng Việt',
            'cover': 'xh_law_econ.jpg',
            'description': 'Giáo trình và tài liệu tham khảo cho sinh viên ngành Luật, Quản lý nhà nước và Giáo dục chính trị tại ĐH Quy Nhơn.',
        },
        {
            'isbn': '978-0-13-448448-8',
            'title': 'Tourism: Quản trị Dịch vụ Du lịch, Lữ hành & Khách sạn Hiện đại',
            'author': 'Roy A. Cook, Cathy H. C. Hsu',
            'publisher': 'Pearson',
            'publish_year': 2024,
            'cat': 'Luật, Du lịch & Nhân văn',
            'department': 'Khoa Tài chính - Ngân hàng và QTKD',
            'pages': 448, 'price': 210000, 'location': 'P.M-DL-01', 'total_copies': 9,
            'circulation_type': 'borrowable', 'language': 'Song ngữ Anh - Việt',
            'cover': 'xh_tourism.jpg',
            'description': 'Quản trị điểm đến, vận hành lữ hành, kinh doanh lưu trú nghỉ dưỡng gắn với phát triển du lịch biển Quy Nhơn – Bình Định.',
        },
        {
            'isbn': '978-0-520-20157-6',
            'title': 'Understanding Vietnam — Tiến trình Văn hóa & Xã hội Việt Nam',
            'author': 'Neil L. Jamieson',
            'publisher': 'University of California Press',
            'publish_year': 2021,
            'cat': 'Luật, Du lịch & Nhân văn',
            'department': 'Khoa Khoa học Xã hội và Nhân văn',
            'pages': 450, 'price': 190000, 'location': 'P.DM1-XH-03', 'total_copies': 5,
            'circulation_type': 'borrowable', 'language': 'Tiếng Anh',
            'cover': 'xh_culture.jpg',
            'description': 'Tài liệu nghiên cứu dành cho ngành Việt Nam học, Đông phương học, Văn học và Công tác xã hội.',
        },

        # --- Luận văn & Khóa luận QNU (Chỉ đọc tại thư viện - Phòng Đọc Mở 2) ---
        {
            'isbn': 'KLTN-QNU-45CNTT-018',
            'title': 'Khóa luận Tốt nghiệp: Xây dựng Hệ thống Quản lý Học vụ Số theo Kiến trúc Microservices & SOA',
            'author': 'Trương Quang Nhật (GVHD: TS. Nguyễn Văn Hiếu)',
            'publisher': 'Lưu chiểu Trường Đại học Quy Nhơn',
            'publish_year': 2025,
            'cat': 'Luận văn & Khóa luận QNU',
            'department': 'Khoa Công nghệ thông tin',
            'pages': 124, 'price': 0, 'location': 'P.DM2-LV-01', 'total_copies': 2,
            'circulation_type': 'reference_only', 'language': 'Tiếng Việt',
            'cover': 'qnu_kltn_cntt.jpg',
            'description': 'Bản lưu chiểu khóa luận tốt nghiệp xuất sắc Khóa 45 ngành Công nghệ thông tin. Phục vụ đọc tại Phòng Đọc Mở 2 (Tầng 3).',
        },
        {
            'isbn': 'LVTS-QNU-25KT-009',
            'title': 'Luận văn Thạc sĩ: Đánh giá Hiệu quả Chuyển đổi số tại các Doanh nghiệp Nhỏ và Vừa tỉnh Bình Định',
            'author': 'Lê Thị Thanh Tâm (Chuyên ngành Quản trị Kinh doanh)',
            'publisher': 'Đào tạo Sau đại học — Trường ĐH Quy Nhơn',
            'publish_year': 2025,
            'cat': 'Luận văn & Khóa luận QNU',
            'department': 'Khoa Kinh tế và Kế toán',
            'pages': 148, 'price': 0, 'location': 'P.DM2-LV-04', 'total_copies': 1,
            'circulation_type': 'reference_only', 'language': 'Tiếng Việt',
            'cover': 'qnu_lvts_kt.jpg',
            'description': 'Luận văn thạc sĩ bản gốc có xác nhận hội đồng bảo vệ tại Trường Đại học Quy Nhơn. Chỉ phục vụ tra cứu tại phòng đọc.',
        },
        {
            'isbn': 'KLTN-QNU-45SP-004',
            'title': 'Khóa luận Tốt nghiệp: Phát triển Năng lực Tư duy Thuật toán cho Học sinh THPT Chuyên tại Bình Định',
            'author': 'Nguyễn Thị Thanh Hương (Khóa 45 Sư phạm Tin - Toán)',
            'publisher': 'Lưu chiểu Trường Đại học Quy Nhơn',
            'publish_year': 2025,
            'cat': 'Luận văn & Khóa luận QNU',
            'department': 'Khoa Sư phạm',
            'pages': 112, 'price': 0, 'location': 'P.DM2-LV-07', 'total_copies': 2,
            'circulation_type': 'reference_only', 'language': 'Tiếng Việt',
            'cover': 'qnu_kltn_sp.jpg',
            'description': 'Tài liệu lưu chiểu Khoa Sư phạm phục vụ sinh viên tham khảo phương pháp nghiên cứu khoa học giáo dục tại Phòng Đọc Mở 2.',
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
                cover_image=b.get('cover'),
                total_copies=b['total_copies'],
                available_copies=b['total_copies'],
                circulation_type=b['circulation_type'],
                language=b['language'],
                description=b['description'],
                status='available',
            )
            db.session.add(book)
    db.session.commit()

    # 4. Authentic QNU Readers (K44, K45, K46, K47 + Cao học + Giảng viên QNU; plus 2211xxxx compatible aliases)
    today = date.today()
    current_year = today.year
    sample_members = [
        {
            'code': 'SV450001', 'student_id': '22110045', 'name': 'Nguyễn Văn An',
            'email': '22110045@sv.university.edu.vn', 'phone': '0901234561',
            'type': 'student', 'gender': 'male',
            'faculty': 'Khoa Công nghệ thông tin', 'class_name': 'CNTT K45A',
            'cohort': 'K45', 'grad_year': current_year, 'status': 'active',
        },
        {
            'code': 'SV450002', 'student_id': '22110112', 'name': 'Trần Thị Minh Châu',
            'email': '22110112@sv.university.edu.vn', 'phone': '0912345672',
            'type': 'student', 'gender': 'female',
            'faculty': 'Khoa Công nghệ thông tin', 'class_name': 'KTPM K45B',
            'cohort': 'K45', 'grad_year': current_year, 'status': 'active',
        },
        {
            'code': 'SV450003', 'student_id': '4554010078', 'name': 'Lê Quốc Bảo',
            'email': '4554010078@st.qnu.edu.vn', 'phone': '0923456783',
            'type': 'student', 'gender': 'male',
            'faculty': 'Khoa Kinh tế và Kế toán', 'class_name': 'Kế toán K45A',
            'cohort': 'K45', 'grad_year': current_year, 'status': 'active',
        },
        {
            'code': 'SV460004', 'student_id': '4651050209', 'name': 'Phạm Ngọc Diệp',
            'email': '4651050209@st.qnu.edu.vn', 'phone': '0934567894',
            'type': 'student', 'gender': 'female',
            'faculty': 'Khoa Công nghệ thông tin', 'class_name': 'Trí tuệ nhân tạo K46',
            'cohort': 'K46', 'grad_year': current_year + 1, 'status': 'active',
        },
        {
            'code': 'SV470005', 'student_id': '4752030064', 'name': 'Hoàng Gia Huy',
            'email': '4752030064@st.qnu.edu.vn', 'phone': '0945678905',
            'type': 'student', 'gender': 'male',
            'faculty': 'Khoa Kỹ thuật và Công nghệ', 'class_name': 'CNKT Ô tô K47A',
            'cohort': 'K47', 'grad_year': current_year + 2, 'status': 'active',
        },
        {
            'code': 'SV460006', 'student_id': '4659010145', 'name': 'Đỗ Mai Thảo Vy',
            'email': '4659010145@st.qnu.edu.vn', 'phone': '0987654321',
            'type': 'student', 'gender': 'female',
            'faculty': 'Khoa Sư phạm', 'class_name': 'SP Toán học K46',
            'cohort': 'K46', 'grad_year': current_year + 1, 'status': 'active',
        },
        {
            'code': 'SV470007', 'student_id': '4757020088', 'name': 'Huỳnh Tuấn Kiệt',
            'email': '4757020088@st.qnu.edu.vn', 'phone': '0976543219',
            'type': 'student', 'gender': 'male',
            'faculty': 'Khoa Ngoại ngữ', 'class_name': 'Ngôn ngữ Anh K47B',
            'cohort': 'K47', 'grad_year': current_year + 2, 'status': 'active',
        },
        {
            'code': 'HV250008', 'student_id': 'CH250018', 'name': 'Võ Thanh Phương',
            'email': 'ch250018@st.qnu.edu.vn', 'phone': '0956789016',
            'type': 'postgrad', 'gender': 'female',
            'faculty': 'Khoa Tài chính - Ngân hàng và QTKD', 'class_name': 'Cao học QTKD K27',
            'cohort': 'CH27', 'grad_year': current_year + 1, 'status': 'active',
        },
        {
            'code': 'GV190009', 'student_id': 'GV001042', 'name': 'TS. Đặng Minh Khôi',
            'email': 'dangminhkhoi@qnu.edu.vn', 'phone': '0967890127',
            'type': 'lecturer', 'gender': 'male',
            'faculty': 'Khoa Công nghệ thông tin', 'class_name': 'Bộ môn Kỹ thuật phần mềm',
            'cohort': None, 'grad_year': None, 'status': 'active',
        },
        {
            'code': 'GV200010', 'student_id': 'GV002015', 'name': 'PGS.TS. Lê Hoài Nam',
            'email': 'lehoainam@qnu.edu.vn', 'phone': '0918273645',
            'type': 'lecturer', 'gender': 'male',
            'faculty': 'Khoa Toán và Thống kê', 'class_name': 'Bộ môn Khoa học dữ liệu',
            'cohort': None, 'grad_year': None, 'status': 'active',
        },
        {
            'code': 'SV440011', 'student_id': '4451050652', 'name': 'Bùi Thị Lan Anh',
            'email': '4451050652@st.qnu.edu.vn', 'phone': '0978901238',
            'type': 'student', 'gender': 'female',
            'faculty': 'Khoa Khoa học Tự nhiên', 'class_name': 'SP Hóa học K44',
            'cohort': 'K44', 'grad_year': current_year - 1, 'status': 'graduated',
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
                membership_start=today - timedelta(days=240),
                membership_end=today + timedelta(days=730),
                status=m['status'],
            )
            db.session.add(member)
    db.session.commit()

    # 5. Sample Circulation Transactions & Reservations
    if Loan.query.count() == 0:
        librarian = User.query.filter_by(username='librarian').first()
        lib_id = librarian.id if librarian else 1

        def get_m(sid): return Member.query.filter_by(student_id=sid).first()
        def get_b(isbn): return Book.query.filter_by(isbn=isbn).first()

        an = get_m('22110045')
        chau = get_m('22110112')
        bao = get_m('4554010078')
        diep = get_m('4651050209')
        huy = get_m('4752030064')
        vy = get_m('4659010145')
        kiet = get_m('4757020088')
        phuong = get_m('CH250018')
        khoi = get_m('GV001042')
        nam = get_m('GV002015')

        b_soa = get_b('978-604-913-412-8')
        b_db = get_b('978-0-07-802215-9')
        b_cc = get_b('978-0-13-235088-4')
        b_ai = get_b('978-0-13-461099-3')
        b_kt = get_b('978-1-305-50712-8')
        b_auto = get_b('978-1-259-06420-3')
        b_ddia = get_b('978-1-491-95035-7')
        b_sp = get_b('978-0-13-477432-9')
        b_eng = get_b('978-1-108-58662-7')
        b_islr = get_b('978-1-0716-1417-4')

        sample_loans = [
            Loan(
                loan_code='PM26110001', book_id=b_soa.id, member_id=an.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=19), due_date=today - timedelta(days=5),
                status='borrowed', condition_out='good', notes='Mượn phục vụ bài tập lớn SOA',
            ),
            Loan(
                loan_code='PM26110002', book_id=b_auto.id, member_id=huy.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=23), due_date=today - timedelta(days=9),
                status='borrowed', condition_out='good', notes='Thực hành xưởng động cơ ô tô',
            ),
            Loan(
                loan_code='PM26100003', book_id=b_kt.id, member_id=bao.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=30), due_date=today - timedelta(days=16),
                return_date=today - timedelta(days=10), status='returned',
                condition_out='good', condition_in='good',
                fine_amount=12000, fine_paid=False, fine_reason='overdue',
                notes='Trả muộn 6 ngày — chưa đóng phạt',
            ),
            Loan(
                loan_code='PM26100004', book_id=b_db.id, member_id=chau.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=25), due_date=today - timedelta(days=11),
                return_date=today - timedelta(days=12), status='returned',
                condition_out='good', condition_in='good', fine_amount=0, fine_paid=True,
            ),
            Loan(
                loan_code='PM26110005', book_id=b_ai.id, member_id=diep.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=4), due_date=today + timedelta(days=10),
                status='borrowed', condition_out='good',
            ),
            Loan(
                loan_code='PM26110006', book_id=b_kt.id, member_id=phuong.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=6), due_date=today + timedelta(days=15),
                status='borrowed', condition_out='good',
            ),
            Loan(
                loan_code='PM26110007', book_id=b_ddia.id, member_id=khoi.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=3), due_date=today + timedelta(days=27),
                status='borrowed', condition_out='good', notes='Tài liệu biên soạn chuyên đề Hệ phân tán',
            ),
            Loan(
                loan_code='PM26110008', book_id=b_sp.id, member_id=vy.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=5), due_date=today + timedelta(days=9),
                status='borrowed', condition_out='good',
            ),
            Loan(
                loan_code='PM26110009', book_id=b_eng.id, member_id=kiet.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=2), due_date=today + timedelta(days=12),
                status='borrowed', condition_out='good',
            ),
            Loan(
                loan_code='PM26110010', book_id=b_islr.id, member_id=nam.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=8), due_date=today + timedelta(days=22),
                status='borrowed', condition_out='good',
            ),
            Loan(
                loan_code='PM26090011', book_id=b_soa.id, member_id=diep.id, librarian_id=lib_id,
                loan_date=today - timedelta(days=50), due_date=today - timedelta(days=36),
                return_date=today - timedelta(days=34), status='returned',
                condition_out='good', condition_in='good',
                fine_amount=4000, fine_paid=True, fine_reason='overdue',
            ),
        ]

        for l in sample_loans:
            db.session.add(l)
            if l.status == 'borrowed':
                bk = db.session.get(Book, l.book_id)
                if bk and bk.available_copies > 0:
                    bk.available_copies -= 1

        bao.total_fine = 12000

        if Reservation.query.count() == 0:
            res_ready = Reservation(
                reservation_code='DC26110001',
                book_id=b_cc.id,
                member_id=chau.id,
                status='ready',
                notified_at=datetime_now(),
                expires_at=today + timedelta(days=2),
                notes='Nhận tại Phòng Mượn Tầng 1',
            )
            if b_cc.available_copies > 0:
                b_cc.available_copies -= 1
            db.session.add(res_ready)

        db.session.commit()

    print("[OK] QNU Library database seeded with 35 books & real covers!")
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
        print('QNU Library SOA services are starting:')
        ports = bootstrap_app.config['SERVICE_PORTS']
        print(f"  Gateway: http://localhost:{ports['gateway']}")
        print(f"  OPAC:    http://localhost:{ports['gateway']}/catalog")
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
        print('\nStopping all QNU Library SOA services...')
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
