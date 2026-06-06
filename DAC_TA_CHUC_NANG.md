# ĐẶC TẢ CHỨC NĂNG HỆ THỐNG - QUERION PROJECT

> **Querion (Mini-Dify):** Nền tảng xây dựng ứng dụng AI hỗ trợ quản lý tri thức đa không gian làm việc (multi-workspace datasets), thiết kế luồng xử lý (workflow canvas), và cổng thông tin hội thoại thời gian thực (SSE streaming chat) tích hợp nguồn trích dẫn tài liệu (citations).

---

## 1. TỔNG QUAN HỆ THỐNG & KIẾN TRÚC CÔNG NGHỆ

Hệ thống Querion được thiết kế theo kiến trúc Microservices tinh gọn kết hợp xử lý bất đồng bộ (Asynchronous Background Processing) để tối ưu hiệu năng và khả năng mở rộng:

- **Frontend (Web):** Xây dựng bằng **Next.js 16**, **React 19**, **TypeScript**, và **Tailwind CSS v4**. Sử dụng **@xyflow/react** (React Flow) để dựng Canvas thiết kế workflow.
- **Backend (API):** Sử dụng **FastAPI (Python)** hỗ trợ lập trình bất đồng bộ (async/await) và kết nối thời gian thực qua giao thức Server-Sent Events (SSE).
- **Background Worker:** Tiến trình chạy ngầm xử lý bất đồng bộ sử dụng **Python RQ (Redis Queue)** để bóc tách, phân mảnh và nhúng (embedding) tài liệu dung lượng lớn.
- **Cơ sở dữ liệu (Database):** 
  - **PostgreSQL 16 + pgvector:** Lưu trữ dữ liệu quan hệ và cơ sở dữ liệu không gian vector ngữ nghĩa. Hỗ trợ thuật toán tìm kiếm lân cận gần nhất xấp xỉ **HNSW (Hierarchical Navigable Small World)** cho kết quả truy vấn ngữ nghĩa dưới 50ms.
  - **Redis:** Làm bộ nhớ đệm (Caching) và hàng đợi công việc (Task Queue) cho Worker.
  - **MinIO:** Lưu trữ đối tượng (S3-compatible Object Storage) để chứa tài liệu tải lên (PDF, DOCX, TXT...).

---

## 2. CHỨC NĂNG PHÂN QUYỀN & QUẢN LÝ ĐA KHÔNG GIAN (MULTI-TENANCY RBAC)

Hệ thống đảm bảo tính cách ly tuyệt đối về mặt dữ liệu giữa các không gian làm việc (Workspace/Tenant) thông qua cơ chế kiểm soát truy cập dựa trên vai trò (RBAC) 2 lớp:

### 2.1 Vai trò cấp Hệ thống (System Roles)
1. **Super Admin (Quản trị tối cao):**
   - Tài khoản mặc định được khởi tạo tự động khi deploy hệ thống (`admin@querion.io` / `admin123`).
   - Có quyền cấu hình và quản trị toàn bộ hệ thống, quản lý tất cả các Workspace.
   - Quản lý danh sách người dùng (Admin) và phân bổ quyền vào các Workspace.
   - Xem và giám sát tất cả các dữ liệu xuyên suốt các không gian làm việc.
2. **Admin (Quản trị viên):**
   - Được tạo bởi Super Admin.
   - Có quyền làm việc trong các Workspace được chỉ định với các vai trò tương ứng trong Workspace đó.
3. **Student (Sinh viên / Người dùng cuối):**
   - Tài khoản được quản trị viên import hoặc tạo thủ công.
   - Chỉ truy cập vào cổng giao diện dành riêng cho sinh viên (Student Portal).
   - Chỉ được tương tác với các ứng dụng (Apps) đã được xuất bản (Published).

