"""Password hashing. Kept as its own module (rather than inline in
AuthService) so the hashing scheme can be swapped/upgraded independently
of authentication logic — e.g. adding a legacy-scheme migration path
later without touching AuthService."""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)
