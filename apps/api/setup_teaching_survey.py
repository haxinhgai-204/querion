"""
Setup khảo sát chất lượng giảng dạy.
Script tự động:
  1. Tìm workflow "Khảo sát chất lượng giảng dạy" trong DB
  2. Copy credentials từ workflow trang thiết bị (đã hoạt động)
  3. Cho phép dùng cùng Spreadsheet nhưng sheet tab khác (Giang_day)
     hoặc nhập Spreadsheet ID mới
"""
import asyncio, json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

SOURCE_WORKFLOW  = "Khảo sát trang thiết bị nhà trường"   # đã có credentials
TARGET_WORKFLOW  = "Khảo sát chất lượng giảng dạy"

# ── Cấu hình ────────────────────────────────────────────────────────────────
# Để None → dùng chung Spreadsheet với khảo sát trang thiết bị
# Điền ID mới nếu muốn dùng Sheet riêng
NEW_SPREADSHEET_ID: str | None = None

# Tên tab trong Google Sheet cho khảo sát giảng dạy
SHEET_NAME = "Giang_day"
# ────────────────────────────────────────────────────────────────────────────

async def setup():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        # 1. Lấy credentials từ workflow nguồn
        src = await conn.execute(
            text("SELECT graph_json FROM workflows WHERE name = :n"),
            {"n": SOURCE_WORKFLOW}
        )
        src_row = src.fetchone()
        if not src_row:
            print(f"❌ Không tìm thấy workflow '{SOURCE_WORKFLOW}'")
            print("   Hãy tạo và setup khảo sát trang thiết bị trước!")
            return

        src_nodes = src_row.graph_json.get("nodes", [])
        src_check = next((n for n in src_nodes if n["id"] == "n_check"), None)
        if not src_check or not src_check["data"].get("service_account_json"):
            print(f"❌ Workflow '{SOURCE_WORKFLOW}' chưa có credentials")
            print("   Hãy chạy fix_submit_node.py trước!")
            return

        sa_json = src_check["data"]["service_account_json"]
        spreadsheet_id = NEW_SPREADSHEET_ID or src_check["data"]["spreadsheet_id"]
        print(f"✅ Lấy credentials từ '{SOURCE_WORKFLOW}'")
        print(f"   Spreadsheet ID: {spreadsheet_id[:30]}...")
        print(f"   Sheet tab: {SHEET_NAME}")

        # 2. Tìm workflow mục tiêu
        tgt = await conn.execute(
            text("SELECT id, graph_json FROM workflows WHERE name = :n"),
            {"n": TARGET_WORKFLOW}
        )
        tgt_row = tgt.fetchone()
        if not tgt_row:
            print(f"\n❌ Workflow '{TARGET_WORKFLOW}' chưa tồn tại trong DB")
            print("   → Vào Workflows → Từ Template → chọn '📋 Khảo sát chất lượng giảng dạy' → Dùng Template")
            print("   → Sau đó chạy lại script này")
            return

        wf_id = tgt_row.id
        graph = tgt_row.graph_json
        nodes = graph.get("nodes", [])

        # 3. Cập nhật n_check và n_submit
        for node in nodes:
            if node["id"] in ("n_check", "n_submit"):
                node["data"]["service_account_json"] = sa_json
                node["data"]["spreadsheet_id"]       = spreadsheet_id
                node["data"]["sheet_name"]           = SHEET_NAME

                if node["id"] == "n_check":
                    node["data"].pop("search_column", None)
                    node["data"]["search_column_name"] = "Mã sinh viên"
                    print(f"✅ n_check: credentials ✓ | sheet={SHEET_NAME} | search=Mã sinh viên")
                else:
                    # Fix row_mapping for teaching quality fields
                    node["data"]["row_mapping"] = {
                        "Thời gian":        "NOW()",
                        "Mã sinh viên":     "{{student_id}}",
                        "Họ tên":           "{{student_name}}",
                        "Email":            "{{student_email}}",
                        "Tên giảng viên":   "{{ten_giang_vien}}",
                        "Điểm giảng dạy":   "{{diem_giang_day}}",
                        "Điểm nội dung":    "{{diem_noi_dung}}",
                        "Điểm hỗ trợ SV":  "{{diem_ho_tro}}",
                        "Nhận xét":         "{{nhan_xet}}",
                    }
                    print(f"✅ n_submit: credentials ✓ | sheet={SHEET_NAME} | {len(node['data']['row_mapping'])} columns")

        await conn.execute(
            text("UPDATE workflows SET graph_json = :g WHERE id = :id"),
            {"g": json.dumps(graph), "id": str(wf_id)}
        )
        await conn.commit()

        print(f"""
✅ SETUP HOÀN THÀNH!

Google Sheet sẽ ghi vào tab '{SHEET_NAME}' với các cột:
  Thời gian | Mã sinh viên | Họ tên | Email | Tên giảng viên | Điểm giảng dạy | Điểm nội dung | Điểm hỗ trợ SV | Nhận xét

Bước tiếp theo:
  1. Vào Google Sheet → mở tab '{SHEET_NAME}' (nếu chưa có thì tạo mới)
     Hoặc để trống — hệ thống tự tạo tab khi chạy lần đầu
  2. Tạo App → chọn workflow '{TARGET_WORKFLOW}' → Publish → cho sinh viên dùng
""")

asyncio.run(setup())
