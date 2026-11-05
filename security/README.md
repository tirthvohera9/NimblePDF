# Local-first security helpers

This directory contains dependency-free Python helpers for:

- conservative filename sanitization;
- local file size, extension, symlink, and PDF-signature validation;
- metadata privacy filtering; and
- validation of text redaction plans.

These helpers never upload files or call a service. They validate policy; they
do not perform PDF parsing or rewriting. **Visual overlays, black rectangles,
annotations, and similar UI operations are not secure redaction**: sensitive
content can remain extractable underneath. A caller must rewrite/remove the
underlying content and verify the resulting file independently.

Run the examples/tests with:

```text
python -m unittest discover security/tests
```
