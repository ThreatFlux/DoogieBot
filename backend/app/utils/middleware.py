from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)

class TrailingSlashMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle trailing slashes in routes.
    This middleware is now disabled - it just passes requests through without redirection.
    We're using this approach to maintain compatibility while we fix URL handling issues.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app
    
    async def dispatch(self, request: Request, call_next):
        # Simply pass the request through without redirection
        # No more redirects for now - let the app handle paths as they come
        response = await call_next(request)
        return response