### 2.2 Vai trò cấp Không gian làm việc (Workspace Roles)
Một Admin khi tham gia vào một Workspace cụ thể sẽ nhận một trong ba vai trò sau:
- **Owner (Chủ sở hữu):** Có toàn quyền kiểm soát Workspace, có quyền thêm/bớt thành viên và phân bổ quyền thành viên trong Workspace của mình. Có quyền xóa Workspace và các tài nguyên liên quan.
- **Editor (Biên tập viên):** Có quyền tạo mới, chỉnh sửa và xóa (CRUD) các tài nguyên của Workspace bao gồm Datasets, Documents, Workflows, Apps. Không có quyền quản lý thành viên.
- **Viewer (Người xem):** Chỉ có quyền xem tài nguyên, thực hiện truy vấn chat thử nghiệm, không có quyền chỉnh sửa hay xóa bất cứ tài nguyên nào.

### 2.3 Bộ chuyển đổi Không gian làm việc (Workspace Switcher)
- Cho phép người dùng Admin chuyển đổi nhanh chóng giữa các Workspace mà họ tham gia thông qua thanh điều hướng trên cùng (Topbar).
- Mỗi API request từ Client sẽ đính kèm Header `X-Workspace-Id` để đảm bảo hệ thống chỉ truy xuất đúng dữ liệu thuộc không gian làm việc hiện hành.

---

## 3. QUẢN LÝ TRI THỨC & TIẾN TRÌNH XỬ LÝ TÀI LIỆU (DATASETS & RAG PIPELINE)

Querion xây dựng một hệ thống RAG (Retrieval-Augmented Generation) hoàn chỉnh giúp đưa các tài liệu chuyên ngành của tổ chức vào làm ngữ cảnh trả lời cho AI.

### 3.1 Quản lý Dataset
- Cho phép tạo mới, cập nhật tên và mô tả của Dataset.
- Danh sách Dataset hiển thị số lượng tài liệu (Documents) và tổng số phân mảnh (Chunks) hiện có.
- Cơ chế ngăn chặn xóa Dataset: Hệ thống hiển thị cảnh báo và yêu cầu xác nhận rõ ràng nếu Dataset đang được liên kết với một Ứng dụng (App) hoặc Luồng công việc (Workflow) đang hoạt động.

### 3.2 Quản lý Tài liệu (Documents)
- Hỗ trợ tải lên (Upload) nhiều tài liệu định dạng khác nhau: **PDF, DOCX, TXT, MD**.
- Quản lý trạng thái xử lý tài liệu thông qua State Machine:
  - `uploaded`: Tài liệu đã tải lên lưu trữ MinIO thành công.
  - `indexing`: Đang trong hàng đợi xử lý phân tách chữ và tạo vector nhúng.
  - `ready`: Hoàn thành xử lý, tài liệu đã sẵn sàng truy vấn.
  - `failed`: Xử lý lỗi (lỗi định dạng file, lỗi kết nối API nhúng...).
- Cho phép xem trước danh sách các phân mảnh chữ (Chunk Preview) sau khi xử lý thành công.

### 3.3 Tiến trình xử lý ngầm (Worker Indexing Pipeline)
Khi người dùng bấm nút kích hoạt Index tài liệu, một Task sẽ được đẩy vào Redis Queue để Background Worker xử lý:
1. **Trích xuất văn bản (Text Extraction):** Worker tải file nhị phân từ MinIO và sử dụng các thư viện như `PyMuPDF`, `python-docx` để chuyển đổi sang văn bản thô (Plain Text).
2. **Phân tách đoạn văn (Text Chunking):** Áp dụng thuật toán chia nhỏ văn bản với cấu hình chuẩn:
   - **Chunk Size (Kích thước phân mảnh):** Khoảng 1000 ký tự.
   - **Overlap (Đoạn gối đầu):** 200 ký tự (giúp đảm bảo tính toàn vẹn ngữ nghĩa của các câu nằm sát biên phân đoạn).
