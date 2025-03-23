from fastapi import APIRouter
from app.api.routes.rag import status, graph, config, indexes, retrieval, chunks

# Create a router that includes all the sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(status.router)
router.include_router(graph.router)
router.include_router(config.router)
router.include_router(indexes.router)
router.include_router(retrieval.router)
router.include_router(chunks.router)