import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.auth.rbac import require_permission
from backend.database.session import get_db_session
from backend.reporting.report_generator import MarkdownEvaluationReport
from backend.schemas.auth import CurrentUser
from backend.schemas.evaluation import (
    EvaluationRunRequest,
    EvaluationRunResult,
    EvaluationRunSummary,
)
from backend.services.evaluation_service import evaluation_service
from backend.utils.csv_safety import sanitize_csv_row

router = APIRouter()
_report_generator = MarkdownEvaluationReport()


@router.post("/evaluation/run", response_model=EvaluationRunResult)
def run_evaluation(
    request: EvaluationRunRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> EvaluationRunResult:
    require_permission(current_user.role, "experiment:write")
    if request.dataset_id:
        require_permission(current_user.role, "dataset:read")
    result = evaluation_service.run_evaluation(
        request.task,
        model=request.model,
        eval_set=request.eval_set,
        dataset_id=request.dataset_id,
        db=db,
    )
    return EvaluationRunResult.model_validate(result)


@router.get("/evaluation/runs", response_model=list[EvaluationRunSummary])
def list_evaluation_runs(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[EvaluationRunSummary]:
    require_permission(current_user.role, "experiment:read")
    return [EvaluationRunSummary.model_validate(s) for s in evaluation_service.list_runs()]


@router.get("/evaluation/runs/{run_id}", response_model=EvaluationRunResult)
def get_evaluation_run(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> EvaluationRunResult:
    require_permission(current_user.role, "experiment:read")
    result = evaluation_service.get_run(run_id)
    return EvaluationRunResult.model_validate(result)


@router.get("/evaluation/runs/{run_id}/report", response_class=PlainTextResponse)
def get_evaluation_report(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> str:
    require_permission(current_user.role, "experiment:read")
    result = evaluation_service.get_run(run_id)
    return _report_generator.generate(result)


@router.get("/evaluation/runs/{run_id}/misclassified.csv")
def download_misclassified_csv(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    require_permission(current_user.role, "experiment:read")
    result = evaluation_service.get_run(run_id)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["text", "true_label", "predicted_label", "confidence"])
    writer.writeheader()
    for sample in result["misclassified_samples_full"]:
        writer.writerow(sanitize_csv_row(sample))
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="misclassified_{run_id}.csv"'},
    )
