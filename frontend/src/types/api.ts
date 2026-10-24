/**
 * Mirrors backend/schemas/*.py and backend/core/constants.py.
 * Keep in sync manually for now; a future pass could codegen this from the
 * backend's OpenAPI schema (`/openapi.json`) instead.
 */

export type NLPTask =
  | "sentiment_analysis"
  | "emotion_detection"
  | "topic_classification"
  | "toxicity_detection"
  | "language_detection"
  | "zero_shot_classification"
  | "semantic_similarity"
  | "text_embeddings";

export type UserRole =
  | "super_admin"
  | "admin"
  | "ml_engineer"
  | "nlp_engineer"
  | "data_scientist"
  | "reviewer"
  | "business_analyst"
  | "auditor"
  | "read_only_user"
  | "analyst"
  | "viewer";

export interface TaskInfo {
  task: NLPTask;
  default_model: string;
  description: string;
  explainable: boolean;
}

export interface InferenceRequest {
  task: NLPTask;
  text: string;
  model_name?: string | null;
  candidate_labels?: string[] | null;
  multi_label?: boolean;
  text_pair?: string | null;
}

export interface BatchInferenceRequest {
  task: NLPTask;
  texts: string[];
  candidate_labels?: string[] | null;
  multi_label?: boolean;
}

export interface BatchInferenceResponse {
  task: NLPTask;
  model_name: string;
  items: { text: string; results: InferenceResult[] }[];
  latency_ms: number;
  throughput_texts_per_second: number;
}

export interface ExplainRequest {
  task: NLPTask;
  text: string;
  target_label?: string | null;
  n_steps?: number;
}

export interface TokenAttribution {
  token: string;
  importance: number;
}

export interface ExplainResponse {
  task: NLPTask;
  model_name: string;
  method: string;
  label: string;
  target_score: number;
  baseline_score: number;
  convergence_delta: number;
  attributions: TokenAttribution[];
  latency_ms: number;
}

export interface InferenceResult {
  label: string;
  score: number;
  raw_scores?: Record<string, number> | null;
}

export interface InferenceResponse {
  task: NLPTask;
  model_name: string;
  results: InferenceResult[];
  latency_ms: number;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string;
  };
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface LoginRequest {
  username: string;
  password: string;
  remember_me: boolean;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface UserPublic {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserPublic;
}

export interface SessionInfo {
  id: string;
  issued_at: string;
  expires_at: string;
}

// --- Datasets ---

export type DatasetStatus = "draft" | "validated" | "archived";

export interface Dataset {
  id: string;
  name: string;
  task: string;
  description: string | null;
  label_set: string[];
  tags: string[];
  version: number;
  parent_version_id: string | null;
  status: DatasetStatus;
  row_count: number;
  is_archived: boolean;
  archived_at: string | null;
  created_by: string | null;
  modified_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetRecord {
  id: string;
  dataset_id: string;
  text: string;
  label: string | null;
  extra_metadata: Record<string, unknown>;
  created_at: string;
}

export interface ValidationIssue {
  kind: string;
  message: string;
  record_indices: number[];
}

export interface ValidationReport {
  total_records: number;
  is_valid: boolean;
  issues: ValidationIssue[];
  label_distribution: Record<string, number>;
  duplicate_count: number;
  empty_count: number;
  short_text_count: number;
  long_text_count: number;
  missing_label_count: number;
  invalid_label_count: number;
}

export interface UploadResponse {
  dataset: Dataset;
  validation_report: ValidationReport;
}

export interface DatasetProfile {
  total_records: number;
  vocabulary_size: number;
  sequence_length: {
    min_words: number;
    max_words: number;
    mean_words: number;
    median_words: number;
  };
  label_distribution: Record<string, number>;
  top_words: [string, number][];
}

// --- Model Registry ---

export type ModelLifecycleStage = "development" | "staging" | "production" | "archived";
export type ApprovalStatus = "pending" | "approved" | "rejected";
export type DeploymentStatus = "not_deployed" | "deployed" | "rolled_back";

export interface ModelRegistryEntry {
  id: string;
  name: string;
  task: NLPTask;
  architecture: string;
  version: string;
  model_name_or_path: string;
  stage: ModelLifecycleStage;
  approval_status: ApprovalStatus;
  deployment_status: DeploymentStatus;
  is_champion: boolean;
  evaluation_run_id: string | null;
  accuracy: number | null;
  macro_f1: number | null;
  registered_by: string | null;
  approved_by: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// --- Evaluation ---

export interface PerClassMetric {
  label: string;
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface CalibrationBin {
  bucket_low: number;
  bucket_high: number;
  avg_confidence: number;
  accuracy: number;
  count: number;
}

export interface MisclassifiedSample {
  text: string;
  true_label: string;
  predicted_label: string;
  confidence: number;
}

export interface LengthSlice {
  name: string;
  count: number;
  accuracy: number;
  error_count: number;
}

export interface ErrorSummary {
  total_errors: number;
  confidence_error_count: number;
  hard_example_count: number;
  false_positives_by_class: Record<string, number>;
  false_negatives_by_class: Record<string, number>;
  errors_by_class: Record<string, number>;
  length_slices: LengthSlice[];
}

export type EvaluationModelKind = "served" | "lexicon_baseline";
export type BuiltinEvalSet = "challenge_set" | "sst2_validation";

export interface EvaluationRunRequest {
  task: NLPTask;
  model: EvaluationModelKind;
  eval_set?: BuiltinEvalSet;
  dataset_id?: string | null;
}

export interface EvaluationRunSummary {
  run_id: string;
  task: NLPTask;
  model_name: string;
  model_kind: EvaluationModelKind;
  eval_set: string;
  created_at: string;
  accuracy: number;
  macro_f1: number | null;
  num_samples: number;
}

export interface EvaluationRunResult {
  run_id: string;
  task: NLPTask;
  model_name: string;
  model_kind: EvaluationModelKind;
  eval_set: string;
  duration_seconds: number | null;
  created_at: string;
  num_samples: number;
  accuracy: number;
  macro_f1: number;
  weighted_f1: number;
  roc_auc: number | null;
  ece: number | null;
  labels: string[];
  confusion_matrix: number[][];
  per_class: PerClassMetric[];
  calibration_bins: CalibrationBin[];
  error_summary: ErrorSummary;
  misclassified_samples: MisclassifiedSample[];
}

// --- Health / Status ---

export interface SubsystemCheck {
  status: string;
  [key: string]: unknown;
}

export interface OverallStatus {
  status: string;
  checks: Record<string, SubsystemCheck>;
}
