"""
backend/routes/auth_routes.py

User profile and auth-related endpoints.
Supabase handles actual login/signup on the frontend.
Backend only needs to verify tokens and manage user data.

Endpoints:
  GET  /api/auth/me        — get current user profile
  POST /api/auth/profile   — update user profile
"""

import logging
import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from middleware.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


class ProfileUpdate(BaseModel):
    full_name: str = ""
    target_role: str = ""
    purpose: str = ""


@router.get("/auth/me")
async def get_current_user(
    request: Request,
    auth=Depends(require_auth),
):
    """
    Returns the current authenticated user's info.
    Used by frontend to verify auth state on load.
    """
    try:
        return JSONResponse({
            "success": True,
            "user": {
                "id": request.state.user_id,
                "email": request.state.user_email,
            }
        })
    except Exception as e:
        logger.error(f"Get user failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/auth/profile")
async def update_profile(
    request: Request,
    body: ProfileUpdate,
    auth=Depends(require_auth),
):
    """
    Updates user profile in Supabase.
    Stores role and purpose preferences.
    """
    try:
        from supabase import create_client

        url  = os.getenv("SUPABASE_URL", "")
        key  = os.getenv("SUPABASE_KEY", "")
        supabase = create_client(url, key)

        user_id = request.state.user_id

        # Upsert user profile
        result = supabase.table("user_profiles").upsert({
            "user_id": user_id,
            "full_name": body.full_name,
            "target_role": body.target_role,
            "purpose": body.purpose,
            "updated_at": "now()",
        }).execute()

        return JSONResponse({
            "success": True,
            "profile": result.data[0] if result.data else {},
        })

    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )