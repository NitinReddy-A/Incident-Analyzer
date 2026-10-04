"""Incident Analyzer: incident intelligence for PagerDuty-managed service fleets.

The package is organised as a small pipeline:

    ingest  ->  curation  ->  classify  ->  transitions  ->  dashboard

Each stage is usable on its own (as a library or via the ``incident-analyzer``
CLI) and exchanges plain pandas DataFrames that follow the schema defined in
:mod:`incident_analyzer.schema`.
"""

from incident_analyzer.transitions import Forecast, TransitionModel

__all__ = ["Forecast", "TransitionModel", "__version__"]

__version__ = "1.0.0"
