import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/seo/scripts"))
import migration_compare as migration


class MigrationComparisonTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.manifest = {
            "source_base": "https://source.example",
            "target_base": "https://preview.example",
            "source_frozen_at": "2026-09-28T09:00:00Z",
            "pages": [{
                "path": "/offres/",
                "source_capture": "source.json",
                "target_capture": "target.json",
            }],
        }
        self.source = {
            "url": "https://source.example/offres/",
            "status_code": 200,
            "headers": {"Content-Type": "text/html; charset=utf-8"},
            "content": '<title>Nos offres</title><h1>Nos offres</h1>'
                '<link rel="canonical" href="https://source.example/offres/">',
            "redirect_details": [],
            "error": None,
            "captured_at": "2026-09-28T09:00:00Z",
        }
        self.target = copy.deepcopy(self.source)
        self.target["url"] = "https://preview.example/offres/"

    def run_comparison(self):
        (self.root / "source.json").write_text(json.dumps(self.source))
        (self.root / "target.json").write_text(json.dumps(self.target))
        with patch.object(migration, "fetch_page", side_effect=AssertionError("Unexpected network")):
            return migration.compare_manifest(self.manifest, self.root)

    def test_matching_metadata_keeps_intentional_description_absence(self):
        report = self.run_comparison()
        self.assertEqual(report["status"], "MATCH")
        self.assertEqual(report["pages"][0]["differences"], [])
        self.assertIsNone(report["pages"][0]["source"]["fields"]["meta_description"])

    def test_canonical_and_trailing_slash_changes_are_not_normalized_away(self):
        self.target["content"] = self.target["content"].replace(
            "https://source.example/offres/", "https://preview.example/offres"
        )
        self.target["url"] = "https://preview.example/offres"
        self.target["requested_url"] = "https://preview.example/offres/"
        report = self.run_comparison()
        fields = {difference["field"] for difference in report["pages"][0]["differences"]}
        self.assertEqual(report["status"], "DIFFERENCES")
        self.assertEqual(fields, {"canonical", "final_path"})

    def test_preview_noindex_requires_an_exact_approved_difference(self):
        self.target["headers"]["X-Robots-Tag"] = "noindex, nofollow"
        self.manifest["pages"][0]["approved_differences"] = {
            "x_robots_tag": {
                "source": None,
                "target": "noindex, nofollow",
                "authority": "GREGG",
                "evidence": "Approbation explicite de la protection preview",
            }
        }
        report = self.run_comparison()
        self.assertEqual(report["status"], "MATCH_WITH_APPROVED_DIFFERENCES")
        self.assertEqual(report["pages"][0]["differences"][0]["state"], "APPROVED")
        self.target["headers"]["X-Robots-Tag"] = "noindex"
        self.assertEqual(self.run_comparison()["status"], "DIFFERENCES")

    def test_authentication_failure_cannot_be_a_clean_comparison(self):
        self.target["status_code"] = 401
        self.target["content"] = "Authentification requise"
        report = self.run_comparison()
        self.assertEqual(report["status"], "NOT_MEASURED")
        self.assertEqual(report["pages"][0]["target"]["status"], "NOT_AVAILABLE")

    def test_capture_for_a_different_route_is_rejected(self):
        self.target["url"] = "https://preview.example/contact/"
        report = self.run_comparison()
        self.assertEqual(report["status"], "NOT_MEASURED")

    def test_cross_domain_redirect_is_not_hidden_by_same_path(self):
        self.target["requested_url"] = "https://preview.example/offres/"
        self.target["url"] = "https://unexpected.example/offres/"
        report = self.run_comparison()
        self.assertEqual(report["status"], "DIFFERENCES")
        self.assertIn("final_origin", [d["field"] for d in report["pages"][0]["differences"]])

    def test_missing_redirect_capture_is_not_assumed_empty(self):
        del self.target["redirect_details"]
        self.assertEqual(self.run_comparison()["status"], "NOT_MEASURED")

    def test_missing_capture_is_an_error_not_zero_differences(self):
        self.manifest["pages"][0]["target_capture"] = "missing.json"
        report = self.run_comparison()
        self.assertEqual(report["status"], "NOT_MEASURED")
        self.assertEqual(report["pages"][0]["target"]["status"], "ERROR")

    def test_invalid_jsonld_is_reported(self):
        self.target["content"] += '<script type="application/ld+json">{broken}</script>'
        report = self.run_comparison()
        self.assertEqual(report["status"], "NOT_MEASURED")
        self.assertEqual(report["pages"][0]["target"]["status"], "ERROR")

    def test_empty_responses_cannot_match(self):
        self.source["content"] = ""
        self.target["content"] = ""
        self.assertEqual(self.run_comparison()["status"], "NOT_MEASURED")

    def test_non_html_responses_cannot_match(self):
        self.source["headers"]["Content-Type"] = "application/json"
        self.target["headers"]["Content-Type"] = "application/json"
        self.source["content"] = self.target["content"] = '{}'
        self.assertEqual(self.run_comparison()["status"], "NOT_MEASURED")

    def test_missing_content_type_does_not_claim_html_capture(self):
        self.target["headers"] = {}
        self.assertEqual(self.run_comparison()["status"], "NOT_MEASURED")

    def test_conflicting_canonicals_cannot_match(self):
        self.target["content"] += '<link rel="canonical" href="https://unexpected.example/">'
        self.assertEqual(self.run_comparison()["status"], "NOT_MEASURED")

    def test_disappeared_page_is_a_status_difference(self):
        self.target["status_code"] = 404
        report = self.run_comparison()
        self.assertEqual(report["status"], "DIFFERENCES")
        self.assertIn("status_code", [d["field"] for d in report["pages"][0]["differences"]])

    def test_empty_manifest_is_rejected(self):
        self.manifest["pages"] = []
        with self.assertRaises(ValueError):
            migration.compare_manifest(self.manifest, self.root)

    def test_host_override_path_is_rejected(self):
        self.manifest["pages"][0]["path"] = "//other.example/offres/"
        with self.assertRaises(ValueError):
            migration.compare_manifest(self.manifest, self.root)

    def test_approval_without_evidence_is_rejected(self):
        self.manifest["pages"][0]["approved_differences"] = {
            "canonical": {"source": None, "target": None, "authority": "GREGG"}
        }
        with self.assertRaises(ValueError):
            migration.compare_manifest(self.manifest, self.root)

    def test_secret_headers_are_not_included_in_report(self):
        self.target["headers"]["Set-Cookie"] = "session=confidential"
        self.target["headers"]["Authorization"] = "confidential"
        report = self.run_comparison()
        self.assertNotIn("confidential", json.dumps(report))

    def test_cli_emits_provenance_and_difference_exit_code(self):
        self.target["content"] = self.target["content"].replace("Nos offres", "Nos services")
        self.run_comparison()
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(self.manifest))
        report_path = self.root / "report.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "skills/seo/scripts/migration_compare.py"),
             str(manifest_path), "--output", str(report_path)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(report_path.read_text())
        self.assertEqual(report["status"], "DIFFERENCES")
        self.assertEqual(len(report["manifest_sha256"]), 64)
        self.assertEqual(len(report["tool"]["sha256"]), 64)
        self.assertEqual(len(report["pages"][0]["source"]["capture_sha256"]), 64)

    def test_cli_rejects_invalid_manifest_with_error_exit_code(self):
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text('{"pages": []}')
        result = subprocess.run(
            [sys.executable, str(ROOT / "skills/seo/scripts/migration_compare.py"), str(manifest_path)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
