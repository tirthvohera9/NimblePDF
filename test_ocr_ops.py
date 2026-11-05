import io
import unittest
from PIL import Image, ImageDraw, ImageFont

from ocr_ops import ocr_pdf, redact_terms
from pdf_ops import _reader


class OcrOperationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        image = Image.new("RGB", (1200, 500), "white")
        font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 64)
        ImageDraw.Draw(image).text((80, 180), "Confidential alice@example.com", fill="black", font=font)
        output = io.BytesIO()
        image.save(output, "PDF", resolution=150)
        cls.pdf = output.getvalue()

    def test_ocr_creates_extractable_output(self):
        output = ocr_pdf(self.pdf)
        self.assertTrue((_reader(output).pages[0].extract_text() or "").strip())

    def test_redaction_removes_term_from_extractable_output(self):
        output = redact_terms(self.pdf, ["alice@example.com"])
        text = "\n".join((page.extract_text() or "").lower() for page in _reader(output).pages)
        self.assertNotIn("alice@example.com", text)


if __name__ == "__main__":
    unittest.main()
