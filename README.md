# Hệ thống Quản lý Thư viện Trường Đại học — Kiến trúc SOA

Hệ thống quản lý lưu thông tài liệu nội bộ **Thư viện Trường Đại học** được xây dựng theo **Kiến trúc Hướng Dịch vụ (SOA)** với một **API Gateway** và **4 dịch vụ miền độc lập** có thể khởi chạy riêng tiến trình.

---

## 1. Mục đích & Phạm vi bài toán (Scope)

- **Phạm vi khoanh vùng:** Thư viện **Trường Đại học** — chỉ phục vụ nội bộ **Sinh viên đại học, Học viên cao học và Giảng viên / Cán bộ** của nhà trường (không xây dựng chung chung cho thư viện công cộng hay cửa hàng bán sách).
- **Mô hình hoạt động:** **Miễn phí khuyến khích đọc** (phí làm thẻ 0₫, phí mượn sách 0₫). Hệ thống chỉ thu **phí chế tài** khi trả muộn hoặc làm mất tài liệu nhằm đảm bảo công bằng xoay vòng giáo trình.
- **Điều kiện tham gia:** Bắt buộc đăng ký bằng **Mã số sinh viên (MSSV)** hoặc **Mã cán bộ (MCB)** gắn với Khoa, Lớp và Năm dự kiến tốt nghiệp.

## 2. Mục đích từng chức năng & Quy tắc nghiệp vụ (Business Rules)

| Chức năng | Mục đích nghiệp vụ | Quy tắc nghiệp vụ áp dụng trong code |
|---|---|---|
| **Quản lý Tài liệu** | Kiểm soát kho giáo trình, vị trí kệ, số bản sao và tách biệt tài liệu cho mượn với bản lưu chiểu | Phân loại `Cho mượn về` vs `Chỉ đọc tại chỗ` (Luận văn/Đồ án bị chặn mượn về); giá bìa là căn cứ đền bù 100% khi mất sách; không xóa sách đang có người mượn |
| **Quản lý Độc giả & Ra trường** | Xác thực đúng người học/giảng viên nội bộ và đảm bảo thu hồi đủ tài sản trường trước khi tốt nghiệp | Bắt buộc MSSV/MCB duy nhất; hạn mức **SV: 5 cuốn/14 ngày**, **Cao học: 7 cuốn/21 ngày**, **GV: 10 cuốn/30 ngày**; chỉ **Xác nhận ra trường** khi `0 sách đang mượn` và `0₫ nợ phạt` |
| **Lưu thông Mượn – Trả & Phạt** | Duy trì vòng quay giáo trình đúng hạn giữa các khóa sinh viên | Tự động **chặn mượn mới** khi có sách quá hạn hoặc nợ phạt; gia hạn tối đa 2 lần (chặn khi đã quá hạn); phạt trễ hạn **2.000₫/ngày**; hỗ trợ thanh toán phạt mở khóa quyền mượn |
| **Thống kê & Cảnh báo** | Hỗ trợ thủ thư và nhà trường bổ sung sách theo nhu cầu khoa và đôn đốc thu hồi sách | Thống kê lượt mượn 12 tháng, theo Khoa, top sách; cảnh báo quá hạn & sinh viên khóa tốt nghiệp đang bị chặn ra trường |

## 3. Phân rã Dịch vụ SOA (Service Design)

```text
Browser ──> API Gateway :5000 ──(Service JWT / HTTP)──> Books Service   :5001
                              ├───────────────────────> Members Service :5002
                              ├───────────────────────> Loans Service   :5003
                              └───────────────────────> Reports Service :5004
```

| Dịch vụ | Cổng | Trách nhiệm & Endpoint tiêu biểu |
|---|---:|---|
| **API Gateway + Web UI** | `5000` | Xác thực phiên/JWT, định tuyến `/api/v1/*`, giao diện nghiệp vụ thủ thư |
| **Books Service** | `5001` | `/api/v1/books/*` — Kho tài liệu, thể loại/ngành, quy chế lưu thông |
| **Members Service** | `5002` | `/api/v1/members/*`, `/api/v1/members/clearance`, `POST /api/v1/members/<id>/clearance` |
| **Loans Service** | `5003` | `/api/v1/loans/*`, `POST /<id>/return`, `POST /<id>/pay-fine`, `POST /<id>/renew`, `POST /<id>/lost` |
| **Reports Service** | `5004` | `/api/v1/reports/dashboard`, `/overdue`, `/faculty-loans`, `/alerts` |

---

## Cách khởi chạy

### 1. Khởi tạo lại dữ liệu mẫu Thư viện Đại học
```powershell
venv\Scripts\python.exe run.py reset-seed
```

### 2. Chạy toàn bộ hệ thống SOA (Gateway + 4 Services)
```powershell
venv\Scripts\python.exe run.py all
```
Truy cập **http://localhost:5000**.

### Tài khoản demo
| Tài khoản | Mật khẩu | Vai trò |
|---|---|---|
| `admin` | `Admin@123` | Quản trị hệ thống |
| `librarian` | `Lib@123` | Cán bộ thủ thư |
