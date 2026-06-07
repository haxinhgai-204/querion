"""Workflow/Chatflow runtime — execute graph_json via node chain.

Supports linear chain + if_else branching.
Each node transforms the state dict sequentially.
"""

import json
import re
import httpx
from typing import Any, AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval import retrieve
from app.services.encryption import decrypt_key
from app.services.observability import log_step_start, log_step_end, complete_run
from app.models.run import Run


async def run_workflow(
    db: AsyncSession,
    graph_json: dict[str, Any],
    query: str,
    inputs: dict[str, Any] | None = None,
    history: list[dict] | None = None,
    run: Run | None = None,
    app_system_prompt: str | None = None,
    app_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a validated workflow/chatflow graph and return answer + citations.

    Args:
        history: conversation history for chatflow memory (list of {role, content})
        app_system_prompt: system prompt from the App config (UI). If provided,
            it overrides the workflow node's own system_prompt field via {{system_prompt}}.
    """
    nodes = graph_json.get("nodes", [])
    edges = graph_json.get("edges", [])

    node_map = {n["id"]: n for n in nodes}

    # Build adjacency list (support multiple outgoing for if_else)
    adj: dict[str, list[dict]] = {n["id"]: [] for n in nodes}
    for edge in edges:
        adj[edge["source"]].append(edge)

    # Find start node
    in_degree: dict[str, int] = {n["id"]: 0 for n in nodes}
    for edge in edges:
        in_degree[edge["target"]] = in_degree.get(edge["target"], 0) + 1

    start = None
    for n in nodes:
        if n["type"] == "input" and in_degree[n["id"]] == 0:
            start = n["id"]
            break

    if not start:
        raise RuntimeError("No input node found")

    # Initialize state
    state: dict[str, Any] = {
        "query": query,
        "inputs": inputs or {},
        "retrieved_chunks": [],
        "prompt_messages": [],
        "answer": "",
        "citations": [],
        "extracted_params": {},
        "history": history or [],
        # App-level system prompt injected from App.system_prompt (UI config).
        # Used by compose_prompt node via {{system_prompt}} placeholder.
        "app_system_prompt": app_system_prompt or "",
        # App model_config_json — passed through to google_sheets node for credentials
        "app_config": app_config or {},
    }
    print(f"\n[WORKFLOW] START | query={query[:60]!r} | nodes={len(nodes)} | history_len={len(history or [])}")

    # Execute graph (supports if_else branching)
    current_id: str | None = start
    visited = set()

    while current_id:
        if current_id in visited:
            break  # prevent infinite loops
        visited.add(current_id)

        node = node_map[current_id]
        node_type = node["type"]
        node_data = node.get("data", {})

        print(f"[WORKFLOW]   exec node={current_id!r} type={node_type!r}")

        # Log step start (if observability enabled)
        step = None
        if run:
            step = await log_step_start(db, run_id=run.id, node_id=current_id, node_type=node_type,
                                        input_data={"query": state["query"][:200]})

        await _execute_node(db, node_type, node_data, state)
        print(f"[WORKFLOW]   done  node={current_id!r} | answer={state.get('answer','')[:50]!r} | params={list(state.get('extracted_params',{}).keys())} | _branch={state.get('_branch','')!r}")

        # Log step end
        if run and step:
            output_preview = {"answer": state.get("answer", "")[:200]}
            if state.get("extracted_params"):
                output_preview["extracted_params"] = state["extracted_params"]
            await log_step_end(step, output_data=output_preview)

        # Find next node
        outgoing = adj.get(current_id, [])
        if not outgoing:
            print(f"[WORKFLOW]   no outgoing from {current_id!r} — stop")
            break
        elif node_type == "if_else" and len(outgoing) >= 2:
            # If/else: pick branch based on condition result
            branch = state.get("_branch", "true")

            # ── Use sourceHandle ("true"/"false") set by React Flow canvas ─
            true_edge = None
            false_edge = None
            for edge in outgoing:
                handle = str(edge.get("sourceHandle", "")).lower()
                if handle == "false":
                    false_edge = edge
                elif handle == "true":
                    true_edge = edge

            # Fallback: sourceHandle not set → use draw order (0=true, 1=false)
            if true_edge is None and false_edge is None:
                true_edge = outgoing[0]
                false_edge = outgoing[1]
            elif true_edge is None:
                true_edge = next(e for e in outgoing if e is not false_edge)
            elif false_edge is None:
                false_edge = next(e for e in outgoing if e is not true_edge)

            chosen = true_edge["target"] if branch == "true" else false_edge["target"]
            print(f"[WORKFLOW]   if_else branch={branch!r} sourceHandles={[e.get('sourceHandle') for e in outgoing]} → {chosen!r}")
            current_id = chosen
        else:
            current_id = outgoing[0]["target"]

    print(f"[WORKFLOW] END | final_answer={state.get('answer','')[:80]!r}")

    # Complete run
    if run:
        await complete_run(run, status="completed")

    return {
        "answer": state["answer"],
        "extracted_params": state.get("extracted_params", {}),
        "retriever_resources": [
            {
                "chunk_id": c.get("chunk_id"),
                "content_preview": c.get("content_preview", ""),
                "chunk_index": c.get("chunk_index"),
                "document_id": c.get("document_id"),
                "dataset_id": c.get("dataset_id"),
                "filename": c.get("filename", ""),
                "score": c.get("score", 0),
            }
            for c in state["citations"]
        ],
    }


async def _execute_node(
    db: AsyncSession,
    node_type: str,
    node_data: dict[str, Any],
    state: dict[str, Any],
) -> None:
    """Execute a single node and update state."""

    if node_type == "input":
        pass

    elif node_type == "retrieve":
        dataset_ids_raw = node_data.get("dataset_ids", [])
        top_k = node_data.get("top_k", 5)
        if dataset_ids_raw:
            dataset_ids = [UUID(d) if isinstance(d, str) else d for d in dataset_ids_raw]
            chunks = await retrieve(db=db, query=state["query"], dataset_ids=dataset_ids, top_k=top_k)
            state["retrieved_chunks"] = chunks
            state["citations"] = chunks

    elif node_type == "compose_prompt":
        template = node_data.get("template", "{{query}}")
        context_parts = []
        for i, chunk in enumerate(state["retrieved_chunks"]):
            context_parts.append(f"[#{i}] {chunk['content']}")
        context = "\n\n".join(context_parts) if context_parts else ""

        # Resolve system_prompt: App-level takes priority over node-level
        resolved_system_prompt = state.get("app_system_prompt") or node_data.get("system_prompt", "")

        prompt_text = template.replace("{{query}}", state["query"])
        prompt_text = prompt_text.replace("{{context}}", context)
        prompt_text = prompt_text.replace("{{system_prompt}}", resolved_system_prompt)

        # Inject extracted_params as readable JSON
        extracted_str = json.dumps(state.get("extracted_params", {}), ensure_ascii=False, indent=2)
        prompt_text = prompt_text.replace("{{extracted_params}}", extracted_str)

        # Inject inputs (student context, etc.)
        for k, v in (state.get("inputs") or {}).items():
            prompt_text = prompt_text.replace(f"{{{{inputs.{k}}}}}", str(v) if v is not None else "")
            prompt_text = prompt_text.replace(f"{{{{{k}}}}}", str(v) if v is not None else "")

        # If the template doesn't use {{system_prompt}} but app has one, prepend it
        if state.get("app_system_prompt") and "{{system_prompt}}" not in template:
            prompt_text = state["app_system_prompt"] + "\n\n" + prompt_text

        # Include history for chatflow memory
        messages: list[dict] = []
        if prompt_text:
            messages.append({"role": "system", "content": prompt_text})
        for h in state.get("history", []):
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": state["query"]})
        state["prompt_messages"] = messages

    elif node_type == "llm_generate":
        from app.services.chat import get_active_llm_provider
        provider = await get_active_llm_provider(db)
        if not provider:
            state["answer"] = "Error: No active LLM provider configured."
            return

        api_key = decrypt_key(provider.api_key_encrypted)
        model = node_data.get("model") or provider.model_name
        temperature = node_data.get("temperature", 0.7)
        max_tokens = node_data.get("max_tokens", 4096)
        messages = state["prompt_messages"] or [{"role": "user", "content": state["query"]}]

        answer = await _call_llm(
            provider_name=provider.provider_name,
            api_key=api_key, model=model,
            messages=messages,
            temperature=temperature, max_tokens=max_tokens,
        )
        # Normalize: LLM may return None (content filter, tool_calls, etc.)
        state["answer"] = answer or "Xin lỗi, tôi không thể tạo phản hồi lúc này. Vui lòng thử lại."

    elif node_type == "parameter_extract":
        # Use LLM to extract structured parameters from the latest message
        schema = node_data.get("schema", {})
        # schema: {"field_name": "field_description", ...}
        if not schema:
            return

        schema_desc = "\n".join(f"- {k}: {v}" for k, v in schema.items())
        extraction_prompt = f"""Extract the following fields from the conversation. Return ONLY valid JSON, nothing else.

Fields to extract:
{schema_desc}

If a field cannot be determined from the conversation, use null.
"""
        # Build context: history + current query
        conversation_text = ""
        for h in state.get("history", []):
            conversation_text += f"{h['role']}: {h['content']}\n"
        conversation_text += f"user: {state['query']}\n"

        extract_messages = [
            {"role": "system", "content": extraction_prompt},
            {"role": "user", "content": conversation_text},
        ]

        from app.services.chat import get_active_llm_provider
        provider = await get_active_llm_provider(db)
        if provider:
            api_key = decrypt_key(provider.api_key_encrypted)
            raw = await _call_llm(
                provider_name=provider.provider_name,
                api_key=api_key, model=provider.model_name,
                messages=extract_messages,
                temperature=0.0, max_tokens=1024,
            )
            # Parse JSON from response
            try:
                # Strip markdown code fences if present
                clean = re.sub(r"```json?\s*", "", raw)
                clean = re.sub(r"```\s*$", "", clean).strip()
                extracted = json.loads(clean)

                # ── Fix 1: Carry over previously extracted non-null values ──
                # Prevents losing mon_hoc when user replies with MSSV only
                prev_params = state.get("extracted_params", {})
                for key, val in prev_params.items():
                    if val is not None and val != "" and not extracted.get(key):
                        extracted[key] = val

                # ── Fix 2: Heuristic — bare number → treat as mssv ──────────
                # When user types only digits (e.g. "22110045"), LLM often
                # fails to recognize it as MSSV without explicit label.
                current_query = state.get("query", "").strip()
                if re.match(r"^\d{7,10}$", current_query) and not extracted.get("mssv"):
                    extracted["mssv"] = current_query
                    print(f"[parameter_extract] Auto-detected MSSV from bare number: {current_query!r}")

                state["extracted_params"] = extracted
            except json.JSONDecodeError:
                state["extracted_params"] = {"_raw": raw}

    elif node_type == "http_request":
        # Call external API
        url = node_data.get("url", "")
        method = node_data.get("method", "POST").upper()
        headers = node_data.get("headers", {})
        body_template = node_data.get("body_template", "")

        if not url:
            return

        # Apply template substitution to URL (supports GET query params like ?student_id={{student_id}})
        url = _apply_template(url, state)

        # Apply template substitution to body
        body_str = _apply_template(body_template, state)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    resp = await client.get(url, headers=headers)
                elif method == "PUT":
                    resp = await client.put(url, headers=headers, content=body_str)
                elif method == "DELETE":
                    resp = await client.delete(url, headers=headers)
                else:  # POST
                    content_type = headers.get("Content-Type", "application/json")
                    resp = await client.post(url, headers=headers, content=body_str)

                state["http_response"] = {
                    "status": resp.status_code,
                    "body": resp.text[:2000],
                }
        except Exception as e:
            state["http_response"] = {"status": 0, "body": str(e)}

    elif node_type == "google_sheets":
        # ── Google Sheets node — tương tác trực tiếp với Google Sheets API v4 ──
        # Node config:
        #   service_account_json: str  (JSON string của Service Account — dán thẳng vào node)
        #   operation:            "find_row" | "append_row"
        #   spreadsheet_id:       Sheet ID (từ URL Google Sheets)
        #   sheet_name:           Tên tab, mặc định "Sheet1"
        #   [find_row]  search_column: int (0=A), search_value: str (hỗ trợ {{placeholder}})
        #   [append_row] row_mapping: dict { "Header": "{{placeholder}} hoặc NOW()" }
        #
        # Output variables:
        #   find_row    → state["google_sheets_found"] = "true" / "false"
        #   append_row  → state["google_sheets_status"] = "success" / "error:..."

        operation      = node_data.get("operation", "append_row")
        spreadsheet_id = _apply_template(node_data.get("spreadsheet_id", ""), state)
        sheet_name     = node_data.get("sheet_name", "Sheet1")

        # ── Credentials resolution (node-level beats app-level) ──────────────
        # Priority 1: service_account_json dán trực tiếp vào node config
        sa_raw = node_data.get("service_account_json", "")
        if sa_raw:
            try:
                import json as _json
                service_account = _json.loads(sa_raw) if isinstance(sa_raw, str) else sa_raw
            except Exception:
                service_account = None
        else:
            # Priority 2: App Settings → model_config_json["google_service_account"]
            service_account = (state.get("app_config") or {}).get("google_service_account")

        if not service_account or not spreadsheet_id:
            print(f"[google_sheets] No credentials or spreadsheet_id — skipping (op={operation})")
            state["google_sheets_found"] = "false" if operation == "find_row" else ""
            state["google_sheets_status"] = "error:no_credentials"
            return

        try:
            from app.services.google_sheets import (
                get_google_access_token, sheets_append, sheets_find_row, sheets_get,
            )

            if operation == "find_row":
                search_col      = int(node_data.get("search_column", 0))
                search_col_name = node_data.get("search_column_name", "")  # e.g. "Mã sinh viên"
                search_val      = _apply_template(node_data.get("search_value", ""), state)
                row_idx = await sheets_find_row(
                    service_account, spreadsheet_id,
                    search_col, search_val, sheet_name,
                    column_name=search_col_name,  # preferred: find col by header name
                )
                found = row_idx is not None  # row_idx already skips header (i==0 skipped)
                state["google_sheets_found"] = "true" if found else "false"
                print(f"[google_sheets] find_row col={search_col_name or search_col!r} val={search_val!r} → found={found}")

            elif operation == "append_row":
                row_mapping: dict = node_data.get("row_mapping", {})

                # Get or create header from the sheet
                all_rows = await sheets_get(service_account, spreadsheet_id, sheet_name)
                if not all_rows:
                    # Auto-create header from row_mapping keys
                    headers = list(row_mapping.keys())
                    await sheets_append(service_account, spreadsheet_id, [headers], sheet_name)
                    all_rows = [headers]
                    print(f"[google_sheets] Created headers: {headers}")

                existing_headers = all_rows[0]

                # Detect stale/mismatched headers — if none of the existing headers
                # match row_mapping keys, the header row is outdated → overwrite it
                matching = sum(1 for h in existing_headers if h in row_mapping)
                if matching == 0 and len(existing_headers) > 0:
                    print(f"[google_sheets] Stale headers detected {existing_headers[:4]}... → overwriting with new headers")
                    from app.services.google_sheets import sheets_clear_row
                    try:
                        await sheets_clear_row(service_account, spreadsheet_id, 1, sheet_name)
                    except Exception:
                        pass  # clear might fail on empty sheet, ignore
                    headers = list(row_mapping.keys())
                    await sheets_append(service_account, spreadsheet_id, [headers], sheet_name)
                    print(f"[google_sheets] New headers written: {headers}")
                else:
                    headers = existing_headers

                # Build row values in header order, applying template substitution
                row = []
                matched_cols = 0
                for h in headers:
                    template = row_mapping.get(h, "")
                    if template == "NOW()":
                        from datetime import datetime, timezone
                        row.append(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                        matched_cols += 1
                    elif template:
                        row.append(_apply_template(template, state))
                        matched_cols += 1
                    else:
                        row.append("")  # unknown column — leave blank

                print(f"[google_sheets] Appending row: {matched_cols}/{len(headers)} columns filled")
                await sheets_append(service_account, spreadsheet_id, [row], sheet_name)
                state["google_sheets_status"] = "success"
                print(f"[google_sheets] append_row SUCCESS")

        except Exception as e:
            print(f"[google_sheets node] Error: {e}")
            if operation == "find_row":
                state["google_sheets_found"] = "false"  # fail open (don't block student)
            else:
                state["google_sheets_status"] = f"error:{e}"

    elif node_type == "if_else":
        # Evaluate condition and set branch
        variable = node_data.get("variable", "")  # e.g. "extracted_params.name"
        operator = node_data.get("operator", "exists")  # exists, equals, contains, not_empty
        compare_value = node_data.get("value", "")

        # Resolve variable from state
        actual_value = _resolve_variable(state, variable)

        if operator == "exists":
            result = actual_value is not None
        elif operator == "not_empty":
            result = bool(actual_value)
        elif operator == "equals":
            result = str(actual_value) == str(compare_value)
        elif operator == "contains":
            result = str(compare_value) in str(actual_value or "")
        else:
            result = bool(actual_value)

        state["_branch"] = "true" if result else "false"

    elif node_type == "answer":
        # Answer node for chatflow — uses answer from state or generates one
        template = node_data.get("template", "")
        if template:
            answer = template
            answer = answer.replace("{{answer}}", state.get("answer", ""))
            answer = answer.replace("{{query}}", state["query"])
            for k, v in state.get("extracted_params", {}).items():
                answer = answer.replace(f"{{{{{k}}}}}", str(v) if v is not None else "")
            http_resp = state.get("http_response", {})
            answer = answer.replace("{{http_status}}", str(http_resp.get("status", "")))
            state["answer"] = answer
        # If no template, keep existing answer from llm_generate (already in state["answer"])
        # Note: if still empty here, the caller (student_auth) will show a generic fallback


    elif node_type == "code_execute":
        # Execute Python code in a restricted sandbox
        code = node_data.get("code", "")
        if not code.strip():
            return

        # Prepare arguments accessible to the code
        args = {
            "query": state["query"],
            "inputs": state.get("inputs", {}),
            "answer": state.get("answer", ""),
            "extracted_params": state.get("extracted_params", {}),
            "retrieved_chunks": state.get("retrieved_chunks", []),
            "http_response": state.get("http_response", {}),
        }

        # Safe builtins
        safe_builtins = {
            "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
            "enumerate": enumerate, "filter": filter, "float": float,
            "int": int, "isinstance": isinstance, "len": len, "list": list,
            "map": map, "max": max, "min": min, "print": print, "range": range,
            "round": round, "set": set, "sorted": sorted, "str": str,
            "sum": sum, "tuple": tuple, "type": type, "zip": zip,
            "True": True, "False": False, "None": None,
            "json": json, "re": re,
        }

        sandbox: dict[str, Any] = {"__builtins__": safe_builtins, "args": args}

        try:
            exec(code, sandbox)
            # Call main(args) if defined
            if "main" in sandbox and callable(sandbox["main"]):
                result = sandbox["main"](args)
                if isinstance(result, dict):
                    # Merge results back into state
                    if "answer" in result:
                        state["answer"] = result["answer"]
                    if "extracted_params" in result:
                        state["extracted_params"].update(result["extracted_params"])
                    # Store full return
                    state["code_output"] = result
                else:
                    state["code_output"] = result
            elif "result" in sandbox:
                state["code_output"] = sandbox["result"]
        except Exception as e:
            state["code_output"] = {"error": str(e)}

    elif node_type == "output":
        pass


def _resolve_variable(state: dict, path: str) -> Any:
    """Resolve a dot-path variable from state. E.g. 'extracted_params.name'"""
    parts = path.split(".")
    current: Any = state
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _apply_template(text: str, state: dict[str, Any]) -> str:
    """Apply variable substitution to any template string.

    Supported placeholders:
        {{query}}                — current user message
        {{answer}}               — current LLM answer
        {{student_id}}           — injected from inputs (student context)
        {{student_name}}         — same
        {{student_email}}        — same
        {{inputs.KEY}}           — any inputs field with explicit prefix
        {{EXTRACTED_FIELD}}      — any field from extracted_params
    """
    text = text.replace("{{query}}", state.get("query", ""))
    text = text.replace("{{answer}}", state.get("answer", ""))

    # inputs context (student info + any extra inputs)
    for k, v in (state.get("inputs") or {}).items():
        text = text.replace(f"{{{{inputs.{k}}}}}", str(v) if v is not None else "")
        text = text.replace(f"{{{{{k}}}}}", str(v) if v is not None else "")

    # extracted parameters
    for k, v in (state.get("extracted_params") or {}).items():
        text = text.replace(f"{{{{{k}}}}}", str(v) if v is not None else "")

    return text



async def _call_llm(
    provider_name: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Call LLM (non-streaming) and return full response text."""
    if provider_name == "openrouter":
        import openai
        client = openai.OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        result = client.chat.completions.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            messages=messages,
        )
        if not result.choices:
            return ""
        content = result.choices[0].message.content
        return content or ""  # normalize None → ""

    elif provider_name == "google":
        from google import genai
        from google.genai.types import Content, Part

        client = genai.Client(api_key=api_key)
        system_instruction = None
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append(Content(role=role, parts=[Part(text=msg["content"])]))

        result = client.models.generate_content(
            model=model if model.startswith("models/") else f"models/{model}",
            contents=contents,
            config={
                "system_instruction": system_instruction,
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            } if system_instruction else {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        return result.text or ""

    elif provider_name == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        system = ""
        chat_msgs = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_msgs.append({"role": msg["role"], "content": msg["content"]})

        result = client.messages.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            system=system, messages=chat_msgs,
        )
        return result.content[0].text if result.content else ""

    else:  # openai direct
        import openai
        client = openai.OpenAI(api_key=api_key)
        result = client.chat.completions.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            messages=messages,
        )
        if not result.choices:
            return ""
        content = result.choices[0].message.content
        return content or ""  # normalize None → ""
