"""
Centralized exception hierarchy.

Every domain raises one of these instead of a bare Exception, so the API
layer can map exception -> HTTP status + consistent error payload in one
place (see exception_handlers.py) instead of every endpoint doing its own
try/except translation.
"""

from typing import Any, Dict, Optional


class PlatformError(Exception):
    """Base class for all platform-raised errors."""

    default_message = "An unexpected error occurred."
    status_code = 500

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


# --- Validation ---
class ValidationError(PlatformError):
    default_message = "Input validation failed."
    status_code = 422


# --- Authentication / Authorization ---
class AuthenticationError(PlatformError):
    default_message = "Authentication failed."
    status_code = 401


class AccountLockedError(AuthenticationError):
    default_message = "Account is temporarily locked due to too many failed login attempts."
    status_code = 423


class InvalidRefreshTokenError(AuthenticationError):
    default_message = "Refresh token is invalid, expired, or has been revoked."
    status_code = 401


class DuplicateUserError(PlatformError):
    default_message = "Username or email is already registered."
    status_code = 409


class FeatureDisabledError(PlatformError):
    default_message = "This feature is not enabled on this deployment."
    status_code = 404


class AuthorizationError(PlatformError):
    default_message = "You do not have permission to perform this action."
    status_code = 403


# --- Model / Inference ---
class ModelNotFoundError(PlatformError):
    default_message = "The requested model is not registered."
    status_code = 404


class ModelInferenceError(PlatformError):
    default_message = "Model inference failed."
    status_code = 500


class ModelLoadError(PlatformError):
    default_message = "Failed to load model weights."
    status_code = 500


# --- Dataset ---
class DatasetError(PlatformError):
    default_message = "Dataset operation failed."
    status_code = 400


class DatasetNotFoundError(DatasetError):
    default_message = "The requested dataset was not found."
    status_code = 404


class DatasetValidationFailedError(DatasetError):
    default_message = "The uploaded dataset failed validation."
    status_code = 422


class EmptyDatasetError(DatasetError):
    default_message = "The dataset has no records to operate on."
    status_code = 400


# --- Evaluation ---
class UnsupportedEvaluationTaskError(PlatformError):
    default_message = "No evaluation baseline is registered for this task."
    status_code = 400


# --- Model Registry ---
class ModelRegistryError(PlatformError):
    default_message = "Model registry operation failed."
    status_code = 400


class ModelNotApprovedError(ModelRegistryError):
    default_message = "This model version has not been approved yet."
    status_code = 409


class InvalidStageTransitionError(ModelRegistryError):
    default_message = "That stage transition is not allowed from the model's current state."
    status_code = 409


# --- Training ---
class TrainingError(PlatformError):
    default_message = "Model training failed."
    status_code = 500


# --- Database ---
class DatabaseError(PlatformError):
    default_message = "A database error occurred."
    status_code = 500


class RecordNotFoundError(DatabaseError):
    default_message = "The requested record was not found."
    status_code = 404


# --- External services ---
class ExternalServiceError(PlatformError):
    default_message = "An external service call failed."
    status_code = 502


# --- Rate limiting ---
class RateLimitExceededError(PlatformError):
    default_message = "Rate limit exceeded. Please slow down."
    status_code = 429
