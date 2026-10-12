"""Small, dependency-free validation helpers shared across services.
Pydantic schemas handle most request validation; these cover checks that
don't fit naturally into a schema field validator."""

from backend.core.exceptions import ValidationError


def require_non_empty_text(text: str, field_name: str = "text") -> None:
    if not text or not text.strip():
        raise ValidationError(f"'{field_name}' must not be empty or whitespace-only.")


def require_max_length(text: str, max_length: int, field_name: str = "text") -> None:
    if len(text) > max_length:
        raise ValidationError(
            f"'{field_name}' exceeds maximum length of {max_length} characters "
            f"(got {len(text)})."
        )