3. **Nhúng Vector (Embedding):** Gọi API nhúng (ví dụ: `text-embedding-3-small` của OpenAI/OpenRouter) để biến mỗi Chunk văn bản thành một Vector 1536 chiều đại diện cho ý nghĩa ngữ nghĩa.
4. **Lưu trữ CSDL Vector:** Thực hiện thao tác chèn hàng loạt (Bulk Insert) các Vector vào bảng `embeddings` trong PostgreSQL sử dụng extension `pgvector`. Thiết lập cấu trúc chỉ mục **HNSW** cho cột vector để tối ưu hóa tốc độ tìm kiếm lân cận.

---

## 4. TRÌNH THIẾT KẾ ĐỒ THỊ LUỒNG CÔNG VIỆC (WORKFLOW CANVAS BUILDER)

Cho phép xây dựng các ứng dụng AI linh hoạt theo kiến trúc đồ thị có hướng phi chu trình (DAG) thay vì các chuỗi bước tuyến tính thông thường.

```
       [ Input Node ]
             │
             ▼
     [ Retrieve Node ] ──(context)──┐
             │                      │
             ▼                      ▼
      [ If/Else Node ] ──► [ Compose Prompt ]
             │                      │
             ▼                      ▼
    [ HTTP Request ] ──► [ LLM Generate ]
                                    │
                                    ▼
                             [ Output Node ]
```

### 4.1 Giao diện vẽ đồ thị (Canvas UI)
- Trình kéo thả trực quan được xây dựng trên **React Flow**.
- Hỗ trợ các tính năng tương tác: Phóng to/Thu nhỏ (Zoom), dịch chuyển Canvas (Pan), tự động căn chỉnh (Auto-layout), kết nối các đầu nút (Edges) bằng dây cáp kéo thả.
- Panel cài đặt thuộc tính (Properties Panel) xuất hiện bên phải màn hình khi click chọn một Node bất kỳ để cấu hình các biến đầu vào, đầu ra, Prompt, API Key...
- Trình kiểm tra tính hợp lệ của luồng (Workflow Validator):
  - Kiểm tra đồ thị có tồn tại chu trình lặp vô hạn hay không (phải là DAG).
  - Đảm bảo có đúng **1 nút Input** và ít nhất **1 nút Output / Answer**.
  - Kiểm tra các liên kết đầu vào/đầu ra của từng nút đã đầy đủ biến hay chưa.

### 4.2 Các loại nút hỗ trợ (Supported Nodes)
- **Input (Đầu vào):** Điểm tiếp nhận truy vấn của người dùng và các biến ngữ cảnh ban đầu (ví dụ: `query`, `history`).
- **Retrieve (Truy xuất):** Tìm kiếm ngữ nghĩa tương đồng (Semantic Search) trên CSDL Vector của các Dataset được chọn, trả về danh sách các phân mảnh văn bản phù hợp nhất kèm điểm số tin cậy (similarity score).
- **Compose Prompt (Soạn Prompt):** Cho phép biên soạn Prompt template động sử dụng cú pháp biến Jinja2 (ví dụ: `{{query}}`, `{{context}}`).
- **LLM Generate (Gọi mô hình):** Gửi Prompt đã dựng tới các nhà cung cấp AI lớn (OpenAI, Anthropic, Gemini, OpenRouter) để sinh văn bản phản hồi.
- **Parameter Extract (Trích xuất tham số):** Sử dụng LLM để phân tích cú pháp ngôn ngữ tự nhiên của người dùng và trích xuất ra các tham số có cấu trúc (ví dụ: trích xuất Tên, Mã số sinh viên - MSSV...).
- **If-Else (Rẽ nhánh điều kiện):** Rẽ nhánh luồng dựa vào giá trị của các biến trong trạng thái (State).
- **HTTP Request (Gọi API ngoại vi):** Gửi yêu cầu HTTP (GET, POST...) đến các dịch vụ bên ngoài, cho phép truyền tham số động từ State và lưu kết quả trả về vào State để các nút sau sử dụng (ví dụ: ghi kết quả khảo sát lên Google Sheets).
- **Code Execute (Thực thi mã nguồn):** Sandbox chạy mã Python tự định nghĩa để xử lý hoặc làm sạch dữ liệu phức tạp.
- **Answer / Output (Đầu ra):** Định nghĩa nội dung phản hồi cuối cùng gửi trả về giao diện chat của người dùng.

