import pytest
from app.services.rag_service import (
    ChunkingService, EmbeddingService, VectorStoreService,
    KnowledgeIngestionService, RetrievalService, RAGService
)
from app.core.database import SessionLocal, init_db

def test_chunking_service_metadata_and_overlap():
    sample_text = """
    SECTION 1: High-Throughput System Architecture
    Distributed caching systems like Redis mitigate database query overhead.
    B-Tree and LSM-tree indices offer distinct read and write performance characteristics under heavy load.
    """ * 10

    chunks = ChunkingService.chunk_document(
        text=sample_text,
        document_name="backend_engineering.txt",
        role_category="Backend Engineer",
        page_number=2,
        chunk_size=700,
        overlap=150
    )

    assert len(chunks) >= 1
    first_chunk = chunks[0]
    assert first_chunk["document"] == "backend_engineering.txt"
    assert first_chunk["role_category"] == "Backend Engineer"
    assert first_chunk["page"] == 2
    assert "content_hash" in first_chunk
    assert "SECTION 1" in first_chunk["chapter"] or "General" in first_chunk["chapter"]

def test_embedding_service():
    chunk = {
        "chunk_text": "RAG architecture uses dense vector embeddings and Large Language Models for grounded retrieval."
    }
    embedded = EmbeddingService.embed_chunks([chunk])
    assert len(embedded) == 1
    assert "embedding" in embedded[0]
    assert len(embedded[0]["embedding"]) == 50

def test_idempotent_ingestion():
    init_db()
    db = SessionLocal()
    try:
        # First ingestion run
        res1 = KnowledgeIngestionService.ingest_all(db, force_reindex=True)
        stored_first_run = res1["total_stored_chunks"]
        assert stored_first_run > 0

        # Second ingestion run without force_reindex
        res2 = KnowledgeIngestionService.ingest_all(db, force_reindex=False)
        assert res2["total_stored_chunks"] == 0
        assert res2["total_skipped_duplicates"] >= stored_first_run
    finally:
        db.close()

def test_retrieval_service_query():
    init_db()
    db = SessionLocal()
    try:
        # Ingest
        KnowledgeIngestionService.ingest_all(db, force_reindex=True)

        # Search with role, candidate topics, resume keywords, and semantic query
        results = RetrievalService.retrieve_context(
            db=db,
            role="Backend Engineer",
            candidate_topics=["Database Indexing", "Caching"],
            resume_keywords=["Redis", "PostgreSQL", "B-Tree"],
            semantic_query="How do LSM-trees compare to B-Trees for write-heavy database workloads?",
            top_k=3
        )

        assert len(results) > 0
        top_chunk = results[0]
        assert top_chunk.score > 0.0
        assert top_chunk.metadata is not None
        assert "document" in top_chunk.metadata
        assert "page" in top_chunk.metadata
    finally:
        db.close()
