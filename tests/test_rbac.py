import pytest

from backend.auth.rbac import has_permission, require_permission
from backend.core.constants import UserRole
from backend.core.exceptions import AuthorizationError


def test_super_admin_and_admin_have_every_permission():
    assert has_permission(UserRole.SUPER_ADMIN, "anything:at-all")
    assert has_permission(UserRole.ADMIN, "model:train")


def test_ml_engineer_and_nlp_engineer_can_train_and_infer():
    for role in (UserRole.ML_ENGINEER, UserRole.NLP_ENGINEER):
        assert has_permission(role, "model:train")
        assert has_permission(role, "model:infer")
        assert has_permission(role, "dataset:write")


def test_data_scientist_can_write_datasets_but_not_train():
    assert has_permission(UserRole.DATA_SCIENTIST, "dataset:write")
    assert has_permission(UserRole.DATA_SCIENTIST, "report:read")
    assert not has_permission(UserRole.DATA_SCIENTIST, "model:train")


def test_reviewer_has_review_permissions_only():
    assert has_permission(UserRole.REVIEWER, "review:write")
    assert not has_permission(UserRole.REVIEWER, "model:train")
    assert not has_permission(UserRole.REVIEWER, "dataset:write")


def test_auditor_has_audit_read_but_nothing_else():
    assert has_permission(UserRole.AUDITOR, "audit:read")
    assert not has_permission(UserRole.AUDITOR, "model:train")
    assert not has_permission(UserRole.AUDITOR, "dataset:write")


def test_read_only_user_cannot_train_but_can_infer():
    assert has_permission(UserRole.READ_ONLY_USER, "model:infer")
    assert not has_permission(UserRole.READ_ONLY_USER, "model:train")


def test_legacy_viewer_matches_read_only_user_grants():
    assert has_permission(UserRole.VIEWER, "model:infer")
    assert not has_permission(UserRole.VIEWER, "model:train")


def test_legacy_analyst_matches_business_analyst_grants():
    assert has_permission(UserRole.ANALYST, "report:read")
    assert has_permission(UserRole.BUSINESS_ANALYST, "report:read")
    assert not has_permission(UserRole.ANALYST, "model:train")


def test_require_permission_raises_for_denied_role():
    with pytest.raises(AuthorizationError):
        require_permission(UserRole.READ_ONLY_USER, "model:train")


def test_require_permission_passes_silently_for_granted_role():
    require_permission(UserRole.SUPER_ADMIN, "model:train")
    require_permission(UserRole.ML_ENGINEER, "model:infer")
