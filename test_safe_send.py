import base64
import io
import unittest

from pypdf import PdfWriter

from safe_send import safe_send_report


class SafeSendTests(unittest.TestCase):
    def test_detects_share_risk_without_returning_raw_email(self):
        writer = PdfWriter()
        writer.add_blank_page(200, 200)
        writer.add_metadata({"/Author": "Internal Team"})
        output = io.BytesIO()
        writer.write(output)
        report = safe_send_report(output.getvalue())
        self.assertIn(report["status"], {"review", "ready"})
        self.assertTrue(any(risk["kind"] == "metadata" for risk in report["risks"]))
        self.assertNotIn("Internal Team", str(report))


if __name__ == "__main__":
    unittest.main()
