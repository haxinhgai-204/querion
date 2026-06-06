"""Fix row_mapping in n_submit: replace snake_case headers with Vietnamese labels."""
import asyncio, json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

WORKFLOW_NAME = "Khảo sát trang thiết bị nhà trường"

# Vietnamese labels matching the equipment survey fields
FIELD_LABELS = {
    "diem_phong_hoc":   "Điểm phòng học",
    "diem_thiet_bi_lab":"Điểm thiết bị lab",
    "diem_thu_vien":    "Điểm thư viện",
    "diem_wifi":        "Điểm WiFi/Internet",
    "nhan_xet":         "Nhận xét",
}

NEW_ROW_MAPPING = {
    "Thời gian":    "NOW()",
    "Mã sinh viên": "{{student_id}}",
    "Họ tên":       "{{student_name}}",
    "Email":        "{{student_email}}",
    "Điểm phòng học":    "{{diem_phong_hoc}}",
    "Điểm thiết bị lab": "{{diem_thiet_bi_lab}}",
    "Điểm thư viện":     "{{diem_thu_vien}}",
    "Điểm WiFi/Internet":"{{diem_wifi}}",
    "Nhận xét":          "{{nhan_xet}}",
}

async def fix():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, graph_json FROM workflows WHERE name = :name"),
            {"name": WORKFLOW_NAME}
        )
        row = result.fetchone()
        if not row:
            print("Workflow not found!")
            return

        wf_id = row.id
        graph = row.graph_json
        nodes = graph.get("nodes", [])

        n_submit = next((n for n in nodes if n["id"] == "n_submit"), None)
        if not n_submit:
            print("n_submit node not found!")
            return

        old_mapping = n_submit["data"].get("row_mapping", {})
        print("Old headers:", list(old_mapping.keys()))

        n_submit["data"]["row_mapping"] = NEW_ROW_MAPPING
        print("New headers:", list(NEW_ROW_MAPPING.keys()))

        await conn.execute(
            text("UPDATE workflows SET graph_json = :g WHERE id = :id"),
            {"g": json.dumps(graph), "id": str(wf_id)}
        )
        await conn.commit()
        print("\nDone! Now:")
        print("1. Xóa toàn bộ dữ liệu trong Google Sheet (Ctrl+A → Delete)")
        print("2. Chạy lại chatflow — header mới sẽ tự tạo với tiếng Việt")

asyncio.run(fix())
