from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://rag_user:rag_pass@localhost:5432/rag_db"

    # OpenAI
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    llm_model: str = "gpt-4o-mini"

    # Chunking
    chunk_size: int = 200       # tokens
    chunk_overlap: int = 20     # tokens

    # Retrieval
    top_k: int = 10             # chunks from vector DB
    rerank_top_n: int = 3       # chunks passed to LLM after reranking

    # Phase 2 — reranker
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    use_reranker: bool = True   # set False to skip reranking (faster, less accurate)

    # Phase 2 — hybrid search
    use_hybrid_search: bool = True   # combine vector + BM25; set False for vector-only

    # Phase 2 — debug / observability
    track_latency: bool = True  # adds per-step timing to query response


settings = Settings()
