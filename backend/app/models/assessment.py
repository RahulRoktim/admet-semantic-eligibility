import datetime
import uuid
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base

class EvidenceAssessment(Base):
    __tablename__ = 'evidence_assessments'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    molecule_id = Column(String, ForeignKey('molecules.id'), nullable=False, index=True)
    
    # Target evidence identification
    target_type = Column(String(50), nullable=False, index=True) # EVIDENCE_RECORD, CURATED_EVIDENCE_RECORD, PREDICTION_RECORD
    target_id = Column(String, nullable=False, index=True) # UUID of the target record
    
    assessment_engine_version = Column(String(50), default='1.0.0', nullable=False)
    evaluated_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # 1. Identity Confidence
    identity_confidence = Column(String(50), nullable=False, index=True) # EXACT, STEREO_MATCH, SALT_FORM_MATCH, PARENT_FORM_MATCH, SYNONYM_MATCH, AMBIGUOUS, UNRESOLVED
    identity_confidence_reason = Column(Text, nullable=False)
    identity_rule_id = Column(String(100), default='IDENTITY_ASSESSMENT_V1')
    
    # 2. Endpoint Relevance
    endpoint_relevance = Column(String(50), nullable=False, index=True) # DIRECT, CLOSELY_RELATED, INDIRECT, CONTEXT_ONLY, NOT_COMPARABLE
    endpoint_relevance_reason = Column(Text, nullable=False)
    endpoint_rule_id = Column(String(100), default='ENDPOINT_RELEVANCE_V1')
    
    # 3. Biological Applicability
    biological_applicability = Column(String(50), nullable=False, index=True) # Includes clinical, in-vitro, preclinical, biochemical, computational, and unspecified contexts.
    biological_applicability_reason = Column(Text, nullable=False)
    biological_rule_id = Column(String(100), default='BIOLOGICAL_APPLICABILITY_V1')
    
    # 4. Measurement Directness
    measurement_directness = Column(String(50), nullable=False, index=True) # Empirical, formal derivation, curated synthesis, prediction, or reference percentile.
    measurement_directness_reason = Column(Text, nullable=False)
    directness_rule_id = Column(String(100), default='MEASUREMENT_DIRECTNESS_V1')
    
    # 5. Source / Provenance Quality
    source_provenance_quality = Column(String(50), nullable=False, index=True) # Curated database/reference, computational model, or derived reference context.
    source_provenance_reason = Column(Text, nullable=False)
    provenance_rule_id = Column(String(100), default='PROVENANCE_QUALITY_V1')
    
    # 6. Model Applicability (Only for PREDICTED evidence)
    model_applicability = Column(String(50), nullable=True, index=True) # Domain status or explicit non-applicability for non-predicted/reference context.
    model_applicability_reason = Column(Text, nullable=True)
    model_rule_id = Column(String(100), nullable=True)
    
    # 7. Temporal & Version Context
    temporal_version_context = Column(String(50), default='CURRENT_SNAPSHOT_VALIDATED', nullable=False)
    temporal_version_reason = Column(Text, nullable=False)
    temporal_rule_id = Column(String(100), default='TEMPORAL_CONTEXT_V1')
    
    # Metadata & Completeness audit
    provenance_completeness_flags = Column(JSON, nullable=True)
    is_current = Column(Boolean, default=True, nullable=False, index=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'molecule_id': self.molecule_id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'assessment_engine_version': self.assessment_engine_version,
            'evaluated_at': self.evaluated_at.isoformat() if self.evaluated_at else None,
            'identity_confidence': self.identity_confidence,
            'identity_confidence_reason': self.identity_confidence_reason,
            'identity_rule_id': self.identity_rule_id,
            'endpoint_relevance': self.endpoint_relevance,
            'endpoint_relevance_reason': self.endpoint_relevance_reason,
            'endpoint_rule_id': self.endpoint_rule_id,
            'biological_applicability': self.biological_applicability,
            'biological_applicability_reason': self.biological_applicability_reason,
            'biological_rule_id': self.biological_rule_id,
            'measurement_directness': self.measurement_directness,
            'measurement_directness_reason': self.measurement_directness_reason,
            'directness_rule_id': self.directness_rule_id,
            'source_provenance_quality': self.source_provenance_quality,
            'source_provenance_reason': self.source_provenance_reason,
            'provenance_rule_id': self.provenance_rule_id,
            'model_applicability': self.model_applicability,
            'model_applicability_reason': self.model_applicability_reason,
            'model_rule_id': self.model_rule_id,
            'temporal_version_context': self.temporal_version_context,
            'temporal_version_reason': self.temporal_version_reason,
            'temporal_rule_id': self.temporal_rule_id,
            'dimensions': {
                'identity_confidence': {
                    'value': self.identity_confidence,
                    'reason': self.identity_confidence_reason,
                    'rule_id': self.identity_rule_id
                },
                'endpoint_relevance': {
                    'value': self.endpoint_relevance,
                    'reason': self.endpoint_relevance_reason,
                    'rule_id': self.endpoint_rule_id
                },
                'biological_applicability': {
                    'value': self.biological_applicability,
                    'reason': self.biological_applicability_reason,
                    'rule_id': self.biological_rule_id
                },
                'measurement_directness': {
                    'value': self.measurement_directness,
                    'reason': self.measurement_directness_reason,
                    'rule_id': self.directness_rule_id
                },
                'source_provenance_quality': {
                    'value': self.source_provenance_quality,
                    'reason': self.source_provenance_reason,
                    'rule_id': self.provenance_rule_id
                },
                'model_applicability': {
                    'value': self.model_applicability,
                    'reason': self.model_applicability_reason,
                    'rule_id': self.model_rule_id
                },
                'temporal_version_context': {
                    'value': self.temporal_version_context,
                    'reason': self.temporal_version_reason,
                    'rule_id': self.temporal_rule_id
                }
            },
            'provenance_completeness_flags': self.provenance_completeness_flags or {},
            'is_current': self.is_current
        }
