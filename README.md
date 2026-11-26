# Hệ thống Quản lý Thư viện Trường Đại học Quy Nhơn (QNU Library — Kiến trúc SOA)

Hệ thống quản lý danh mục học thuật, lưu thông tài liệu, đặt giữ chỗ trực tuyến (OPAC) và thanh lý thẻ ra trường dành riêng cho **Thư viện – Trung tâm Số và Học liệu, Trường Đại học Quy Nhơn (170 An Dương Vương, TP. Quy Nhơn)**, triển khai theo **Kiến trúc Hướng Dịch vụ (SOA)** gồm **API Gateway** và **4 dịch vụ miền độc lập**.

---

## Quy trình Phân tích & Thiết kế Dịch vụ (Service Design)

### Bước 1. Xác định Mục đích & Khoanh vùng Phạm vi (Scope)
- **Đối tượng & Phạm vi:** Khoanh vùng trực tiếp cho **Thư viện Trường Đại học Quy Nhơn (QNU)** tại Tòa nhà Thư viện 15 tầng (*Phòng Giáo trình Tầng 1, Phòng Mượn Tầng 1, Phòng Đọc Mở 1 Tầng 2, Phòng Đọc Mở 2 Tầng 3*) — phục vụ nội bộ **Sinh viên chính quy (K44–K47), Học viên cao học và Giảng viên / Cán bộ** thuộc các khoa đào tạo của QNU.
- **Mô hình hoạt động:** **Miễn phí khuyến khích đọc và nghiên cứu** (0₫ phí cấp thẻ, 0₫ phí mượn giáo trình). Hệ thống chỉ hạch toán **tiền phạt / đền bù** (trả muộn, làm hư hỏng nặng hoặc làm mất sách) để bảo toàn tài sản công và duy trì vòng quay học liệu công bằng giữa các khóa.
- **Điều kiện tham gia:** Định danh bắt buộc bằng **Mã sinh viên QNU (VD: `455105xxxx`, `465105xxxx`)** hoặc **Mã cán bộ** gắn với Khoa chuyên môn, Lớp và Khóa đào tạo.

### Bước 2. Mục đích từng Chức năng & Quy tắc Nghiệp vụ (Business Rules)

| Phân hệ chức năng | Bản chất & Mục đích nghiệp vụ | Quy tắc & Ràng buộc thực thi trong code |
|---|---|---|
| **1. Quản lý Danh mục & Cổng OPAC** | Kiểm soát chính xác vị trí kệ, số lượng bản sao và giúp sinh viên tự tra cứu kho sách mọi lúc | • Phân tách `Mượn về nhà` và `Đọc tại chỗ` (Luận văn/khóa luận lưu chiểu bị chặn mượn về).<br>• Đảm bảo bất biến tồn kho: `Tổng bản = Sẵn trên kệ + Đang mượn + Đang giữ tại quầy`; chặn giảm tổng bản thấp hơn số bản đang lưu thông.<br>• Chặn xóa cứng đầu sách đã phát sinh lịch sử lưu thông để bảo toàn sổ đối chiếu. |
| **2. Quản lý Độc giả & Xét Tốt nghiệp** | Xác thực tư cách thành viên nhà trường và thu hồi triệt để tài sản trường trước khi sinh viên ra trường | • Bắt buộc MSSV/MCB và Email hợp lệ.<br>• Định mức theo nhóm thẻ: **Sinh viên** (5 cuốn / 14 ngày / thẻ 4 năm), **Cao học** (7 cuốn / 21 ngày / thẻ 2 năm), **Giảng viên** (10 cuốn / 30 ngày / thẻ 5 năm).<br>• **Đối soát tốt nghiệp** (chỉ áp dụng SV/HV): Chỉ cấp xác nhận khi đồng thời `0 sách đang giữ` và `0₫ công nợ phí`. |
| **3. Lưu thông, Đặt giữ chỗ & Chế tài** | Duy trì luân chuyển giáo trình đúng hạn, ưu tiên người xếp hàng chờ và xử lý tự động các vi phạm | • **Chặn mượn mới / gia hạn** khi thẻ hết hạn, có sách quá hạn hoặc còn nợ phí.<br>• **Hàng đợi Đặt giữ chỗ (Hold Queue):** Giữ bản sẵn tại quầy 3 ngày hoặc xếp hàng FIFO khi hết sách; tự động chuyển bản vừa trả cho người chờ đầu tiên; chặn gia hạn nếu sách đang có người đặt chờ.<br>• **Tự động tính phí:** Trễ hạn `2.000₫/ngày`; hư hỏng nặng `30% giá bìa` (tối thiểu `20.000₫`); làm mất `100% giá bìa + phí quá hạn` và trừ tồn kho. |
| **4. Thống kê, Phân tích & Cảnh báo** | Cung cấp căn cứ dữ liệu để bổ sung giáo trình cho các khoa có nhu cầu cao và đôn đốc thu hồi nợ | • Biểu đồ lưu thông 12 tháng, tỷ trọng chuyên ngành, thống kê theo Khoa/Viện, xuất báo cáo CSV.<br>• Cảnh báo tự động: phiếu quá hạn, sách đến hạn hôm nay, sách giữ tại quầy chờ nhận, sinh viên khóa tốt nghiệp đang vướng nghĩa vụ. |

### Bước 3. Phân rã Dịch vụ SOA (Service Decomposition)

```text
Browser (Staff UI & Public OPAC)
        │
        ▼
  API Gateway (:5000) ──[HS256 Service JWT]──► Books Service   (:5001)  /api/v1/books/*
                      ├──[HS256 Service JWT]──► Members Service (:5002)  /api/v1/members/*
                      ├──[HS256 Service JWT]──► Loans Service   (:5003)  /api/v1/loans/*
                      └──[HS256 Service JWT]──► Reports Service (:5004)  /api/v1/reports/*
```

---

## Hướng dẫn Khởi chạy

### 1. Khởi tạo cơ sở dữ liệu mẫu
```powershell
venv\Scripts\python.exe run.py reset-seed
```

### 2. Khởi chạy toàn bộ hệ thống SOA (Gateway + 4 Services)
```powershell
venv\Scripts\python.exe run.py all
```

- **Quầy nghiệp vụ thủ thư:** http://localhost:5000/login
- **Cổng tra cứu OPAC (Sinh viên / Giảng viên):** http://localhost:5000/catalog

### Tài khoản thử nghiệm (Môi trường phát triển)
| Tài khoản | Mật khẩu | Phân quyền |
|---|---|---|
| `admin` | `Admin@123` | Quản trị hệ thống |
| `librarian` | `Lib@123` | Cán bộ lưu thông |
