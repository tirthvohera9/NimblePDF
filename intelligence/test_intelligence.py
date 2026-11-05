import unittest

from intelligence.extraction import TextDocumentExtractor
from intelligence.health import recommend_pdf_health
from intelligence.intent import parse_workflow_intent
from intelligence.pii import detect_pii


class IntelligenceTests(unittest.TestCase):
    def test_intent_is_deterministic_and_structured(self):
        result = parse_workflow_intent("Please compress this PDF")
        self.assertEqual(result.action, "compress")
        self.assertIn("pdf", result.entities["formats"])
        self.assertGreaterEqual(result.confidence, 0.7)

    def test_health_recommendations_are_deterministic(self):
        result = recommend_pdf_health({"page_count": 1, "file_size_bytes": 30 * 1024 * 1024, "has_text": False})
        self.assertEqual(result.score, 76)
        self.assertEqual([item.code for item in result.findings], ["large-file", "no-text"])

    def test_pii_masks_and_validates_cards(self):
        result = detect_pii("Contact jane@example.com or 4111 1111 1111 1111.")
        self.assertEqual([item.kind for item in result], ["email", "credit_card"])
        self.assertEqual(result[0].masked_value, "****@example.com")

    def test_extraction_adapter(self):
        result = TextDocumentExtractor().extract(["first page", ""])
        self.assertEqual(result.pages[0].page_number, 1)
        self.assertEqual(result.pages[1].confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
