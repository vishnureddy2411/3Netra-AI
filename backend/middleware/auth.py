"""
backend/middleware/auth.py

JWT verification using Supabase admin client.
Reads token directly from Authorization header.
"""

import logging
import os

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


async def verify_token(request: Request) -> dict:
    """
    Reads Bearer token from Authorization header.
    Verifies using Supabase admin client.
    """
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Authorization header missing or invalid"
            )

        token = auth_header.split(" ")[1]

        from supabase import create_client
        url = os.getenv("SUPABASE_URL", "").replace("/rest/v1", "").rstrip("/")
        key = os.getenv("SUPABASE_KEY", "")

        if not url or not key:
            raise HTTPException(status_code=500, detail="Supabase config missing")

        supabase = create_client(url, key)
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user = user_response.user
        request.state.user_id    = user.id
        request.state.user_email = user.email or ""

        logger.info(f"Auth verified: user={user.id} email={user.email}")
        return {"sub": user.id, "email": user.email}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


class AuthDependency:
    """
    FastAPI dependency — reads token from headers directly.
    No HTTPBearer injection that conflicts with request body.
    """
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        try:
            return await verify_token(request)
        except HTTPException:
            if self.auto_error:
                raise
            return None


# Convenience instance
require_auth = AuthDependency()