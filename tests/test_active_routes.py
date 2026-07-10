import unittest

from backend.app.main import app
from dashboard import api_client


class ActiveRouteTests(unittest.TestCase):
    def test_only_website_analysis_workflow_is_routed(self) -> None:
        paths = {route.path for route in app.routes}

        self.assertIn("/analysis/website", paths)
        self.assertNotIn("/analysis/single", paths)
        self.assertNotIn("/analysis/batch", paths)

    def test_dashboard_exposes_only_website_analysis_client(self) -> None:
        self.assertTrue(hasattr(api_client, "analyze_website"))
        self.assertFalse(hasattr(api_client, "analyze_review"))

    def test_dashboard_ui_imports_without_deleted_model_services(self) -> None:
        from dashboard import ui

        self.assertTrue(hasattr(ui, "render_website_report"))


if __name__ == "__main__":
    unittest.main()
