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
) -> dict[str, Any]:
    """Execute a validated workflow/chatflow graph and return answer + citations.

    Args:
        history: conversation history for chatflow memory (list of {role, content})
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
    }

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

        # Log step start (if observability enabled)
        step = None
        if run:
            step = await log_step_start(db, run_id=run.id, node_id=current_id, node_type=node_type,
                                        input_data={"query": state["query"][:200]})

        await _execute_node(db, node_type, node_data, state)

        # Log step end
        if run and step:
            output_preview = {"answer": state.get("answer", "")[:200]}
            if state.get("extracted_params"):
                output_preview["extracted_params"] = state["extracted_params"]
            await log_step_end(step, output_data=output_preview)

        # Find next node
        outgoing = adj.get(current_id, [])
        if not outgoing:
            break
        elif node_type == "if_else" and len(outgoing) >= 2:
            # If/else: pick branch based on condition result
            branch = state.get("_branch", "true")
            # Convention: first edge = true, second edge = false
            # Or use sourceHandle: "true"/"false"
            true_edge = None
            false_edge = None
            for edge in outgoing:
                handle = edge.get("sourceHandle", "")
                if handle == "false" or edge == outgoing[-1]:
                    false_edge = edge
                else:
                    true_edge = edge
            if len(outgoing) == 2:
                true_edge = outgoing[0]
                false_edge = outgoing[1]

            current_id = true_edge["target"] if branch == "true" else false_edge["target"]
        else:
            current_id = outgoing[0]["target"]

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

        prompt_text = template.replace("{{query}}", state["query"])
        prompt_text = prompt_text.replace("{{context}}", context)
        prompt_text = prompt_text.replace("{{system_prompt}}", node_data.get("system_prompt", ""))

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
        state["answer"] = answer

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

        # Replace variables in body template
        body_str = body_template
        body_str = body_str.replace("{{query}}", state["query"])
        body_str = body_str.replace("{{answer}}", state.get("answer", ""))
        # Replace extracted params
        for k, v in state.get("extracted_params", {}).items():
            body_str = body_str.replace(f"{{{{{k}}}}}", str(v) if v is not None else "")

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
        # If no template, keep existing answer from llm_generate

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


async def _call_llm(
    provider_name: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Call LLM (non-streaming) and return full response text."""
    if provider_name == "google":
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

    else:  # openai
        import openai
        client = openai.OpenAI(api_key=api_key)
        result = client.chat.completions.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            messages=messages,
        )
        return result.choices[0].message.content if result.choices else ""
