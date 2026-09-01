import datetime
import logging
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.api.router import api_router
from app.services.rag_service import RAGService

# Configure server-side logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("intervue_ai")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup DB init
    init_db()
    
    # Auto-ingest knowledge base documents if present
    db = SessionLocal()
    try:
        RAGService.ingest_documents(db=db, force_reindex=False)
    except Exception as e:
        logger.warning(f"Warning during initial RAG ingestion: {e}")
    finally:
        db.close()
        
    yield

app = FastAPI(
    title="IntervueAI Backend API",
    description="Production-grade AI-powered role-based technical interview platform with RAG grounding.",
    version="1.0.0",
    lifespan=lifespan
)

# Centralized Exception Handlers for Structured Error Responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Request Validation Error",
                "details": exc.errors(),
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Internal Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "An internal server error occurred. Please try again later.",
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
            }
        }
    )

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {
        "status": "online",
        "app": "IntervueAI Backend",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
