import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.append(str(Path(__file__).parent.parent))
from engram_core import TaxonomyValidator, DriveVaultManager

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

if __name__ == "__main__":
    unittest.main()