### 4.3 Trình chạy đồ thị (Workflow Runtime Engine)
- Dựa trên tư duy quản lý trạng thái của **LangGraph**, hệ thống duy trì một đối tượng trạng thái (Graph State) đi qua các nút.
- Trình chạy sẽ phân tích cấu trúc đồ thị JSON, kích hoạt tuần tự các hàm xử lý Python tương ứng của từng node, cập nhật các biến đầu ra vào State và thực hiện rẽ nhánh theo các Cạnh kết nối (Edges).

---

## 5. QUẢN LÝ ỨNG DỤNG & ĐO LƯỜNG HIỆU NĂNG (APPS & OBSERVABILITY)

Giúp liên kết các cấu hình nghiệp vụ và Workflow thành các ứng dụng hoàn chỉnh để phân phối tới người dùng cuối.

### 5.1 Quản lý Ứng dụng (Apps)
- Hỗ trợ ba loại ứng dụng cốt lõi:
  1. **Pure Chat App:** Ứng dụng hội thoại thông thường với LLM, cấu hình bằng System Prompt.
  2. **Simple RAG App:** Ứng dụng hội thoại được liên kết trực tiếp với 1 Dataset cụ thể (xử lý RAG tự động mà không cần thiết lập Workflow phức tạp).
  3. **Workflow App:** Ứng dụng chạy trên nền tảng của một sơ đồ Canvas thiết kế sẵn.
- **Vòng đời xuất bản (Publishing Lifecycle):** Cung cấp cờ `is_published`. Quản trị viên có thể tự do thử nghiệm, thay đổi cấu hình Prompt hoặc chỉnh sửa sơ đồ Workflow trong trang soạn thảo nháp mà không ảnh hưởng tới phiên bản ứng dụng đang phục vụ người dùng cuối ngoài cổng sinh viên. Khi hoàn thành kiểm thử, quản trị viên chỉ cần bấm "Publish" để cập nhật phiên bản mới nhất.

### 5.2 Nhật ký thực thi & Đo lường (Observability)
- Hệ thống tự động ghi nhật ký mọi lượt chạy ứng dụng vào bảng `runs` và `run_steps`.
- Quản trị viên có thể theo dõi:
  - Tổng thời gian xử lý phản hồi (Total Latency).
  - Bản đồ thời gian chi tiết của từng Node trong đồ thị (Node Timings) để phát hiện điểm nghẽn (bottleneck).
  - Nhật ký dữ liệu đầu vào và đầu ra chi tiết của từng bước chạy (Input/Output values) để phục vụ công tác gỡ lỗi (Debugging).

---

## 6. CỔNG THÔNG TIN SINH VIÊN (STUDENT PORTAL & CHAT ENGINE)

Là giao diện được thiết kế đơn giản, tập trung và tối ưu trải nghiệm đọc - tra cứu của sinh viên hoặc khách hàng cuối.

### 6.1 Xác thực & Bảo mật tài khoản
- Đăng nhập bằng Email và Mật khẩu do quản trị viên cấp.
- Cơ chế **Đổi mật khẩu bắt buộc ở lần đầu đăng nhập:** Nếu tài khoản sử dụng mật khẩu mặc định (`querion123`), hệ thống sẽ tự động hiển thị popup yêu cầu đổi mật khẩu mới an toàn trước khi cho phép sử dụng các tính năng khác.

