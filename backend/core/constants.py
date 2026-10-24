"""Platform-wide constants. Values that are configuration (change per
environment) belong in config/settings.py instead — this file is only for
values that are true constants regardless of environment."""

from enum import Enum


class NLPTask(str, Enum):
    """Every task the platform serves. Each one has a registered plugin and
    a real model behind it (see backend/plugins/__init__.py) — a task is
    only added here once it works end to end."""

    SENTIMENT_ANALYSIS = "sentiment_analysis"
    EMOTION_DETECTION = "emotion_detection"
    TOPIC_CLASSIFICATION = "topic_classification"
    TOXICITY_DETECTION = "toxicity_detection"
    LANGUAGE_DETECTION = "language_detection"
    ZERO_SHOT_CLASSIFICATION = "zero_shot_classification"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    TEXT_EMBEDDINGS = "text_embeddings"


class ModelArchitecture(str, Enum):
    BERT = "bert"
    ROBERTA = "roberta"
    DEBERTA = "deberta"
    DISTILBERT = "distilbert"
    XLM_ROBERTA = "xlm_roberta"
    SENTENCE_TRANSFORMER = "sentence_transformer"


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelLifecycleStage(str, Enum):
    """Where a registered model sits in its promotion path. Only APPROVED
    models can be promoted to PRODUCTION (enforced in
    backend/services/model_registry_service.py, not just documented here)."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DeploymentStatus(str, Enum):
    NOT_DEPLOYED = "not_deployed"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"


class DatasetStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    ARCHIVED = "archived"


class UserRole(str, Enum):
    """
    Enterprise role set. ANALYST and VIEWER are kept as backward-compatible
    aliases for BUSINESS_ANALYST and READ_ONLY_USER respectively — anything
    already storing/checking those values keeps working (see rbac.py, which
    grants them identical permissions to their modern counterparts).
    """

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    ML_ENGINEER = "ml_engineer"
    NLP_ENGINEER = "nlp_engineer"
    DATA_SCIENTIST = "data_scientist"
    REVIEWER = "reviewer"
    BUSINESS_ANALYST = "business_analyst"
    AUDITOR = "auditor"
    READ_ONLY_USER = "read_only_user"

    # --- Legacy aliases (pre-dating the 9-role expansion) ---
    ANALYST = "analyst"
    VIEWER = "viewer"


MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 32
