"""FastAPI dependencies for auth. Wire these into endpoints with `Depends(...)`
rather than duplicating token-parsing logic in every route."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.auth.jwt_handler import decode_access_token
from backend.core.constants import UserRole
from backend.core.exceptions import AuthenticationError, RecordNotFoundError
from backend.database.session import get_db_session
from backend.repositories.user_repository import UserRepository
from backend.schemas.auth import CurrentUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session),
) -> CurrentUser:
    """
    Resolves the authenticated principal fresh from the database on every
    request, rather than trusting the role embedded in the JWT payload.
    This means a role change or deactivation takes effect immediately for
    new requests, without waiting for the access token to expire.
    """
    if token is None:
        raise AuthenticationError("Missing bearer token.")

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Token missing subject claim.")

    try:
        user = UserRepository(db).get(user_id)
    except RecordNotFoundError as exc:
        raise AuthenticationError("User no longer exists.") from exc

    if not user.is_active:
        raise AuthenticationError("This account has been deactivated.")

    return CurrentUser(user_id=user.id, username=user.username, role=UserRole(user.role))
