from sqlalchemy import Column, Integer, String, Float, DateTime, func, Text, ForeignKey, JSON, Boolean
from app.db.session import Base
import uuid

class SourceRecord(Base):
    __tablename__ = "source_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ingestion_run_id = Column(String, ForeignKey("ingestion_runs.id"), nullable=False, index=True)
    source_database = Column(String, nullable=False, index=True)
    external_record_id = Column(String, nullable=True, index=True)
    molecule_id = Column(String, ForeignKey("molecules.id"), nullable=False, index=True)
    retrieved_at = Column(DateTime, server_default=func.now())
    # raw_payload_hash is retained as a compatibility alias for the canonical
    # payload hash.  New records expose both representations explicitly.
    raw_payload_hash = Column(String, nullable=True)
    payload_canonical_sha256 = Column(String, nullable=True)
    raw_bytes_sha256 = Column(String, nullable=True)
    raw_payload_path = Column(String, nullable=True)
    query_identifier = Column(String, nullable=True)
    external_source_url = Column(String, nullable=True)

class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(String, ForeignKey("molecules.id"), nullable=False, index=True)
    source_record_id = Column(String, ForeignKey("source_records.id"), nullable=False, index=True)
    mapping_run_id = Column(String, ForeignKey("mapping_runs.id"), nullable=True, index=True)
    
    endpoint_id = Column(String, nullable=False, index=True) # Canonical hierarchical endpoint
    
    raw_endpoint_name = Column(String, nullable=True)
    result_kind = Column(String, nullable=True) # numeric, categorical
    
    # Raw value
    raw_value = Column(String, nullable=True)
    raw_unit = Column(String, nullable=True)
    raw_qualifier = Column(String, nullable=True) # =, >, <, ~
    
    # Normalized
    normalized_value = Column(Float, nullable=True)
    normalized_unit = Column(String, nullable=True)
    normalization_status = Column(String(40), nullable=True) # CONVERTED, FAILED, MISSING_UNIT, CATEGORICAL, etc.
    categorical_value = Column(String, nullable=True)
    
    # Context & Ontology
    species = Column(String, nullable=True)
    biological_system = Column(String, nullable=True)
    assay_type = Column(String, nullable=True)
    matrix = Column(String, nullable=True) # e.g. plasma, serum, whole blood, buffer
    
    # Semantic & Provenance Intelligence
    evidence_type = Column(String, default="EXPERIMENTAL", index=True) # EXPERIMENTAL, DERIVED, PREDICTED, CURATED, REGULATORY
    biological_scope = Column(String, nullable=True) # HUMAN, PRECLINICAL_IN_VIVO, IN_VITRO, CELL_FREE, CELLULAR, CURATED_REGULATORY, UNKNOWN
    result_semantics = Column(String, nullable=True) # CONTINUOUS_CONCENTRATION, CONTINUOUS_FRACTION, CONTINUOUS_PERCENT, etc.
    admet_relevance = Column(String, default="ADMET_RELEVANT", index=True) # ADMET_RELEVANT, ADMET_RELATED, NON_ADMET_BIOACTIVITY, UNRESOLVED
    
    # Current vs Historical Interpretation Tracking
    is_current = Column(Boolean, default=True, nullable=False, index=True)
    interpretation_status = Column(String(50), default="CURRENT", nullable=False, index=True) # CURRENT, SUPERSEDED, HISTORICAL
    underlying_observation_id = Column(String(255), nullable=True, index=True) # e.g. "ChEMBL:12345"
    
    # Rule Mapping Metadata
    mapping_rule_id = Column(String, nullable=True)
    mapping_status = Column(String, nullable=True) # EXACT, HIGH_CONFIDENCE, CONTEXT_SUPPORTED, AMBIGUOUS, UNMAPPED
    mapping_reason = Column(Text, nullable=True)
    
    # Derivation Metadata
    is_derived = Column(Boolean, default=False, index=True)
    derivation_rule = Column(Text, nullable=True)
    derived_from_evidence_id = Column(String, ForeignKey("evidence_records.id"), nullable=True, index=True)
    derivation_engine_version = Column(String, nullable=True)
    
    # Uncertainty
    uncertainty_value = Column(Float, nullable=True)
    uncertainty_type = Column(String, nullable=True)
    
    publication_id = Column(String, nullable=True)
    comments = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
