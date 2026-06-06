const zlib = require('zlib');
const fs = require('fs');
const https = require('https');
const path = require('path');

const pumlText = `@startuml
skinparam handwritten false
skinparam monochrome false
skinparam shadowing true
skinparam ActivityBackgroundColor #F9FBE7
skinparam ActivityBorderColor #827717
skinparam ActivityFontColor #33691E
skinparam ActivityFontSize 12
skinparam ActivityFontName Arial
skinparam ArrowColor #558B2F
skinparam StartColor #2E7D32
skinparam EndColor #C62828

title Sơ đồ quy trình xử lý truy vấn của AI Agent (Querion)

start
:Sinh viên gửi câu hỏi từ giao diện Chat;
:FastAPI Gateway xác thực tài khoản (JWT);
:Tải cấu hình Đồ thị (graph_json) từ Cơ sở dữ liệu;
:Khởi tạo phiên thực thi Run (trạng thái 'running');
:Khởi tạo bộ nhớ tạm thời State\\n(chứa query, history, extracted_params...);

if (Workflow yêu cầu trích xuất thông tin?) then (Có)
  :LLM trích xuất tham số từ hội thoại\\n(Node parameter_extract);
  if (Đã cung cấp đủ tham số cần thiết?) then (Có)
    :Cập nhật các tham số đã trích xuất vào State;
    split
      :Tìm kiếm ngữ nghĩa trên Vector DB\\n(Node retrieve);
    split again
      :Gọi API / Webhook bên ngoài\\n(Node http_request);
    split again
      :Chạy mã Python tính toán sandbox\\n(Node code_execute);
    end split
    :Tổng hợp ngữ cảnh và tạo câu trả lời\\n(Node llm_generate);
  else (Thiếu)
    :Tạo câu hỏi yêu cầu sinh viên bổ sung\\n(Node answer);
  endif
else (Không)
  split
    :Tìm kiếm ngữ nghĩa trên Vector DB\\n(Node retrieve);
  split again
    :Gọi API / Webhook bên ngoài\\n(Node http_request);
  split again
    :Chạy mã Python tính toán sandbox\\n(Node code_execute);
  end split
  :Tổng hợp ngữ cảnh và tạo câu trả lời\\n(Node llm_generate);
endif

:Lưu tin nhắn mới và ghi lịch sử chạy (Run Steps) vào DB;
:Trả kết quả kèm nguồn trích dẫn về Chat UI (SSE Streaming);
:Hiển thị câu trả lời và nguồn tài liệu tham khảo cho sinh viên;
stop
@endum`;

function encodePlantUML(text) {
  const compressed = zlib.deflateRawSync(Buffer.from(text, 'utf8'));
  const stdB64 = compressed.toString('base64');
  const stdChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  const pumlChars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_";
  
  let result = '';
  for (let i = 0; i < stdB64.length; i++) {
    const char = stdB64[i];
    if (char === '=') continue; // Skip padding
    const index = stdChars.indexOf(char);
    if (index !== -1) {
      result += pumlChars[index];
    } else {
      result += char;
    }
  }
  return result;
}

const encoded = encodePlantUML(pumlText);
const url = `https://www.plantuml.com/plantuml/png/${encoded}`;
console.log('Fetching from:', url);

const docsDir = 'c:/Users/HP/Documents/Projects/querion/docs/images';
const artDir = 'C:/Users/HP/.gemini/antigravity/brain/eb911444-71fd-4c7e-acbb-5f4f4967176b/artifacts';

fs.mkdirSync(docsDir, { recursive: true });
fs.mkdirSync(artDir, { recursive: true });

https.get(url, (res) => {
  if (res.statusCode !== 200) {
    console.error('Failed with status code:', res.statusCode);
    process.exit(1);
  }
  
  const data = [];
  res.on('data', (chunk) => data.push(chunk));
  res.on('end', () => {
    const buffer = Buffer.concat(data);
    fs.writeFileSync(path.join(docsDir, 'so_do_tong_quan_xu_ly.png'), buffer);
    fs.writeFileSync(path.join(artDir, 'so_do_tong_quan_xu_ly.png'), buffer);
    console.log('SUCCESS');
  });
}).on('error', (err) => {
  console.error('Error:', err.message);
  process.exit(1);
});
