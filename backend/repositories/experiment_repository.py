from sqlalchemy.orm import Session

from backend.models.experiment import Experiment
from backend.repositories.base_repository import BaseRepository


class ExperimentRepository(BaseRepository[Experiment]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Experiment)

    def find_by_task(self, task: str) -> list[Experiment]:
        return list(self._db.query(Experiment).filter(Experiment.task == task).all())
