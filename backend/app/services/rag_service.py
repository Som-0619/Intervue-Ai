import os
import glob
import re
import uuid
import json
import hashlib
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

import fitz  # PyMuPDF
from app.core.config import settings
from app.models.domain import KnowledgeChunk
from app.schemas.pydantic_schemas import KnowledgeChunkDTO

logger = logging.getLogger(__name__)

# --- 1. ChunkingService ---
class ChunkingService:
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E]', ' ', text)
        lines = []
        for line in text.splitlines():
            sline = line.strip()
            if re.match(r'^[=\-]{3,}$', sline):
                continue
            if 'INTERVUEAI KNOWLEDGE BASE:' in sline:
                continue
            lines.append(line)
        text = "\n".join(lines)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @classmethod
    def chunk_document(
        cls,
        text: str,
        document_name: str,
        role_category: str,
        page_number: int = 1,
        chunk_size: int = 800,
        overlap: int = 150
    ) -> List[Dict[str, Any]]:
        cleaned = cls.clean_text(text)
        if not cleaned:
            return []

        chapter = "General Overview"
        chapter_match = re.search(r'(?:CHAPTER|SECTION)\s+\d+[:\s\-\_]*([^\n]+)', cleaned, re.IGNORECASE)
        if chapter_match:
            chapter = chapter_match.group(0).strip()

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(cleaned):
            end = start + chunk_size
            if end >= len(cleaned):
                chunk_text = cleaned[start:].strip()
                if len(chunk_text) > 30:
                    chunks.append(cls._create_chunk_dict(chunk_text, document_name, role_category, chapter, page_number, chunk_index))
                break

            break_pos = cleaned.rfind('. ', start, end)
            if break_pos == -1 or break_pos < start + (chunk_size // 2):
                break_pos = cleaned.rfind('\n', start, end)
            if break_pos == -1 or break_pos < start + (chunk_size // 2):
                break_pos = cleaned.rfind(' ', start, end)
            if break_pos == -1:
                break_pos = end

            chunk_text = cleaned[start:break_pos + 1].strip()
            if len(chunk_text) > 30:
                chunks.append(cls._create_chunk_dict(chunk_text, document_name, role_category, chapter, page_number, chunk_index))
                chunk_index += 1

            start = break_pos + 1 - overlap

        return chunks

    @staticmethod
    def _create_chunk_dict(
        chunk_text: str,
        document_name: str,
        role_category: str,
        chapter: str,
        page_number: int,
        chunk_index: int
    ) -> Dict[str, Any]:
        content_hash = hashlib.sha256(f"{document_name}_{chunk_text}".encode('utf-8')).hexdigest()
        first_line = chunk_text.split('\n')[0][:60]
        section = first_line if any(k in first_line.lower() for k in ["section", "overview", "design", "architecture", "security", "rag", "eval"]) else f"Section {chunk_index + 1}"

        return {
            "content_hash": content_hash,
            "document": document_name,
            "role_category": role_category,
            "chapter": chapter,
            "section": section,
            "page": page_number,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text
        }


# --- 2. EmbeddingService ---
class EmbeddingService:
    @staticmethod
    def _compute_dense_vector(text: str) -> List[float]:
        words = re.findall(r'\w+', text.lower())
        vocabulary = [
            "distributed", "system", "database", "cache", "redis", "kafka", "sql",
            "microservices", "concurrency", "async", "lock", "sharding", "index",
            "rag", "embedding", "vector", "llm", "transformer", "prompt", "eval",
            "fine-tuning", "bert", "attention", "loss", "gradient", "pytorch",
            "react", "state", "virtual", "dom", "hydration", "ssr", "rendering",
            "component", "hook", "typescript", "performance", "api", "security",
            "authentication", "authorization", "rate", "limit", "load", "balancer",
            "consistency", "replication", "partition", "transaction", "acid"
        ]
        counts = [words.count(term) for term in vocabulary]
        vec = np.array(counts, dtype=float)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @classmethod
    def embed_chunks(cls, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        embedded_chunks = []
        for chunk in chunks:
            vector = cls._compute_dense_vector(chunk["chunk_text"])
            chunk_copy = dict(chunk)
            chunk_copy["embedding"] = vector
            embedded_chunks.append(chunk_copy)
        return embedded_chunks


# --- 3. VectorStoreService ---
class VectorStoreService:
    @staticmethod
    def store_chunks(db: Session, chunks_with_embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        stored_count = 0
        skipped_count = 0

        existing_chunks = db.query(KnowledgeChunk).all()
        existing_hashes = set()
        for ec in existing_chunks:
            meta = ec.metadata_json or {}
            if "content_hash" in meta:
                existing_hashes.add(meta["content_hash"])

        new_db_objects = []
        for item in chunks_with_embeddings:
            chash = item["content_hash"]
            if chash in existing_hashes:
                skipped_count += 1
                continue

            chunk_id = f"chunk_{uuid.uuid4().hex[:10]}"
            metadata = {
                "content_hash": chash,
                "document": item["document"],
                "chapter": item["chapter"],
                "section": item["section"],
                "page": item["page"],
                "chunk_index": item["chunk_index"],
                "role_category": item["role_category"],
                "embedding": item["embedding"]
            }

            db_chunk = KnowledgeChunk(
                id=chunk_id,
                document_name=item["document"],
                role_category=item["role_category"],
                title=f"{item['document']} - P{item['page']} ({item['section']})",
                chunk_text=item["chunk_text"],
                metadata_json=metadata
            )
            new_db_objects.append(db_chunk)
            existing_hashes.add(chash)
            stored_count += 1

        if new_db_objects:
            db.bulk_save_objects(new_db_objects)
            db.commit()

        return {
            "stored_count": stored_count,
            "skipped_count": skipped_count
        }


# --- 4. KnowledgeIngestionService ---
class KnowledgeIngestionService:
    @classmethod
    def ingest_document(cls, db: Session, file_path: str, force_reindex: bool = False) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        doc_name = os.path.basename(file_path)
        # Derive role category from parent directory if present
        parent_dir = os.path.basename(os.path.dirname(file_path))
        if parent_dir in ["ai-ml", "backend", "frontend"]:
            role_cat = parent_dir.replace("-", " ").title() + " Engineer"
        else:
            role_cat = doc_name.split(".")[0].replace("_", " ").title()

        ext = os.path.splitext(file_path)[1].lower()

        if force_reindex:
            db.query(KnowledgeChunk).filter(KnowledgeChunk.document_name == doc_name).delete()
            db.commit()

        raw_chunks = []
        if ext == ".pdf":
            try:
                doc = fitz.open(file_path)
                for page_idx, page in enumerate(doc):
                    page_text = page.get_text("text")
                    if page_text.strip():
                        page_chunks = ChunkingService.chunk_document(
                            text=page_text,
                            document_name=doc_name,
                            role_category=role_cat,
                            page_number=page_idx + 1
                        )
                        raw_chunks.extend(page_chunks)
                doc.close()
            except Exception as e:
                logger.error(f"Error extracting PDF '{file_path}': {e}")
                raise ValueError(f"PDF extraction error: {e}")
        elif ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                full_text = f.read()
            raw_chunks = ChunkingService.chunk_document(
                text=full_text,
                document_name=doc_name,
                role_category=role_cat,
                page_number=1
            )
        else:
            return {"status": "skipped", "message": f"Unsupported format '{ext}'"}

        embedded = EmbeddingService.embed_chunks(raw_chunks)
        res = VectorStoreService.store_chunks(db, embedded)
        return {
            "document": doc_name,
            "total_extracted_chunks": len(embedded),
            "stored_chunks": res["stored_count"],
            "skipped_duplicates": res["skipped_count"]
        }

    @classmethod
    def ingest_all(cls, db: Session, force_reindex: bool = False) -> Dict[str, Any]:
        """Recursively scan knowledge-base/ directory and ingest all documents."""
        kb_dir = settings.KNOWLEDGE_BASE_DIR
        if not os.path.exists(kb_dir):
            os.makedirs(kb_dir, exist_ok=True)

        if force_reindex:
            db.query(KnowledgeChunk).delete()
            db.commit()

        results = []
        for root, _, files in os.walk(kb_dir):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in [".pdf", ".txt", ".md"]:
                    fpath = os.path.join(root, filename)
                    res = cls.ingest_document(db=db, file_path=fpath, force_reindex=False)
                    results.append(res)

        total_stored = sum(r.get("stored_chunks", 0) for r in results)
        total_skipped = sum(r.get("skipped_duplicates", 0) for r in results)

        logger.info(f"Recursive Knowledge Base Ingestion Complete: {total_stored} stored, {total_skipped} skipped.")
        return {
            "status": "success",
            "files_processed": len(results),
            "total_stored_chunks": total_stored,
            "total_skipped_duplicates": total_skipped,
            "details": results
        }


# --- 5. RetrievalService ---
class RetrievalService:
    @classmethod
    def retrieve_context(
        cls,
        db: Session,
        role: str,
        candidate_topics: Optional[List[str]] = None,
        resume_keywords: Optional[List[str]] = None,
        semantic_query: str = "",
        previously_used_chunk_ids: Optional[List[str]] = None,
        top_k: int = 3
    ) -> List[KnowledgeChunkDTO]:
        previously_used = set(previously_used_chunk_ids or [])
        all_chunks = db.query(KnowledgeChunk).all()
        if not all_chunks:
            KnowledgeIngestionService.ingest_all(db)
            all_chunks = db.query(KnowledgeChunk).all()

        if not all_chunks:
            return [
                KnowledgeChunkDTO(
                    id="chunk_fallback_01",
                    document_name="reference_standard.txt",
                    role_category=role,
                    title=f"{role} Standard Spec",
                    chunk_text=f"Core technical principles for {role}: scalable architecture, state management, security boundaries, and high availability.",
                    score=0.9,
                    metadata={"document": "reference_standard.txt", "page": 1, "section": "Core Standards"}
                )
            ]

        query_parts = [semantic_query]
        if candidate_topics:
            query_parts.extend(candidate_topics)
        if resume_keywords:
            query_parts.extend(resume_keywords)

        combined_query_text = " ".join([p for p in query_parts if p]).strip()
        query_vec = np.array(EmbeddingService._compute_dense_vector(combined_query_text))
        query_norm = np.linalg.norm(query_vec)

        scored_list = []
        for db_chunk in all_chunks:
            meta = db_chunk.metadata_json or {}
            emb = meta.get("embedding")
            
            sim = 0.0
            if emb:
                chunk_vec = np.array(emb)
                chunk_norm = np.linalg.norm(chunk_vec)
                if query_norm > 0 and chunk_norm > 0:
                    sim = float(np.dot(query_vec, chunk_vec) / (query_norm * chunk_norm))

            role_boost = 1.25 if role.lower() in db_chunk.role_category.lower() or db_chunk.role_category.lower() in role.lower() else 1.0
            reuse_penalty = 0.25 if db_chunk.id in previously_used else 1.0
            final_score = round(sim * role_boost * reuse_penalty, 4)

            dto = KnowledgeChunkDTO(
                id=db_chunk.id,
                document_name=db_chunk.document_name,
                role_category=db_chunk.role_category,
                title=db_chunk.title,
                chunk_text=db_chunk.chunk_text,
                score=final_score,
                metadata={
                    "document": meta.get("document", db_chunk.document_name),
                    "chapter": meta.get("chapter", "General"),
                    "section": meta.get("section", "Main"),
                    "page": meta.get("page", 1),
                    "chunk_index": meta.get("chunk_index", 0)
                }
            )
            scored_list.append(dto)

        scored_list.sort(key=lambda x: x.score or 0.0, reverse=True)
        top_chunks = scored_list[:top_k]

        retrieved_ids = [c.id for c in top_chunks]
        scores = [c.score for c in top_chunks]
        doc_metadata = [c.metadata for c in top_chunks]

        logger.info(f"RAG Retrieval | Query: '{semantic_query}' | Role: '{role}'")
        logger.info(f"Retrieved Chunk IDs: {retrieved_ids}")
        logger.info(f"Previously Used Chunk IDs: {list(previously_used)}")
        logger.info(f"Similarity Scores: {scores}")
        logger.info(f"Document Metadata: {doc_metadata}")

        return top_chunks


class RAGService:
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
        chunks = ChunkingService.chunk_document(text, "document.txt", "General", chunk_size=chunk_size, overlap=overlap)
        return [c["chunk_text"] for c in chunks]

    @staticmethod
    def ingest_documents(db: Session, force_reindex: bool = False) -> Dict[str, Any]:
        return KnowledgeIngestionService.ingest_all(db=db, force_reindex=force_reindex)

    @staticmethod
    def search_relevant_chunks(
        db: Session,
        query: str,
        target_role: str,
        previously_used_chunk_ids: Optional[List[str]] = None,
        top_k: int = 3
    ) -> List[KnowledgeChunkDTO]:
        return RetrievalService.retrieve_context(
            db=db,
            role=target_role,
            semantic_query=query,
            previously_used_chunk_ids=previously_used_chunk_ids,
            top_k=top_k
        )

