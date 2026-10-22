"""JWT auth, bcrypt, rate limiting, and FastAPI auth dependencies."""
import os
import sqlite3
import bcrypt
import jwt
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.db import DB_PATH, get_db




AUTH_ENV_PATH = "/home/james/stacklabs/scripts/.env.auth"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

def _get_jwt_secret() -> str:
    secret = os.getenv("SOVEREIGN_AUTH_SECRET")
    if not secret and os.path.exists(AUTH_ENV_PATH):
        with open(AUTH_ENV_PATH) as f:
            for line in f:
                if line.startswith("SOVEREIGN_AUTH_SECRET="):
                    secret = line.strip().split("=", 1)[1]
    if not secret:
        raise RuntimeError("SOVEREIGN_AUTH_SECRET not set. Run migration 001.")
    return secret

# In-memory rate limiter: {ip: [timestamp, ...]}
_login_attempts: dict = defaultdict(list)
RATE_LIMIT_WINDOW = 60   # seconds
RATE_LIMIT_MAX = 5

def _check_rate_limit(ip: str):
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    attempts = [t for t in _login_attempts[ip] if t > window_start]
    _login_attempts[ip] = attempts
    if len(attempts) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 60 seconds.")
    _login_attempts[ip].append(now)

def _get_user_modules(user_name: str) -> list[str]:
    """Return list of active module_name grants for a user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT m.module_name
        FROM m2m_user_module um
        JOIN sys_user u ON u.sys_id = um.user_sys_id
        JOIN sys_module m ON m.module_name = um.module_name
        WHERE u.user_name = ? AND um.active = 1 AND m.active = 1
        ORDER BY m.module_name
    """, (user_name,))
    modules = [r["module_name"] for r in c.fetchall()]
    conn.close()
    return modules

def _create_token(user_name: str, role: str, display_name: str, modules: list[str] | None = None) -> str:
    secret = _get_jwt_secret()
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_name,
        "role": role,
        "display_name": display_name,
        "modules": modules or [],
        "exp": exp,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

def _decode_token(token: str) -> dict:
    secret = _get_jwt_secret()
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def _get_user_from_db(user_name: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT user_name, password_hash, role, display_name, active, avatar_url, favorite_team, introduction, nap_mist_balance, layout_configuration, nap_mist_balance AS u_nap_mist_balance, layout_configuration AS u_layout_configuration FROM sys_user WHERE user_name=? AND active=1", (user_name,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _decode_token(credentials.credentials)

def require_pilot(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in ("pilot", "admin"):
        raise HTTPException(status_code=403, detail="Pilot access required")
    return user

def require_manager_or_pilot(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in ("pilot", "admin", "stack_manager"):
        raise HTTPException(status_code=403, detail="Manager or Pilot access required")
    return user
