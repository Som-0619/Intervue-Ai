import os
import sys

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.core.database import SessionLocal, init_db
from app.services.rag_service import RAGService

def main():
    print("Initializing Database...")
    init_db()
    db = SessionLocal()
    try:
        print("Ingesting Knowledge Base documents...")
        result = RAGService.ingest_documents(db=db, force_reindex=True)
        print("Ingestion Result:", result)
    finally:
        db.close()

if __name__ == "__main__":
    main()
