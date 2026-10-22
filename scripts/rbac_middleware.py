"""
rbac_middleware.py — Sovereign OS RBAC enforcement layer
KI-048: All callers are already authenticated tailnet members.
This middleware enforces role-level and service-level permissions on top.
"""
import sqlite3, os
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

DB_PATH = "/home/james/stacklabs/dna/sovereign_now.db"
JWT_SECRET = os.getenv("SOVEREIGN_JWT_SECRET", "sovereign_secret_2026")
bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*allowed_roles: str):
    """Usage: Depends(require_role("pilot", "creator"))"""
    def dependency(user=Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Required role: {allowed_roles}")
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT active FROM sys_user WHERE user_name = ?", (user["user_name"],)
        ).fetchone()
        conn.close()
        if not row or row[0] != 1:
            raise HTTPException(status_code=403, detail="Account disabled")
        return user
    return dependency

def require_service_access(port: int, min_level: str = "read"):
    """Usage: Depends(require_service_access(8001, "full"))"""
    level_rank = {"none": 0, "read": 1, "full": 2}
    def dependency(user=Depends(get_current_user)):
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT access_level FROM sys_role_permission WHERE role = ? AND port = ?",
            (user.get("role"), port)
        ).fetchone()
        conn.close()
        if not row or level_rank.get(row[0], 0) < level_rank.get(min_level, 1):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.get('role')}' insufficient for this service"
            )
        return user
    return dependency
