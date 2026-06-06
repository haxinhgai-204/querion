"""Google Sheets API v4 integration — dùng Service Account JWT, không cần gspread.

Cách n8n, Make, Zapier tương tác với Google Sheets trong thực tế:
─────────────────────────────────────────────────────────────────
1. Lấy access_token từ Service Account (JWT → POST google oauth2)
2. Gọi thẳng Google Sheets REST API v4 với Bearer token
   - READ:   GET  https://sheets.googleapis.com/v4/spreadsheets/{id}/values/{range}
   - WRITE:  POST https://sheets.googleapis.com/v4/spreadsheets/{id}/values/{range}:append
3. Không cần thư viện ngoài (chỉ cần httpx + PyJWT)

Cấu hình trong App.model_config_json:
{
  "google_service_account": { ...service account JSON... },
  "google_sheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
}
"""

import json
import time
from typing import Any

import httpx


async def get_google_access_token(service_account: dict) -> str:
    """Lấy OAuth2 access_token từ Service Account JSON.
    
    Đây là cách n8n thực hiện khi dùng Google Sheets node:
    1. Ký JWT bằng private_key của service account
    2. Gửi JWT lên Google để đổi lấy access_token (30 phút)
    """
    try:
        import jwt  # PyJWT
    except ImportError:
        raise RuntimeError("Cần cài PyJWT: pip install PyJWT cryptography")

    now = int(time.time())
    payload = {
        "iss": service_account["client_email"],
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    signed_jwt = jwt.encode(payload, service_account["private_key"], algorithm="RS256")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_jwt,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def sheets_get(
    service_account: dict,
    sheet_id: str,
    range_: str = "Sheet1",
) -> list[list[Any]]:
    """Đọc dữ liệu từ Google Sheets.
    
    Tương đương Google Sheets node "Get Rows" trong n8n.
    """
    token = await get_google_access_token(service_account)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json().get("values", [])


async def sheets_append(
    service_account: dict,
    sheet_id: str,
    values: list[list[Any]],
    range_: str = "Sheet1",
) -> bool:
    """Ghi hàng mới vào Google Sheets.
    
    Tương đương Google Sheets node "Append Row" trong n8n.
    Google Sheets API tự tìm hàng trống cuối cùng để ghi.
    """
    token = await get_google_access_token(service_account)
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
        f"/values/{range_}:append"
        f"?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"values": values},
            timeout=15.0,
        )
        resp.raise_for_status()
        return True


async def sheets_clear_row(
    service_account: dict,
    sheet_id: str,
    row_number: int,  # 1-indexed (row 1 = header)
    range_: str = "Sheet1",
) -> bool:
    """Xóa nội dung của một hàng cụ thể (không xóa hàng, chỉ xóa nội dung).
    
    Dùng khi cần ghi đè header row cũ.
    """
    token = await get_google_access_token(service_account)
    # Clear the specific row range, e.g. Sheet1!1:1
    clear_range = f"{range_}!{row_number}:{row_number}"
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{clear_range}:clear"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return True


async def sheets_find_row(
    service_account: dict,
    sheet_id: str,
    column_index: int,  # 0-based (ignored if column_name is given)
    value: str,
    range_: str = "Sheet1",
    column_name: str = "",  # header name, e.g. "Mã sinh viên" — preferred over index
) -> int | None:
    """Tìm hàng theo giá trị cột — dùng để kiểm tra sinh viên đã nộp chưa.

    Nếu column_name được cung cấp, tự động tìm column index từ header row
    (tránh lỗi do JSONB sort keys theo alphabetical).

    Returns:
        Row index (0-based, bao gồm header) nếu tìm thấy, None nếu không có.
    """
    all_rows = await sheets_get(service_account, sheet_id, range_)
    if not all_rows:
        return None

    # Resolve column index from header name if provided
    if column_name and all_rows:
        header_row = all_rows[0]
        try:
            column_index = header_row.index(column_name)
        except ValueError:
            # Header not found yet (sheet might be empty or header not created)
            return None

    for i, row in enumerate(all_rows):
        if i == 0:
            continue  # skip header row
        if len(row) > column_index and str(row[column_index]).strip() == str(value).strip():
            return i
    return None


async def check_and_submit_survey(
    service_account: dict,
    sheet_id: str,
    student_id: str,
    row_data: dict[str, Any],
    sheet_name: str = "Sheet1",
) -> dict[str, str]:
    """Check duplicate rồi ghi kết quả khảo sát vào Google Sheets.
    
    Đây là hàm tổng hợp được gọi bởi survey router — thay thế hoàn toàn gspread.
    
    Returns:
        {"status": "success"} hoặc {"status": "already_submitted"}
    """
    # 1. Kiểm tra sinh viên đã nộp chưa (tìm student_id trong cột B — index 1)
    existing = await sheets_find_row(service_account, sheet_id, 1, student_id, sheet_name)
    if existing is not None:
        return {"status": "already_submitted"}

    # 2. Tạo header nếu sheet trống
    all_rows = await sheets_get(service_account, sheet_id, sheet_name)
    if not all_rows:
        headers = ["Thời gian", "student_id", "student_name", "student_email"]
        survey_fields = [k for k in row_data if k not in ("student_id", "student_name", "student_email")]
        headers.extend(survey_fields)
        await sheets_append(service_account, sheet_id, [headers], sheet_name)

    # 3. Ghi hàng data
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC+7")

    # Lấy headers hiện tại để sắp xếp đúng thứ tự cột
    all_rows = await sheets_get(service_account, sheet_id, sheet_name)
    headers = all_rows[0] if all_rows else []

    if headers:
        row = []
        for h in headers:
            if h == "Thời gian":
                row.append(now)
            else:
                row.append(str(row_data.get(h, "")))
    else:
        row = [now, student_id,
               row_data.get("student_name", ""),
               row_data.get("student_email", ""),
               *[str(v) for k, v in row_data.items()
                 if k not in ("student_id", "student_name", "student_email")]]

    await sheets_append(service_account, sheet_id, [row], sheet_name)
    return {"status": "success"}
