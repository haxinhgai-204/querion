"""Retrieval service — embed query → pgvector similarity search → top_k chunks."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AiProvider
from app.services.encryption import decrypt_key


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
    """Embed a single query string using the active provider."""
    api_key = decrypt_key(provider.api_key_encrypted)

    if provider.provider_name == "google":
        from google import genai
        client = genai.Client(api_key=api_key)
        model_name = provider.model_name
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        result = client.models.embed_content(model=model_name, contents=[query])
        vec = list(result.embeddings[0].values)
    else:
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(input=[query], model=provider.model_name)
        vec = response.data[0].embedding

    # Pad to 1536 if needed
    if len(vec) < 1536:
        vec = vec + [0.0] * (1536 - len(vec))
    return vec[:1536]


async def retrieve(
    db: AsyncSession,
    query: str,
    dataset_ids: list[UUID],
    top_k: int = 5,
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
    ]
