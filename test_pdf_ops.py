import base64
import unittest

from pypdf import PdfWriter

from server import analyze_payload, operation_payload


def pdf_bytes(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=200, height=200)
    import io
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class PdfOperationTests(unittest.TestCase):
    def test_merge_and_verify(self):
        files = [{"name": f"{index}.pdf", "data": base64.b64encode(pdf_bytes(1)).decode()} for index in (1, 2)]
        status, payload = operation_payload({"operation": "merge", "files": files})
        self.assertEqual(status, 200)
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["output"]["pageCount"], 2)

    def test_split_rejects_out_of_range_page(self):
        file = {"name": "input.pdf", "data": base64.b64encode(pdf_bytes(1)).decode()}
        status, payload = operation_payload({"operation": "split", "files": [file], "pages": [2]})
        self.assertEqual(status, 422)
        self.assertEqual(payload["code"], "INVALID_PAGE")

    def test_rotate_verifies_output(self):
        file = {"name": "input.pdf", "data": base64.b64encode(pdf_bytes(1)).decode()}
        status, payload = operation_payload({"operation": "rotate", "files": [file], "pages": [1], "degrees": 90})
        self.assertEqual(status, 200)
        self.assertTrue(payload["verified"])

    def test_metadata_sanitization_verifies_output(self):
        file = {"name": "input.pdf", "data": base64.b64encode(pdf_bytes(1)).decode()}
        status, payload = operation_payload({"operation": "sanitize-metadata", "files": [file]})
        self.assertEqual(status, 200)
        self.assertTrue(payload["verified"])

    def test_analysis_returns_accessibility_checks(self):
        file = {"name": "input.pdf", "data": base64.b64encode(pdf_bytes(1)).decode()}
        status, payload = analyze_payload(file)
        self.assertEqual(status, 200)
        self.assertIn("accessibility", payload["analysis"])
        self.assertEqual(payload["analysis"]["pageCount"], 1)


if __name__ == "__main__":
    unittest.main()
