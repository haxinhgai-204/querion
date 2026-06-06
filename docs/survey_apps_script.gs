/**
 * QUERION SURVEY — Google Apps Script Web App
 * =============================================
 * Deploy này làm cầu nối giữa chatflow Querion và Google Sheets.
 *
 * CÁCH DEPLOY:
 *   1. Mở Google Sheet cần dùng → Extensions → Apps Script
 *   2. Xóa code mặc định, dán toàn bộ file này vào
 *   3. Lưu lại (Ctrl+S)
 *   4. Deploy → New deployment → Web app
 *      - Execute as: Me
 *      - Who has access: Anyone
 *   5. Copy URL deployment → dán vào node "http_request" trong Querion Workflow
 *
 * CÁCH HOẠT ĐỘNG:
 *   GET  ?action=check&student_id=xxx  → Kiểm tra sinh viên đã nộp chưa
 *   POST { action:"submit", ...fields } → Ghi hàng mới vào Sheet
 *
 * CÁC HẰNG SỐ CẦN THAY:
 *   SHEET_NAME — tên sheet tab (mặc định "Sheet1")
 *   STUDENT_ID_COLUMN — cột chứa student_id để kiểm tra trùng lặp
 */

// ─── Cấu hình ────────────────────────────────────────────────────────────────
var SHEET_NAME = "Sheet1";          // Tên tab trong Google Sheet
var STUDENT_ID_COLUMN = 1;          // Cột A (1-indexed) chứa student_id
var SUBMITTED_MARKER = "submitted"; // Giá trị dùng để đánh dấu đã nộp


// ─── Xử lý GET (kiểm tra đã nộp chưa) ───────────────────────────────────────
function doGet(e) {
  try {
    var action = e.parameter.action || "check";
    var studentId = e.parameter.student_id || "";

    if (action === "check") {
      var alreadySubmitted = _checkSubmitted(studentId);
      return _jsonResponse({ submitted: alreadySubmitted });
    }

    return _jsonResponse({ error: "Unknown action: " + action }, 400);

  } catch (err) {
    return _jsonResponse({ error: err.toString() }, 500);
  }
}


// ─── Xử lý POST (ghi kết quả khảo sát) ──────────────────────────────────────
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var action = data.action || "submit";

    if (action === "submit") {
      // Kiểm tra trùng trước khi ghi
      if (_checkSubmitted(data.student_id || "")) {
        return _jsonResponse({ status: "already_submitted" });
      }

      _appendRow(data);
      return _jsonResponse({ status: "success" });
    }

    return _jsonResponse({ error: "Unknown action: " + action }, 400);

  } catch (err) {
    return _jsonResponse({ error: err.toString() }, 500);
  }
}


// ─── Kiểm tra sinh viên đã nộp chưa ─────────────────────────────────────────
function _checkSubmitted(studentId) {
  if (!studentId) return false;

  var sheet = _getSheet();
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return false; // Chỉ có header, chưa có data

  var ids = sheet.getRange(2, STUDENT_ID_COLUMN, lastRow - 1, 1).getValues();
  for (var i = 0; i < ids.length; i++) {
    if (ids[i][0].toString() === studentId.toString()) return true;
  }
  return false;
}


// ─── Ghi hàng mới vào Sheet ──────────────────────────────────────────────────
function _appendRow(data) {
  var sheet = _getSheet();

  // Tự động tạo header nếu sheet trống
  if (sheet.getLastRow() === 0) {
    _createHeader(sheet, data);
  }

  // Xây dựng hàng data theo đúng thứ tự header
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  var row = headers.map(function(h) {
    if (h === "Thời gian") return new Date().toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
    return data[h] !== undefined ? data[h] : "";
  });

  sheet.appendRow(row);
}


// ─── Tạo header tự động từ data payload ──────────────────────────────────────
function _createHeader(sheet, data) {
  // Các cột cố định đặt trước
  var fixedCols = ["student_id", "student_name", "student_email"];
  var dynamicCols = Object.keys(data).filter(function(k) {
    return k !== "action" && fixedCols.indexOf(k) === -1;
  });

  var headers = ["Thời gian"].concat(fixedCols).concat(dynamicCols);

  // Ghi header vào dòng 1
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

  // Định dạng header
  var headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setFontWeight("bold");
  headerRange.setBackground("#4a86e8");
  headerRange.setFontColor("#ffffff");
  sheet.setFrozenRows(1);
}


// ─── Helpers ─────────────────────────────────────────────────────────────────
function _getSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
  }
  return sheet;
}

function _jsonResponse(obj, code) {
  var output = ContentService.createTextOutput(JSON.stringify(obj));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}


// ─── Test thủ công trong Apps Script IDE ─────────────────────────────────────
function testCheck() {
  var result = _checkSubmitted("test-student-001");
  Logger.log("Submitted: " + result);
}

function testSubmit() {
  _appendRow({
    action: "submit",
    student_id: "test-001",
    student_name: "Nguyễn Văn A",
    student_email: "a@student.edu.vn",
    diem_phong_hoc: "4",
    diem_thiet_bi_lab: "3",
    diem_thu_vien: "5",
    diem_wifi: "2",
    nhan_xet: "Wifi yếu, cần nâng cấp thiết bị lab",
  });
  Logger.log("Row appended OK");
}
