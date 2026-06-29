"""
Embedding wrapper around OpenAI's text-embedding-3-small.

Why a wrapper instead of calling OpenAI directly everywhere?
  - One place to swap the model (e.g. to a local model later)
  - Batching: OpenAI allows up to 2048 inputs per request
  - Consistent error handling and logging
"""

# from openai import AsyncOpenAI

# from app.core.config import settings

# _client = AsyncOpenAI(api_key=settings.openai_api_key)

# # OpenAI's max inputs per embedding request
# _BATCH_SIZE = 512


# async def embed_texts(texts: list[str]) -> list[list[float]]:
#     """
#     Embed a list of texts. Handles batching automatically.
#     Returns embeddings in the same order as input texts.
#     """
#     if not texts:
#         return []

#     all_embeddings: list[list[float]] = []

#     # Process in batches to stay within API limits
#     for i in range(0, len(texts), _BATCH_SIZE):
#         batch = texts[i : i + _BATCH_SIZE]

#         response = await _client.embeddings.create(
#             model=settings.embedding_model,
#             input=batch,
#             dimensions=settings.embedding_dimensions,
#         )

#         # OpenAI returns embeddings in the same order as inputs
#         batch_embeddings = [item.embedding for item in response.data]
#         all_embeddings.extend(batch_embeddings)

#     return all_embeddings


# async def embed_query(query: str) -> list[float]:
#     """
#     Embed a single query string.
#     Convenience wrapper around embed_texts for the query path.
#     """
#     results = await embed_texts([query])
#     return results[0]


from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")  # 80MB, downloads once

async def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = _model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()

async def embed_query(query: str) -> list[float]:
    return (await embed_texts([query]))[0]