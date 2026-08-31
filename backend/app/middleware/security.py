import hmac
import hashlib
from typing import Optional
from fastapi import Request, HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from jose import JWTError, jwt

from app.config import settings

# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])

security_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security_scheme)) -> dict[str, str]:
    """Dependency to retrieve and validate JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"user_id": user_id, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def verify_api_key(request: Request) -> str:
    """Dependency for inter-service or client direct API key validation, if needed."""
    api_key = request.headers.get("X-API-Key")
    # For demonstration, validating a dummy static key; in production, validate against DB/Vault
    if not api_key or api_key != "static-trusted-client-key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    return api_key

class RequestSigningMiddleware:
    """
    Middleware to validate HMAC-SHA256 signature header on sensitive endpoints.
    Requires X-Signature header computed with a shared secret.
    """
    def __init__(self, secret: bytes):
        self.secret = secret

    async def __call__(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/exams") and request.method in ["POST", "PUT"]:
            signature = request.headers.get("X-Signature")
            if not signature:
                # Return standard 403 or intercept early, though middleware standard is to return Response
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=403, content={"detail": "Missing X-Signature header"})
            
            body = await request.body()
            computed_signature = hmac.new(self.secret, body, hashlib.sha256).hexdigest()
            
            if not hmac.compare_digest(signature, computed_signature):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=403, content={"detail": "Invalid signature"})
                
        response = await call_next(request)
        return response
