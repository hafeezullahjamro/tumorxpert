"""Database snapshots driven exclusively by completed pipeline operations."""
from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.orm import Session

from ..db.models import Study

STAGES = (
    ("validate", "Validate uploaded modalities"),
    ("preprocess", "Preprocess MRI volumes"),
    ("synthesis", "Synthesize missing modality"),
    ("nnunet", "nnU-Net segmentation"),
    ("swinunetr", "Swin UNETR segmentation"),
    ("ensemble", "Save model outputs and calculate ensemble metrics"),
    ("previews", "Render preview images"),
    ("exports", "Generate report and exports"),
    ("persist", "Save results and artifact records"),
)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def step_record(key, label):
    return dict(id=key, label=label, status="PENDING", completed=0, total=1,
                unit="operations", percent=0.0, detail=None, children=[])


class ProgressReporter:
    def __init__(self, bind, study_id):
        self.bind, self.study_id = bind, study_id
        self.snapshot = dict(run_id=str(uuid4()), status="PROCESSING", percent=0.0,
                             started_at=timestamp(), updated_at=timestamp(), finished_at=None,
                             error=None, stages=[step_record(*stage) for stage in STAGES])
        self.last_write = 0.0

    def _find(self, key):
        for stage in self.snapshot["stages"]:
            if stage["id"] == key:
                return stage
            for child in stage["children"]:
                if child["id"] == key:
                    return child
        raise KeyError(key)

    def children(self, stage, entries):
        self._find(stage)["children"] = [step_record(*entry) for entry in entries]
        self.flush(force=True)

    def update(self, key, completed=0, total=1, *, unit="operations", detail=None,
               status="RUNNING", force=False):
        item = self._find(key)
        item.update(completed=completed, total=max(total, 1), unit=unit,
                    detail=detail, status=status)
        item["percent"] = 100.0 if status in {"DONE", "SKIPPED"} else min(99.9, 100 * completed / max(total, 1))
        self.flush(force=force or status != "RUNNING")

    def done(self, key, detail=None):
        item = self._find(key)
        self.update(key, item["total"], item["total"], unit=item["unit"],
                    detail=detail or item["detail"], status="DONE")

    def skip(self, key, reason):
        for child in self._find(key)["children"]:
            if child["status"] != "DONE":
                child.update(status="SKIPPED", percent=100.0, detail=reason)
        self.update(key, status="SKIPPED", detail=reason)

    def flush(self, *, force=False, db=None):
        for stage in self.snapshot["stages"]:
            children = stage["children"]
            if children:
                stage["percent"] = sum(item["percent"] for item in children) / len(children)
                if stage["status"] == "SKIPPED":
                    continue
                if all(item["status"] in {"DONE", "SKIPPED"} for item in children):
                    stage["status"] = "DONE"
                elif any(item["status"] == "FAILED" for item in children):
                    stage["status"] = "FAILED"
                elif any(item["status"] != "PENDING" for item in children):
                    stage["status"] = "RUNNING"
        stages = self.snapshot["stages"]
        self.snapshot["percent"] = round(sum(stage["percent"] for stage in stages) / len(stages), 1)
        if self.snapshot["status"] != "DONE":
            self.snapshot["percent"] = min(99.9, self.snapshot["percent"])
        if not force and monotonic() - self.last_write < 0.5:
            return
        self.snapshot["updated_at"] = timestamp()
        statement = update(Study).where(Study.id == self.study_id).values(progress=self.snapshot)
        if db is not None:
            db.execute(statement)
        else:
            with Session(self.bind) as session:
                session.execute(statement)
                session.commit()
        self.last_write = monotonic()

    def finish(self, db):
        self.snapshot.update(status="DONE", finished_at=timestamp())
        self.flush(force=True, db=db)

    def fail(self, error, db):
        for stage in self.snapshot["stages"]:
            for item in [stage, *stage["children"]]:
                if item["status"] == "RUNNING":
                    item["status"] = "FAILED"
        self.snapshot.update(status="FAILED", error=str(error), finished_at=timestamp())
        self.flush(force=True, db=db)
