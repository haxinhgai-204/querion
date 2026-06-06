import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT name, graph_json FROM workflows ORDER BY updated_at DESC LIMIT 3"
        ))
        for row in rows:
            nodes = row.graph_json.get("nodes", [])
            gs_nodes = [n for n in nodes if n.get("type") == "google_sheets"]
            print("Workflow:", row.name)
            for n in gs_nodes:
                d = n.get("data", {})
                has_sa = bool(d.get("service_account_json"))
                sheet_id = d.get("spreadsheet_id", "")[:40]
                op = d.get("operation", "")
                print("  Node", n["id"], "op=" + op, "has_credentials=" + str(has_sa), "spreadsheet_id=" + repr(sheet_id))

asyncio.run(check())
