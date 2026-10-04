"""Interactive Dash dashboard."""

from incident_analyzer.dashboard.app import create_app, create_server, load_dashboard_data

__all__ = ["create_app", "create_server", "load_dashboard_data"]
