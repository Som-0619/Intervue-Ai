from fastapi import APIRouter
from app.api.endpoints import candidates, interviews, rag, reports

api_router = APIRouter()
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
