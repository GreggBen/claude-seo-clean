import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "fix_correlate", ROOT / "skills/seo/scripts/fix_correlate.py"
)
correlator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(correlator)


class MarkupCorrelationTests(unittest.TestCase):
    def findings(self, claimed, visible):
        return correlator.correlate_markup_vs_visible(
            {
                "available": True,
                "text": visible,
                "jsonld": [{"@type": "Answer", "text": claimed}],
            },
            "raw",
            {},
        )

    def test_html_answer_matches_its_visible_text(self):
        self.assertEqual(
            self.findings(
                "<p>La couverture <strong>prévoyance</strong> protège votre activité.</p>",
                "La couverture prévoyance protège votre activité.",
            ),
            [],
        )

    def test_entities_and_block_boundaries_match_visible_text(self):
        self.assertEqual(
            self.findings(
                "<p>Santé&nbsp;&amp;&nbsp;prévoyance</p><p>Une protection adaptée.</p>",
                "Santé & prévoyance Une protection adaptée.",
            ),
            [],
        )

    def test_genuinely_missing_answer_remains_reported(self):
        findings = self.findings(
            "<p>Cette réponse décrit une protection totalement absente de la page.</p>",
            "Cette page présente seulement les coordonnées du cabinet.",
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["state"], "OBSERVED")
        self.assertEqual(findings[0]["evidence"]["unmatched_count"], 1)

    def test_plain_text_comparison_is_preserved(self):
        self.assertEqual(
            self.findings(
                "Une protection adaptée à votre activité professionnelle.",
                "Une protection adaptée à votre activité professionnelle.",
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
