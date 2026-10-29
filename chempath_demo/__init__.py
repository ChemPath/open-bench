"""ChemPath demo: public demonstration of ChemPath molecular characterization.

Structure characterization of botanical formulations with RDKit, plus SHAP
explainability on a synthetic model. Not the production ChemPath engine.
"""

__version__ = "0.2.0"

from chempath_demo.characterize import analyze_batch, analyze_formulation  # noqa: E402
from chempath_demo.schema import RequestError  # noqa: E402

__all__ = ["__version__", "analyze_formulation", "analyze_batch", "RequestError"]
