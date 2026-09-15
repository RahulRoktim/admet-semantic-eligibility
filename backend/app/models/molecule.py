from sqlalchemy import Column, Integer, String, DateTime, func, Text, Float, JSON
from app.db.session import Base
import uuid

class Molecule(Base):
    __tablename__ = "molecules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    preferred_name = Column(String, nullable=True)
    original_input = Column(String, nullable=False)
    original_structure = Column(String, nullable=True)
    canonical_smiles = Column(String, nullable=False, unique=True, index=True)
    canonical_non_isomeric_smiles = Column(String, nullable=True)
    inchi = Column(Text, nullable=True)
    inchikey = Column(String, nullable=True, index=True)
    molecular_formula = Column(String, nullable=True)
    molecular_weight = Column(Float, nullable=True)
    formal_charge = Column(Integer, nullable=True)
    pubchem_cid = Column(String, nullable=True)
    # Form-aware PubChem identity fields.  pubchem_cid remains the selected
    # display identifier for backward compatibility; these fields make it
    # explicit whether a submitted form was actually verified and whether any
    # parent/standardized identifier was retrieved.
    pubchem_submitted_cid = Column(String, nullable=True)
    pubchem_standardized_cid = Column(String, nullable=True)
    pubchem_parent_cid = Column(String, nullable=True)
    pubchem_identity_relationship = Column(String, nullable=True)
    pubchem_identity_status = Column(String, nullable=True)
    pubchem_identity_details = Column(JSON, nullable=True)
    chembl_id = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
