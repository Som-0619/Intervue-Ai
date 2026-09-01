import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pydantic_schemas import IngestionRequest, KnowledgeChunkDTO
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/ingest")
def trigger_ingestion(payload: IngestionRequest, db: Session = Depends(get_db)):
    try:
        res = RAGService.ingest_documents(db=db, force_reindex=payload.force_reindex)
        return res
    except Exception as e:
        logger.error(f"Error during RAG ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to ingest knowledge base documents.")

@router.get("/search", response_model=List[KnowledgeChunkDTO])
def search_knowledge_base(
    query: str = Query(..., description="Semantic search query"),
    target_role: str = Query("Backend Engineer", description="Target job role"),
    top_k: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db)
):
    try:
        results = RAGService.search_relevant_chunks(db=db, query=query, target_role=target_role, top_k=top_k)
        return results
    except Exception as e:
        logger.error(f"Error during RAG vector search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to execute knowledge base search.")
