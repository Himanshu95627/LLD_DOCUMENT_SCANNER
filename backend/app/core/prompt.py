"""
Builds the final prompt sent to the LLM.

Key design decisions:
  - System prompt instructs the model to ONLY answer from provided context
  - Each chunk is labelled with its source file and page for traceability  
  - Explicitly tells the model to say "I don't know" if context is insufficient
    (this is what prevents hallucinations in RAG systems)
"""

from app.core.retriever import RetrievedChunk

SYSTEM_PROMPT = """You are a precise document assistant. Answer the user's question
using ONLY the context chunks provided below. 

Rules:
- If the answer is in the context, answer clearly and cite the source.
- If the answer is NOT in the context, say: "I don't have enough information in the
  provided documents to answer this question."
- Never make up information that isn't in the context.
- Keep answers concise and factual.
"""


def build_prompt(
    query: str,
    chunks: list[RetrievedChunk],
) -> list[dict]:
    """
    Returns a messages list ready to pass to the OpenAI chat completions API.
    """
    # Format each chunk with its source info
    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk.filename
        if chunk.page_number:
            source += f", page {chunk.page_number}"
        context_parts.append(
            f"[Chunk {i} | Source: {source} | Similarity: {chunk.similarity_score:.2f}]\n"
            f"{chunk.content}"
        )

    context_text = "\n\n---\n\n".join(context_parts)

    user_message = f"""Context from documents:
{context_text}

---

Question: {query}"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
