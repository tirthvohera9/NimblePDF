import tempfile
import unittest
from pathlib import Path

from security import (
    FileValidator,
    FileValidationError,
    MetadataPolicy,
    MetadataPolicyError,
    RedactionRange,
    RedactionSafetyError,
    check_redaction_plan,
    safe_filename,
    sanitize_metadata,
)
from security.files import FileLimits


class SecurityHelpersTests(unittest.TestCase):
    def test_safe_filename_removes_path_and_reserved_name(self):
        self.assertEqual(safe_filename(r"..\CON.txt"), "_CON.txt")
        self.assertEqual(safe_filename("..."), "document")

    def test_pdf_validation_checks_signature_and_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.pdf"
            path.write_bytes(b"%PDF-1.7\n")
            result = FileValidator().validate(path)
            self.assertEqual(result.mime_type, "application/pdf")
            with self.assertRaises(FileValidationError):
                FileValidator(FileLimits(max_bytes=2)).validate(path)

    def test_metadata_policy_removes_private_fields(self):
        value = sanitize_metadata({"Author": "Ada", "custom": "ok"})
        self.assertEqual(value, {"custom": "ok"})
        with self.assertRaises(MetadataPolicyError):
            sanitize_metadata({"custom": "x"}, MetadataPolicy(max_value_length=0))

    def test_redaction_ranges_must_not_overlap(self):
        self.assertEqual(
            check_redaction_plan("secret name", [RedactionRange(0, 6)]),
            (RedactionRange(0, 6),),
        )
        with self.assertRaises(RedactionSafetyError):
            check_redaction_plan("secret", [RedactionRange(0, 4), RedactionRange(3, 6)])


if __name__ == "__main__":
    unittest.main()
