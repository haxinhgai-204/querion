"""Fix n_check node: use search_column_name instead of column index."""
import asyncio, json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

WORKFLOW_NAME = "Khảo sát trang thiết bị nhà trường"

async def fix():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, graph_json FROM workflows WHERE name = :name"),
            {"name": WORKFLOW_NAME}
        )
        row = result.fetchone()
        if not row:
            print("Workflow not found!"); return

        wf_id = row.id
        graph = row.graph_json
        nodes = graph.get("nodes", [])

        n_check = next((n for n in nodes if n["id"] == "n_check"), None)
        if not n_check:
            print("n_check not found!"); return

        # Replace numeric index with column name
        n_check["data"].pop("search_column", None)
        n_check["data"]["search_column_name"] = "Mã sinh viên"
        print("Updated n_check:")
        print("  search_column_name:", n_check["data"]["search_column_name"])
        print("  search_value:", n_check["data"]["search_value"])

        await conn.execute(
            text("UPDATE workflows SET graph_json = :g WHERE id = :id"),
            {"g": json.dumps(graph), "id": str(wf_id)}
        )
        await conn.commit()
        print("Done! Duplicate check will now search by header name 'Mã sinh viên'")

asyncio.run(fix())
