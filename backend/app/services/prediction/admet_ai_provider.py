import pandas as pd
import importlib.metadata
from numbers import Real
from typing import Dict, Any, List
from app.services.prediction.base import PredictionProvider
from app.models.molecule import Molecule

class AdmetAiProvider(PredictionProvider):
    name = "admet_ai"
    version = "v2"

    def __init__(self):
        self.initialization_error = None
        self.package_version = None
        try:
            from admet_ai import ADMETModel
            self.model = ADMETModel()
            self.package_version = importlib.metadata.version("admet-ai")
        except Exception as exc:
            self.model = None
            self.initialization_error = str(exc)

    def is_available(self) -> bool:
        return self.model is not None

    def _endpoint_metadata(self) -> Dict[str, Dict[str, Any]]:
        # ADMET-AI adds DrugBank percentile context beside model outputs. Use
        # the package's own metadata so classification probabilities are not
        # mislabeled as regression values and percentiles are not mislabeled as
        # endpoint probabilities.
        try:
            from admet_ai.admet_info import get_admet_info

            metadata = {
                str(item["id"]).casefold(): {
                    "task_type": str(item.get("task_type") or "unknown").lower(),
                    "units": None if pd.isna(item.get("units")) else str(item.get("units")),
                }
                for item in get_admet_info().to_dict(orient="records")
            }
        except Exception:
            metadata = {}
        return metadata

    def _format_row(
        self,
        row: Dict[str, Any],
        metadata: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        records = []
        for key, val in row.items():
            endpoint_id = str(key).lower()
            is_reference_percentile = (
                "_drugbank_approved" in endpoint_id and endpoint_id.endswith("_percentile")
            )
            base_endpoint_id = endpoint_id.split("_drugbank_approved", 1)[0]
            endpoint_metadata = metadata.get(base_endpoint_id, {})
            if is_reference_percentile:
                prediction_type = "reference_percentile"
                prediction_unit = "percentile"
            else:
                prediction_type = endpoint_metadata.get("task_type", "unknown")
                prediction_unit = endpoint_metadata.get("units")

            numeric_value = float(val) if isinstance(val, Real) and not pd.isna(val) else None
            records.append({
                "endpoint_id": endpoint_id,
                "source_output_name": str(key),
                "raw_prediction": str(val),
                "normalized_prediction": numeric_value,
                "prediction_type": prediction_type,
                "prediction_unit": prediction_unit,
                "uncertainty_value": None  # ADMET-AI doesn't natively return uncertainty without conformal prediction flag usually
            })
        return records

    def predict_smiles_batch(self, smiles: List[str]) -> List[List[Dict[str, Any]]]:
        """Predict an ordered batch through the production output formatter.

        The validation harness uses this method so it receives exactly the
        same endpoint names, types, units, and percentile safeguards as the
        interactive application, without reloading the model per molecule.
        """
        if not self.is_available():
            detail = f" ({self.initialization_error})" if self.initialization_error else ""
            raise RuntimeError(f"ADMET-AI package or local model is not available{detail}.")
        if not smiles:
            return []

        preds = self.model.predict(smiles=smiles)
        if not isinstance(preds, pd.DataFrame):
            raise TypeError(f"Unexpected return type from admet-ai: {type(preds)}")
        if len(preds) != len(smiles):
            raise ValueError(
                "ADMET-AI returned a different number of rows than requested; "
                "invalid structures must be rejected before prediction."
            )

        metadata = self._endpoint_metadata()
        return [self._format_row(row.to_dict(), metadata) for _, row in preds.iterrows()]

    def predict(self, mol: Molecule) -> List[Dict[str, Any]]:
        return self.predict_smiles_batch([mol.canonical_smiles])[0]
