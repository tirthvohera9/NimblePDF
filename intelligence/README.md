# NimblePDF local document intelligence

This directory is a dependency-free, local-first intelligence layer. It does
not read files, call external APIs, execute document content, or send data
anywhere. A host application supplies metadata or decoded text and may plug in
its own local PDF parser through `DocumentExtractor`.

## Interfaces

```python
from intelligence import detect_pii, parse_workflow_intent, recommend_pdf_health

intent = parse_workflow_intent("Compress this PDF")
pii = detect_pii("Email jane@example.com")
health = recommend_pdf_health({"page_count": 2, "has_text": True})
```

All findings have bounded confidence scores. PII values should be treated as
sensitive even though `masked_value` is provided for logs and UI.

## Run the tests

From the project directory:

```text
python -m unittest discover -s intelligence -p "test_*.py" -v
```
