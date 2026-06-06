"""Fix n_submit node: copy credentials from n_check + set correct spreadsheet_id."""
import asyncio, json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select
from app.config import settings

WORKFLOW_NAME = "Khảo sát trang thiết bị nhà trường"
SPREADSHEET_ID = "1VXkWN_P9_XLOm1JlENxSDa3yNK1n8ja-5IVViny_qdo"

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

        # Find n_check credentials
        n_check = next((n for n in nodes if n["id"] == "n_check"), None)
        n_submit = next((n for n in nodes if n["id"] == "n_submit"), None)

        if not n_check or not n_submit:
            print("Nodes not found!")
            return

        sa_json = n_check["data"].get("service_account_json", "")
        if not sa_json:
            print("n_check has no credentials either! Please add credentials via UI first.")
            return

        # Copy credentials to n_submit + set correct spreadsheet_id
        n_submit["data"]["service_account_json"] = sa_json
        n_submit["data"]["spreadsheet_id"] = SPREADSHEET_ID
        n_check["data"]["spreadsheet_id"] = SPREADSHEET_ID  # fix n_check too

        print("Updating n_submit with:")
        print("  has_credentials:", bool(n_submit["data"]["service_account_json"]))
        print("  spreadsheet_id:", n_submit["data"]["spreadsheet_id"])
        print("  n_check spreadsheet_id:", n_check["data"]["spreadsheet_id"])

        await conn.execute(
            text("UPDATE workflows SET graph_json = :g WHERE id = :id"),
            {"g": json.dumps(graph), "id": str(wf_id)}
        )
        await conn.commit()
        print("Done! Workflow updated in DB.")

asyncio.run(fix())
