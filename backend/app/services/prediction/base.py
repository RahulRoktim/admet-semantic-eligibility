from typing import List, Dict, Any
from app.models.molecule import Molecule

class PredictionProvider:
    name: str = "base"
    version: str = "0.0.0"

    def is_available(self) -> bool:
        return False

    def predict(self, mol: Molecule) -> List[Dict[str, Any]]:
        raise NotImplementedError()
