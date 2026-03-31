"""Chat service — retrieval + LLM streaming for RAG chat."""

import json
from uuid import UUID
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_provider import AiProvider
from app.services.encryption import decrypt_key
from app.services.retrieval import retrieve


SYSTEM_PROMPT = """You are a friendly, knowledgeable AI assistant who has thoroughly read and understood the user's documents. Think of yourself as a helpful colleague who knows the material well.

Personality:
- Be warm, conversational, and natural — not robotic or overly formal.
- Show genuine interest in helping the user explore their documents.
- Use a friendly tone, add brief commentary or insights when helpful.

How to answer:
- For greetings or casual chat, respond naturally. You can mention you're ready to help with their documents.
- For document-related questions, answer thoroughly using the context below. Cite sources with [#0], [#1] etc.
- If you can partially answer, do your best and note what's missing.
- If the context doesn't cover the question, say so honestly and suggest related topics the documents DO cover.
- Feel free to summarize, compare, or offer insights that connect different parts of the context.
- Always respond in the same language the user uses.

Document Context:
{context}
"""


async def get_active_llm_provider(db: AsyncSession) -> AiProvider | None:
    """Get the first active LLM provider."""
    result = await db.execute(
        select(AiProvider).where(
            AiProvider.is_active == True,
            AiProvider.purpose == "llm",
        ).order_by(AiProvider.created_at).limit(1)
    )
    return result.scalar_one_or_none()


async def chat_stream(
    db: AsyncSession,
    query: str,
    dataset_id: UUID,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """Stream a RAG chat response.

    1. Retrieve relevant chunks from pgvector
    2. Build prompt with context
    3. Stream LLM response

    Yields SSE-formatted strings: data: {"type": "...", "content": "..."}
    """
    # 1. Retrieve relevant chunks
    sources = await retrieve(db=db, query=query, dataset_ids=[dataset_id], top_k=5)

    # Send sources first
    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

    # 2. Get LLM provider
    provider = await get_active_llm_provider(db)
    if not provider:
        yield f"data: {json.dumps({'type': 'error', 'content': 'No active LLM provider configured. Add one in Admin → Settings.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # 3. Build context from chunks
    context_parts = []
    for i, src in enumerate(sources):
        context_parts.append(f"[#{i}] {src['content']}")
    context = "\n\n".join(context_parts) if context_parts else "No relevant context found."

    # 4. Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(context=context)}]
    # Add conversation history (last 10 messages)
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    # 5. Stream LLM response
    api_key = decrypt_key(provider.api_key_encrypted)

    try:
        if provider.provider_name == "google":
            async for chunk in _stream_google(api_key, provider.model_name, messages):
                yield chunk
        elif provider.provider_name == "anthropic":
            async for chunk in _stream_anthropic(api_key, provider.model_name, messages):
                yield chunk
        else:  # openai
            async for chunk in _stream_openai(api_key, provider.model_name, messages):
                yield chunk
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    yield "data: [DONE]\n\n"


async def _stream_openai(api_key: str, model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    """Stream from OpenAI API using async client."""
    import openai
    client = openai.AsyncOpenAI(api_key=api_key)

    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"


async def _stream_google(api_key: str, model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    """Stream from Google Gemini API using thread executor for sync SDK."""
    import asyncio
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

    model_name = model if model.startswith("models/") else f"models/{model}"
    config = {"system_instruction": system_instruction} if system_instruction else None

    # Run sync streaming in thread, push chunks through queue
    queue: asyncio.Queue = asyncio.Queue()

    def _run_sync():
        response = client.models.generate_content_stream(
            model=model_name, contents=contents, config=config,
        )
        for chunk in response:
            if chunk.text:
                queue.put_nowait(chunk.text)
        queue.put_nowait(None)  # sentinel

    loop = asyncio.get_event_loop()
    task = loop.run_in_executor(None, _run_sync)

    while True:
        # Poll queue with short sleep to yield control
        try:
            text = queue.get_nowait()
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.01)
            continue
        if text is None:
            break
        yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"

    await task  # ensure thread completed


async def _stream_anthropic(api_key: str, model: str, messages: list[dict]) -> AsyncGenerator[str, None]:
    """Stream from Anthropic API using async client."""
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=api_key)

    system = ""
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system = msg["content"]
        else:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})

    async with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=system,
        messages=chat_messages,
    ) as stream:
        async for text in stream.text_stream:
            yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"


async def generate_title(db: AsyncSession, user_message: str, assistant_response: str) -> str | None:
    """Use LLM to generate a short conversation title from the first exchange."""
    import asyncio
    provider = await get_active_llm_provider(db)
    if not provider:
        return user_message[:80] if len(user_message) > 3 else None

    api_key = decrypt_key(provider.api_key_encrypted)

    prompt = f"""Based on this user message, generate a short conversation title (3-6 words) that describes WHAT THE USER IS ASKING ABOUT. The title should be a neutral topic label, like a document heading. Use the same language as the user. Reply with ONLY the title text, nothing else.

User message: {user_message[:300]}"""

    try:
        if provider.provider_name == "google":
            from google import genai
            client = genai.Client(api_key=api_key)
            model = provider.model_name if provider.model_name.startswith("models/") else f"models/{provider.model_name}"
            result = await asyncio.to_thread(
                client.models.generate_content, model=model, contents=[prompt]
            )
            return result.text.strip()[:120] if result.text else None
        elif provider.provider_name == "anthropic":
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)
            result = await client.messages.create(
                model=provider.model_name, max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            return result.content[0].text.strip()[:120] if result.content else None
        else:  # openai
            import openai
            client = openai.AsyncOpenAI(api_key=api_key)
            result = await client.chat.completions.create(
                model=provider.model_name, max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            return result.choices[0].message.content.strip()[:120] if result.choices else None
    except:
        return user_message[:80] if len(user_message) > 3 else None

