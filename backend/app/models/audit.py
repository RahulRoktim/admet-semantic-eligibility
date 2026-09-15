from sqlalchemy import Column, String, Integer, DateTime, func, ForeignKey, JSON, Boolean
from app.db.session import Base
import uuid

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(String, ForeignKey("molecules.id"), nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    event_timestamp = Column(DateTime, server_default=func.now())
    details = Column(JSON, nullable=True)

class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(String, ForeignKey("molecules.id"), nullable=False, index=True)
    connector_name = Column(String, nullable=False)
    connector_version = Column(String, nullable=False)
    endpoint_registry_version = Column(String, nullable=False)
    started_at = Column(DateTime, server_default=func.now())
    status = Column(String, nullable=False) # SUCCESS, FAILED
    error_message = Column(String, nullable=True)
    
    # Pagination & retrieval metadata
    total_count_reported = Column(Integer, nullable=True)
    pages_fetched = Column(Integer, nullable=True)
    records_fetched = Column(Integer, nullable=True)
    records_deduplicated = Column(Integer, nullable=True)
    is_truncated = Column(Boolean, default=False, nullable=False)
    records_omitted = Column(Integer, default=0, nullable=False)
    truncation_reason = Column(String, nullable=True)

class MappingRun(Base):
    __tablename__ = "mapping_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(String, ForeignKey("molecules.id"), nullable=False, index=True)
    ingestion_run_id = Column(String, ForeignKey("ingestion_runs.id"), nullable=True, index=True)
    registry_version = Column(String, nullable=False) # e.g. "0.2.0"
    mapping_engine_version = Column(String, nullable=False) # e.g. "1.0.0"
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    status = Column(String, nullable=False) # STARTED, SUCCESS, FAILED
    total_classified_count = Column(Integer, default=0)
    admet_relevant_count = Column(Integer, default=0)
    admet_related_count = Column(Integer, default=0)
    non_admet_count = Column(Integer, default=0)
    mapped_count = Column(Integer, default=0)
    unmapped_count = Column(Integer, default=0)
    derived_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    error_message = Column(String, nullable=True)
