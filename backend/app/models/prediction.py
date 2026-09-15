from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, JSON, String, Text, func
from app.db.session import Base
import uuid

class ModelRun(Base):
    __tablename__ = "model_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(String, ForeignKey("molecules.id"), nullable=False, index=True)
    provider_name = Column(String, nullable=False, index=True)
    model_version = Column(String, nullable=False)
    execution_timestamp = Column(DateTime, server_default=func.now())
    original_input = Column(String, nullable=False)
    standardized_input = Column(String, nullable=False)
    model_metadata = Column(JSON, nullable=True)
    status = Column(String, default="SUCCESS", server_default="SUCCESS", nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    is_current = Column(Boolean, default=True, server_default="1", nullable=False, index=True)

class PredictionRecord(Base):
    __tablename__ = "prediction_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_run_id = Column(String, ForeignKey("model_runs.id"), nullable=False, index=True)
    molecule_id = Column(String, ForeignKey("molecules.id"), nullable=False, index=True)
    endpoint_id = Column(String, nullable=False, index=True)
    
    raw_prediction = Column(String, nullable=False)
    normalized_prediction = Column(Float, nullable=True)
    prediction_type = Column(String, nullable=False) # regression, classification, reference_percentile, unknown
    
    uncertainty_value = Column(Float, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
