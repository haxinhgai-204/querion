"""Retrieval service — embed query → pgvector similarity search → top_k chunks."""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AiProvider
from app.services.encryption import decrypt_key

logger = logging.getLogger(__name__)

# Retry configuration for transient embedding API failures
EMBED_MAX_RETRIES = 5
EMBED_RETRY_DELAY = 2.0  # seconds, doubles each retry


async def get_active_embedding_provider(db: AsyncSession) -> AiProvider | None:
    """Get the first active embedding provider."""
    from sqlalchemy import select
    result = await db.execute(
        select(AiProvider).where(
            AiProvider.is_active == True,
            AiProvider.purpose == "embedding",
        ).order_by(AiProvider.created_at).limit(1)
    )
    return result.scalar_one_or_none()


async def embed_query(query: str, provider: AiProvider) -> list[float]:
    """Embed a single query string using the active provider.

    Includes retry logic for transient failures (e.g. OpenRouter cold start).
    """
    api_key = decrypt_key(provider.api_key_encrypted)
    last_error: Exception | None = None

    for attempt in range(1, EMBED_MAX_RETRIES + 1):
        try:
            vec = await _do_embed(query, provider.provider_name, api_key, provider.model_name)

            # Pad to 1536 if needed
            if len(vec) < 1536:
                vec = vec + [0.0] * (1536 - len(vec))

            if attempt > 1:
                logger.info(f"[embed_query] Succeeded on attempt {attempt}")
            return vec[:1536]

        except Exception as e:
            last_error = e
            logger.warning(
                f"[embed_query] Attempt {attempt}/{EMBED_MAX_RETRIES} failed "
                f"(provider={provider.provider_name}, model={provider.model_name}): {e}"
            )
            if attempt < EMBED_MAX_RETRIES:
                delay = EMBED_RETRY_DELAY * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

    # All retries exhausted
    raise last_error  # type: ignore[misc]


async def _do_embed(query: str, provider_name: str, api_key: str, model_name: str) -> list[float]:
    """Perform the actual embedding call. Runs sync clients in a thread to avoid blocking the event loop."""

    # Base URLs for OpenAI-compatible proxy providers
    _PROVIDER_URLS = {
        "openrouter": "https://openrouter.ai/api/v1",
        "vilao": "https://api.vilao.ai/v1",
    }

    if provider_name == "google":
        def _google_embed():
            from google import genai
            client = genai.Client(api_key=api_key)
            mn = model_name if model_name.startswith("models/") else f"models/{model_name}"
            result = client.models.embed_content(model=mn, contents=[query])
            return list(result.embeddings[0].values)
        return await asyncio.to_thread(_google_embed)

    else:  # openai-compatible: openai, openrouter, vilao, etc.
        def _openai_compat_embed():
            import openai
            base_url = _PROVIDER_URLS.get(provider_name)
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            client = openai.OpenAI(**kwargs)
            response = client.embeddings.create(input=[query], model=model_name)
            return response.data[0].embedding
        return await asyncio.to_thread(_openai_compat_embed)


async def retrieve(
    db: AsyncSession,
    query: str,
    dataset_ids: list[UUID],
    top_k: int = 5,
    similarity_threshold: float = 0.35,
) -> list[dict]:
    """Embed query → pgvector cosine search → return top_k chunks.

    Returns list of:
        {chunk_id, content, score, document_id, dataset_id, chunk_index}
    """
    provider = await get_active_embedding_provider(db)
    if not provider:
        return []

    query_embedding = await embed_query(query, provider)
    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # pgvector cosine distance: 1 - cosine_similarity
    # Lower distance = more similar
    dataset_ids_str = ",".join(f"'{str(d)}'" for d in dataset_ids)

    sql = text(f"""
        SELECT
            c.id AS chunk_id,
            c.content,
            c.chunk_index,
            c.document_id,
            c.dataset_id,
            d.filename,
            (e.embedding <=> CAST(:query_vec AS vector)) AS distance
        FROM chunks c
        JOIN embeddings e ON e.chunk_id = c.id
        JOIN documents d ON d.id = c.document_id
        WHERE c.dataset_id IN ({dataset_ids_str})
        ORDER BY distance ASC
        LIMIT :top_k
    """)

    result = await db.execute(sql, {"query_vec": vec_str, "top_k": top_k})
    rows = result.fetchall()

    return [
        {
            "chunk_id": str(row.chunk_id),
            "content": row.content,
            "content_preview": row.content[:200] if row.content else "",
            "chunk_index": row.chunk_index,
            "document_id": str(row.document_id),
            "dataset_id": str(row.dataset_id),
            "filename": row.filename,
            "score": round(1 - row.distance, 4),
        }
        for row in rows
        if (1 - row.distance) >= similarity_threshold
    ]