### 6.2 Giao diện Hội thoại thời gian thực (SSE Streaming Chat)
- Sinh viên có thể lựa chọn các Ứng dụng (Apps) được phân phối trong Workspace của mình từ thanh Sidebar.
- Giao thức **Server-Sent Events (SSE)** truyền tải phản hồi dạng dòng chảy ký tự (streaming tokens) tạo hiệu ứng máy đánh chữ mượt mà, giảm thiểu cảm giác chờ đợi của người dùng.
- **Trích dẫn nguồn dữ liệu (Citations):** Khi câu trả lời sử dụng thông tin từ RAG, giao diện chat sẽ hiển thị các nhãn trích dẫn. Sinh viên có thể click vào nhãn để xem trước đoạn văn bản gốc (Raw chunk content), xem tên file PDF gốc và tải file về máy thông qua link presigned tạm thời của MinIO (hạn dùng 10 phút để đảm bảo an toàn bảo mật).
- **Tự động đặt tiêu đề (Auto-title):** Sau khi hoàn thành lượt chat đầu tiên của một hội thoại mới, hệ thống tự động gọi một tiến trình LLM siêu nhỏ phân tích câu hỏi/câu trả lời để đặt tên tiêu đề ngắn gọn cho hội thoại đó thay vì giữ tên mặc định "New Chat".
- Quản lý lịch sử hội thoại: Xem danh sách các cuộc trò chuyện trước đó, tiếp tục chat hoặc xóa hội thoại cũ.

---

## 7. CÁC TÍNH NĂNG BỔ TRỢ HỆ THỐNG (SYSTEM UTILITIES)

### 7.1 Quản lý và Nhập dữ liệu Sinh viên (Student Management & Bulk Import)
- Hỗ trợ tạo mới tài khoản sinh viên đơn lẻ.
- **Nhập hàng loạt (Bulk Import) từ các định dạng văn bản chuyên dụng:**
  - Hỗ trợ file **CSV**, Excel (**xlsx, xls**), và Word (**docx**).
  - Tự động map tiêu đề các cột dựa trên từ khóa (ví dụ: nhận diện cột chứa email nếu tiêu đề là "email", "thư điện tử"; nhận diện cột họ tên nếu tiêu đề là "name", "họ tên", "tên"; nhận diện cột mã sinh viên nếu tiêu đề là "student_id", "mssv"...).
  - Báo cáo kết quả import chi tiết: Số dòng tạo mới thành công, số dòng bỏ qua do trùng lặp email, và danh sách các dòng bị lỗi cú pháp dữ liệu.

### 7.2 Cấu hình nhà cung cấp AI (AI Providers Config)
- Quản trị viên (Super Admin hoặc Workspace Admin có quyền) có thể cấu hình thông số API cho các nhà cung cấp AI bao gồm: **OpenRouter, OpenAI, Anthropic, Google Gemini**.
- Toàn bộ API Key được hệ thống mã hóa bảo mật (Sử dụng mã hóa AES-GCM) trước khi lưu xuống Cơ sở dữ liệu và chỉ giải mã tạm thời trong bộ nhớ khi thực hiện lệnh gọi API.
- Cho phép cấu hình kích hoạt/vô hiệu hóa từng nhà cung cấp và đặt model mặc định cho toàn hệ thống.

### 7.3 Hỗ trợ Đa ngôn ngữ (i18n) & Giao diện đa chế độ (Theme Switching)
- Hỗ trợ chuyển đổi ngôn ngữ nhanh chóng giữa **Tiếng Việt** và **Tiếng Anh (English)** tại mọi màn hình của cả Admin Dashboard và Student Portal.
- Hỗ trợ chuyển đổi giao diện **Sáng/Tối (Light/Dark Mode)** tương thích với thiết bị của người dùng, mang lại trải nghiệm làm việc thoải mái vào ban đêm.
