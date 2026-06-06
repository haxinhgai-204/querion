# Hướng dẫn Khởi động / Dừng Querion

> Tài liệu này hướng dẫn cách **start** và **stop** toàn bộ hệ thống Querion trên Windows bằng script tự động.

---

## Yêu cầu trước khi bắt đầu

Đảm bảo bạn đã hoàn thành [Setup ban đầu](./SETUP_WINDOWS.md) (cài Docker, Python, Node.js, clone code, cài dependencies).

---

## Khởi động (Start)

### Cách 1: Dùng terminal (khuyến nghị)

Mở PowerShell hoặc Terminal trong VS Code, di chuyển đến thư mục gốc project:

```powershell
.\start.ps1
```

### Cách 2: Double-click

Mở File Explorer, vào thư mục gốc project, **double-click** file `start.bat`.

### Script sẽ tự động thực hiện

| Bước | Mô tả | Thời gian |
|------|-------|-----------|
| 1 | Khởi động Docker containers (PostgreSQL, Redis, MinIO) | 5-10 giây |
| 2 | Chờ PostgreSQL sẵn sàng | 5-30 giây |
| 3 | Khởi động API server trên port **8000** | 2-3 giây |
| 4 | Khởi động Web frontend trên port **3000** | 2-3 giây |
| 5 | Khởi động Worker (xử lý background jobs) | 1-2 giây |

### Kết quả mong đợi

```
========================================
   All services are running!
========================================

  Web UI:      http://localhost:3000
  API Docs:    http://localhost:8000/docs
  MinIO:       http://localhost:9001

  Admin login: admin@querion.io / admin123

  Press Ctrl+C to stop all services.
```

### Kiểm tra

Mở browser và truy cập:

| URL | Mô tả |
|-----|-------|
| http://localhost:3000 | Giao diện Web chính |
| http://localhost:8000/docs | Tài liệu API (Swagger) |
| http://localhost:9001 | Quản lý file MinIO |

### Tài khoản đăng nhập

| Dịch vụ | Username / Email | Password |
|---------|-----------------|----------|
| Web Admin | `admin@querion.io` | `admin123` |
| MinIO Console | `minioadmin` | `minioadmin_secret` |

---

## Dừng (Stop)

### Cách 1: Nhấn Ctrl+C

Nếu `start.ps1` đang chạy trong terminal, nhấn **Ctrl+C**. Script sẽ tự động tắt API, Web, và Worker.

> **Lưu ý**: Docker containers vẫn chạy sau khi Ctrl+C. Điều này giúp việc start lại nhanh hơn.

### Cách 2: Dùng script stop

Mở terminal **mới** và chạy:

```powershell
.\stop.ps1
```

Hoặc **double-click** file `stop.bat`.

Script sẽ:
1. Tắt API server (port 8000)
2. Tắt Web frontend (port 3000) 
3. Tắt Worker
4. **Hỏi** bạn có muốn tắt Docker containers không

```
  Stop Docker containers too? (y/N):
```

- Nhấn **Enter** hoặc **N** → giữ Docker chạy (khuyến nghị, start lại nhanh hơn)
- Nhấn **Y** → tắt luôn Docker (cần khi muốn giải phóng RAM hoặc tắt máy)

---

## Các tình huống thường gặp

### Muốn restart nhanh (không tắt Docker)

```powershell
# Chỉ cần chạy start lại - script sẽ tự kill process cũ và start mới
.\start.ps1
```

### Muốn tắt hoàn toàn (cuối ngày / tắt máy)

```powershell
.\stop.ps1
# Chọn Y khi hỏi "Stop Docker containers too?"
```

### Web UI bị lỗi ERR_CONNECTION_REFUSED

Chạy `stop.ps1` (chọn **N** cho Docker), rồi chạy lại `start.ps1`:

```powershell
.\stop.ps1
# Chọn N (giữ Docker)
.\start.ps1
```

### Port bị chiếm bởi process cũ

Script `start.ps1` đã tự động xử lý — nó sẽ kill process cũ trên port trước khi start mới. Không cần làm gì thêm.

### Docker Desktop chưa mở

Nếu thấy lỗi liên quan Docker, mở **Docker Desktop** từ Start Menu, đợi icon cá voi ở taskbar chuyển xanh, rồi chạy lại `start.ps1`.

---

## Tóm tắt lệnh

| Hành động | Lệnh |
|-----------|------|
| **Start tất cả** | `.\start.ps1` hoặc double-click `start.bat` |
| **Stop tất cả** | `.\stop.ps1` hoặc double-click `stop.bat` |
| **Restart nhanh** | `.\start.ps1` (tự kill cũ + start mới) |
| **Stop chỉ Docker** | `cd infra\docker; docker compose down` |
| **Start chỉ Docker** | `cd infra\docker; docker compose up -d` |
