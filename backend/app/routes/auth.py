from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt

from app.models.database import get_session, Superintendent
from app.models.schemas import LoginRequest, LoginResponse, BiometricVerifyRequest, BiometricVerifyResponse
from app.config import settings
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Authenticate with email and password.
    In a real system, this would verify passwords via Passlib.
    """
    # Mock authentication for demonstration
    if request.email == "admin@secureexam.com" and request.password == "admin123":
        user_id = str(uuid.uuid4())
        role = "admin"
        center_id = None
    else:
        # Check superintendent
        query = select(Superintendent).where(Superintendent.email == request.email)
        result = await session.execute(query)
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        user_id = str(user.id)
        role = "center"
        center_id = str(user.center_id)

    access_token_expires = timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    token_data = {"sub": user_id, "role": role}
    if center_id:
        token_data["center_id"] = center_id
        
    access_token = create_access_token(
        data=token_data, expires_delta=access_token_expires
    )
    
    await AuditService.log_action(session, "USER_LOGIN", metadata={"email": request.email})
    await session.commit()
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRY_MINUTES * 60
    )

@router.post("/biometric-verify", response_model=BiometricVerifyResponse)
async def biometric_verify(
    request: BiometricVerifyRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Verify biometric challenge token.
    Requires hardware-backed attestation in a real setup.
    """
    # Mock biometric verification
    verified = request.challenge_token.startswith("valid_")
    
    await AuditService.log_action(
        session, 
        "BIOMETRIC_VERIFY", 
        superintendent_id=request.superintendent_id,
        device_fingerprint=request.device_fingerprint,
        metadata={"verified": verified}
    )
    await session.commit()
    
    if verified:
        session_token = str(uuid.uuid4())
        return BiometricVerifyResponse(verified=True, session_token=session_token)
        
    raise HTTPException(status_code=401, detail="Biometric verification failed")

@router.post("/refresh")
async def refresh_token():
    """Endpoint for refreshing JWT tokens."""
    # Implementation depends on refresh token strategy (e.g. rotation, redis store)
    return {"detail": "Not implemented"}

@router.post("/logout")
async def logout():
    """Invalidate current token."""
    # Implementation would typically add the token to a Redis blacklist
    return {"detail": "Logged out successfully"}
