import type { UserRole } from "@/types/api";

/**
 * Mirrors backend/auth/rbac.py's permission table, for UI purposes only —
 * showing/hiding a button based on this is a convenience so people don't
 * click something that will 403, not a security control. The backend
 * re-checks every one of these independently on every request; if this
 * table ever drifts out of sync with the backend, the worst case is a
 * button that's shown-but-403s or hidden-but-would-have-worked, not a
 * permission bypass.
 */
const ROLE_PERMISSIONS: Record<UserRole, Set<string> | "*"> = {
  super_admin: "*",
  admin: "*",
  ml_engineer: new Set(["model:train", "model:infer", "dataset:write", "dataset:read", "experiment:write", "experiment:read"]),
  nlp_engineer: new Set(["model:train", "model:infer", "dataset:write", "dataset:read", "experiment:write", "experiment:read"]),
  data_scientist: new Set(["model:infer", "dataset:write", "dataset:read", "experiment:write", "experiment:read", "report:read"]),
  reviewer: new Set(["model:infer", "review:read", "review:write", "experiment:read"]),
  business_analyst: new Set(["model:infer", "experiment:read", "report:read"]),
  analyst: new Set(["model:infer", "experiment:read", "report:read"]),
  auditor: new Set(["audit:read", "experiment:read", "report:read"]),
  read_only_user: new Set(["model:infer", "experiment:read"]),
  viewer: new Set(["model:infer", "experiment:read"]),
};

const APPROVAL_ROLES: UserRole[] = ["reviewer", "admin", "super_admin"];

export function hasPermission(role: UserRole | undefined, permission: string): boolean {
  if (!role) return false;
  const grants = ROLE_PERMISSIONS[role];
  if (grants === "*") return true;
  return grants.has(permission);
}

export function canApproveModels(role: UserRole | undefined): boolean {
  return !!role && APPROVAL_ROLES.includes(role);
}
