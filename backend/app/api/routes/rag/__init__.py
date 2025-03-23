from fastapi import APIRouter
from app.api.routes.rag import status, graph, config, indexes, retrieval, chunks

router = APIRouter()

# Include sub-routers
router.include_router(status.router, tags=["rag"])
router.include_router(graph.router, tags=["rag"])
router.include_router(config.router, tags=["rag"])
router.include_router(indexes.router, tags=["rag"])
router.include_router(retrieval.router, tags=["rag"])
router.include_router(chunks.router, tags=["rag"])