import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "skills/seo/hooks/validate-schema.py"
SPEC = importlib.util.spec_from_file_location("schema_hook", HOOK_PATH)
hook = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hook)


class SchemaValidationTests(unittest.TestCase):
    def validate(self, data):
        return hook.validate_jsonld(
            '<script type="application/ld+json">' + json.dumps(data) + "</script>"
        )

    def test_graph_nodes_inherit_context(self):
        self.assertEqual(
            self.validate({
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "Organization", "@id": "https://example.com/#organization"},
                    {"@type": "WebPage", "@id": "https://example.com/"},
                ],
            }),
            [],
        )

    def test_missing_graph_node_type_is_reported(self):
        errors = self.validate({
            "@context": "https://schema.org",
            "@graph": [{"name": "Un organisme sans type"}],
        })
        self.assertTrue(any("@graph[0]" in error and "@type" in error for error in errors))

    def test_script_with_extra_attributes_is_validated(self):
        errors = hook.validate_jsonld(
            '<script id="identity" type="application/ld+json">{invalid}</script>'
        )
        self.assertTrue(any("Invalid JSON" in error for error in errors))

    def test_multiple_types_are_supported(self):
        self.assertEqual(self.validate({
            "@context": "https://schema.org",
            "@type": ["Organization", "InsuranceAgency"],
        }), [])

    def test_scalar_payload_is_not_silently_accepted(self):
        self.assertTrue(self.validate(42))

    def test_untyped_script_does_not_crash_validation(self):
        self.assertEqual(hook.validate_jsonld('<script type>console.log("ok")</script>'), [])

    def test_nested_placeholder_in_graph_is_reported(self):
        self.assertTrue(any("placeholder" in error.lower() for error in self.validate({
            "@context": "https://schema.org",
            "@graph": [{"@type": "Organization", "name": "[Business Name]"}],
        })))

    def test_dynamic_tsx_is_reported_as_not_measured(self):
        self.assert_dynamic_source(
            '<script type="application/ld+json" '
            'dangerouslySetInnerHTML={{ __html: serializeJsonLd(data) }} />'
        )

    def test_jsx_stringify_expression_is_not_misread_as_invalid_json(self):
        self.assert_dynamic_source(
            '<script type="application/ld+json">{JSON.stringify(data)}</script>'
        )

    def test_jsx_type_expression_is_not_misread_as_no_schema(self):
        self.assert_dynamic_source(
            '<script type={"application/ld+json"} '
            'dangerouslySetInnerHTML={{ __html: serializeJsonLd(data) }} />'
        )

    def test_stringify_in_served_html_remains_invalid(self):
        self.assertTrue(hook.validate_jsonld(
            '<script type="application/ld+json">{JSON.stringify(data)}</script>'
        ))

    def test_static_block_does_not_hide_dynamic_jsx_block(self):
        report = hook.inspect_jsonld(
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Organization"}</script>'
            '<script type={"application/ld+json"} '
            'dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />',
            source=True,
        )
        self.assertEqual(report["status"], "NOT_MEASURED")
        self.assertEqual(report["blocks"], 1)
        self.assertEqual(report["dynamic_blocks"], 1)

    def assert_dynamic_source(self, content):
        with tempfile.TemporaryDirectory() as directory:
            component = Path(directory) / "JsonLd.tsx"
            component.write_text(content)
            result = subprocess.run(
                [sys.executable, str(HOOK_PATH), str(component)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0)
        self.assertIn("NOT_MEASURED", result.stdout)


if __name__ == "__main__":
    unittest.main()
