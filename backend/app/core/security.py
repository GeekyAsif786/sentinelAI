from datetime import UTC, datetime, timedelta
from enum import StrEnum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from app.core.config import Settings, get_settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


bearer_scheme = HTTPBearer(auto_error=False)



class RoleName(StrEnum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"
    auditor = "auditor"


class AuthenticatedUser(BaseModel):
    user_id: str
    email: EmailStr
    roles: set[RoleName]


def create_access_token(
    subject: str,
    email: str,
    roles: set[RoleName],
    settings: Settings,
) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    claims: dict[str, object] = {
        "sub": subject,
        "email": email,
        "roles": [role.value for role in roles],
        "exp": expires_at,
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        ) from exc

    subject = claims.get("sub")
    email = claims.get("email")
    raw_roles = claims.get("roles", [])
    if not isinstance(subject, str) or not isinstance(email, str) or not isinstance(raw_roles, list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    roles: set[RoleName] = set()
    for raw_role in raw_roles:
        if isinstance(raw_role, str):
            try:
                roles.add(RoleName(raw_role))
            except ValueError:
                continue

    if not roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No valid roles assigned")

    return AuthenticatedUser(user_id=subject, email=email, roles=roles)


def require_roles(*allowed_roles: RoleName):
    def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.roles.isdisjoint(set(allowed_roles)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency

