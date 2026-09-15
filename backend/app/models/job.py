import datetime
import uuid
from typing import Any, Dict

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, func

from app.db.session import Base


class OperationJob(Base):
    """Persisted lifecycle record for an observable local operation.

    Jobs wrap existing synchronous scientific operations. The underlying
    evidence/model run remains the source of scientific truth; this table only
    records operational state, progress, and the returned API result.
    """

    __tablename__ = "operation_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(String, ForeignKey("molecules.id"), nullable=False, index=True)
    operation = Column(String(50), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="QUEUED", server_default="QUEUED", index=True)
    progress = Column(Integer, nullable=False, default=0, server_default="0")
    message = Column(String, nullable=True)
    attempt = Column(Integer, nullable=False, default=1, server_default="1")
    retry_of = Column(String, ForeignKey("operation_jobs.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    cancel_requested = Column(Boolean, nullable=False, default=False, server_default="0")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "molecule_id": self.molecule_id,
            "operation": self.operation,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "attempt": self.attempt,
            "retry_of": self.retry_of,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "result": self.result,
            "cancel_requested": self.cancel_requested,
        }
