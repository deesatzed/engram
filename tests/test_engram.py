import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.append(str(Path(__file__).parent.parent))
from engram_core import TaxonomyValidator, DriveVaultManager, TriageDisposition
from engram_screenshots import OpenRouterLunaClient, triage_screenshot_image


class TestTaxonomyValidator(unittest.TestCase):
    def test_validate_notebook_exact_match(self):
        self.assertEqual(TaxonomyValidator.validate_notebook("EPIC"), "EPIC")
        self.assertEqual(TaxonomyValidator.validate_notebook("PDF Notebook"), "PDF Notebook")

    def test_validate_notebook_case_insensitive(self):
        self.assertEqual(TaxonomyValidator.validate_notebook("epic"), "EPIC")
        self.assertEqual(TaxonomyValidator.validate_notebook("work"), "Work")

    def test_validate_notebook_fallback(self):
        self.assertEqual(TaxonomyValidator.validate_notebook("Random Notebook"), "Work")

    def test_filter_tags(self):
        candidate_tags = ["#epic", "SQL", "MadeUpTag", "#Academic"]
        filtered = TaxonomyValidator.filter_tags(candidate_tags)
        self.assertIn("Epic", filtered)
        self.assertIn("SQL", filtered)
        self.assertIn("Academic", filtered)
        self.assertNotIn("MadeUpTag", filtered)


class TestDriveVaultManager(unittest.TestCase):
    def setUp(self):
        self.drive_base = Path("/tmp/engram_drive_mock")
        self.import_base = Path("/tmp/engram_import_mock")
        self.mgr = DriveVaultManager(self.drive_base, self.import_base, heavy_threshold_mb=10.0)

    @patch("pathlib.Path.stat")
    def test_is_heavy_true(self, mock_stat):
        mock_stat.return_value = MagicMock(st_size=15 * 1024 * 1024)
        self.assertTrue(self.mgr.is_heavy(Path("dummy.pdf")))

    @patch("pathlib.Path.stat")
    def test_is_heavy_false(self, mock_stat):
        mock_stat.return_value = MagicMock(st_size=5 * 1024 * 1024)
        self.assertFalse(self.mgr.is_heavy(Path("dummy.pdf")))


class TestLunaDecisionsTriage(unittest.TestCase):
    def test_parse_direct_predicate_json(self):
        raw = {"type": "predicate", "name": "evaluation", "probability": 0.91}
        parsed = OpenRouterLunaClient.parse_decision_response(raw)
        self.assertAlmostEqual(parsed["probability"], 0.91)

    def test_parse_openrouter_wrapped_choice_json(self):
        raw = {
            "choices": [
                {"message": {"content": '{"type": "choice", "choice": "EPIC", "probability": 0.94}'}}
            ]
        }
        parsed = OpenRouterLunaClient.parse_decision_response(raw)
        self.assertEqual(parsed["choice"], "EPIC")

    @patch("pathlib.Path.stat")
    def test_triage_trashes_high_probability_junk(self, mock_stat):
        mock_stat.return_value = MagicMock(st_size=100 * 1024, st_mtime=1700000000)
        client = MagicMock(spec=OpenRouterLunaClient)
        client.evaluate_predicate.return_value = 0.88

        decision = triage_screenshot_image(Path("2fa_code.png"), client)
        self.assertEqual(decision.disposition, TriageDisposition.TRASH_EPHEMERAL)

    @patch("pathlib.Path.stat")
    def test_triage_routes_valid_screenshot_to_chosen_notebook(self, mock_stat):
        mock_stat.return_value = MagicMock(st_size=250 * 1024, st_mtime=1700000000)
        client = MagicMock(spec=OpenRouterLunaClient)
        client.model = "openai/gpt-6-luna-decisions"
        client.evaluate_predicate.return_value = 0.05
        client.evaluate_choice.return_value = "EPIC"

        decision = triage_screenshot_image(Path("bpa_schema.png"), client)
        self.assertEqual(decision.disposition, TriageDisposition.KEEP_REFERENCE)
        self.assertEqual(decision.notebook, "EPIC")
        self.assertTrue(decision.clean_filename.endswith(".png"))


if __name__ == "__main__":
    unittest.main()
