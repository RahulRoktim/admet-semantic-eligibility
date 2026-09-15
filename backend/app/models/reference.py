from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
import uuid
import datetime
from app.db.session import Base

class ReferenceDataset(Base):
    __tablename__ = 'reference_datasets'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_name = Column(String, nullable=False, index=True) # e.g. 'DILIrank'
    dataset_version = Column(String, nullable=False, index=True) # e.g. '2.0'
    source_organization = Column(String, nullable=False) # e.g. 'FDA / NCTR'
    source_url = Column(String, nullable=True)
    download_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    local_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    sha256_hash = Column(String, nullable=False, unique=True, index=True)
    record_count = Column(Integer, nullable=False)
    schema_signature = Column(String, nullable=True)
    status = Column(String, default='AVAILABLE', index=True) # AVAILABLE, INVALID_SCHEMA, CHECKSUM_CHANGED, FAILED
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    records = relationship('ReferenceDatasetRecord', back_populates='dataset', cascade='all, delete-orphan')
    curated_evidence = relationship('CuratedEvidenceRecord', back_populates='source_dataset')

class ReferenceDatasetRecord(Base):
    __tablename__ = 'reference_dataset_records'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, ForeignKey('reference_datasets.id'), nullable=False, index=True)
    external_record_id = Column(String, nullable=False, index=True) # e.g. LT00004
    raw_compound_name = Column(String, nullable=False, index=True)
    raw_data_json = Column(Text, nullable=False) # Full original serialized JSON of all columns
    source_row_hash = Column(String, nullable=False, index=True) # SHA-256 of raw data fields
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    dataset = relationship('ReferenceDataset', back_populates='records')

class IdentityMatch(Base):
    __tablename__ = 'identity_matches'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_dataset = Column(String, nullable=False, index=True) # e.g. 'DILIrank'
    dataset_record_id = Column(String, nullable=False, index=True) # e.g. LT00004
    source_compound_name = Column(String, nullable=False, index=True) # e.g. 'Verapamil hydrochloride'
    molecule_id = Column(String, ForeignKey('molecules.id'), nullable=True, index=True)
    
    match_method = Column(String, nullable=False) # EXACT_NAME_MATCH, EXACT_SYNONYM_MATCH, EXACT_STRUCTURE_MATCH, SALT_FORM_MATCH, PARENT_ACTIVE_MOIETY_MATCH, MANUAL_CURATED_MATCH, AMBIGUOUS_MATCH, NO_MATCH
    match_status = Column(String, default='MATCHED', index=True) # MATCHED, AMBIGUOUS, UNMATCHED, MANUAL_REVIEW
    confidence_class = Column(String, default='EXACT', index=True) # EXACT, HIGH_CONFIDENCE, RELATIONSHIP_SUPPORTED, AMBIGUOUS, UNMATCHED
    matched_structure_form = Column(String, default='PARENT') # PARENT, SALT, METABOLITE, MIXTURE, UNKNOWN
    match_details = Column(Text, nullable=True) # JSON payload with details
    curator_note = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    molecule = relationship('Molecule')

class CuratedEvidenceRecord(Base):
    __tablename__ = 'curated_evidence_records'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(String, ForeignKey('molecules.id'), nullable=False, index=True)
    endpoint_id = Column(String, nullable=False, index=True) # e.g. 'toxicity.hepatotoxicity.human.dili.curated_risk'
    evidence_class = Column(String, default='CURATED_REFERENCE', index=True) # CURATED_REFERENCE, REGULATORY_LABEL_DERIVED, USER_CURATED
    curation_authority = Column(String, default='FDA', index=True) # e.g. 'FDA', 'EMA', 'PMDA'
    
    dataset_name = Column(String, nullable=False) # e.g. 'DILIrank'
    dataset_version = Column(String, nullable=False) # e.g. '2.0'
    dataset_record_id = Column(String, nullable=False) # e.g. 'LT00004'
    
    raw_compound_name = Column(String, nullable=False) # e.g. 'Acetaminophen' or 'Verapamil hydrochloride'
    raw_classification = Column(String, nullable=False) # e.g. 'vMost-DILI-concern'
    normalized_classification = Column(String, nullable=False, index=True) # MOST_CONCERN, LESS_CONCERN, NO_CONCERN, AMBIGUOUS
    
    severity_class = Column(String, nullable=True) # e.g. '5', '8', '0', '3'
    label_section = Column(String, nullable=True) # e.g. 'Warnings and precautions', 'Box warning'
    comment = Column(String, nullable=True) # e.g. 'Unchanged', 'Revised', 'New'
    
    biological_scope = Column(String, default='HUMAN', index=True) # HUMAN
    population_scope = Column(String, default='GENERAL_CLINICAL_POPULATION')
    
    identity_match_id = Column(String, ForeignKey('identity_matches.id'), nullable=True)
    identity_match_method = Column(String, nullable=True)
    identity_match_status = Column(String, nullable=True)
    identity_match_confidence_class = Column(String, nullable=True)
    matched_structure_form = Column(String, nullable=True)
    
    source_dataset_id = Column(String, ForeignKey('reference_datasets.id'), nullable=False)
    source_row_hash = Column(String, nullable=False)
    
    mapping_run_id = Column(String, nullable=True)
    ontology_version = Column(String, default='0.3.0')
    
    is_current = Column(Boolean, default=True, index=True)
    interpretation_status = Column(String, default='CURRENT', index=True) # CURRENT, SUPERSEDED, REJECTED
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    molecule = relationship('Molecule')
    source_dataset = relationship('ReferenceDataset', back_populates='curated_evidence')
    identity_match = relationship('IdentityMatch')
