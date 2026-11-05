"""Evidence-first share-readiness analysis with no raw PII in the response."""

from __future__ import annotations

from pdf_ops import PdfOperationError, _reader, analyze
from intelligence.pii import detect_pii


def safe_send_report(data: bytes) -> dict:
    reader = _reader(data)
    report = analyze(data)
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    pii = detect_pii(text)
    metadata = reader.metadata or {}
    risks: list[dict] = []

    for finding in pii:
        risks.append({
            "kind": "personal-data",
            "severity": "high" if finding.kind in {"ssn", "credit_card"} else "medium",
            "label": finding.kind.replace("_", " "),
            "masked": finding.masked_value,
            "confidence": finding.confidence,
            "page": next((page["page"] for page in report["pages"] if page["preview"] and finding.value in page["preview"]), None),
            "recommendation": "Redact this value before sharing." if finding.kind in {"ssn", "credit_card"} else "Review whether this value should be shared.",
        })
    if "/JavaScript" in str(reader.root_object) or "/JS" in str(reader.root_object):
        risks.append({"kind": "active-content", "severity": "high", "label": "JavaScript", "recommendation": "Sanitize the PDF before sharing."})
    if "/EmbeddedFiles" in str(reader.root_object):
        risks.append({"kind": "embedded-content", "severity": "high", "label": "Embedded files", "recommendation": "Inspect or remove embedded files."})
    if metadata:
        private_keys = [key for key in metadata if key in {"/Author", "/Creator", "/Producer", "/Subject"} and metadata.get(key)]
        if private_keys:
            risks.append({"kind": "metadata", "severity": "low", "label": "Descriptive metadata", "fields": private_keys, "recommendation": "Sanitize metadata if the document identity matters."})
    failed_accessibility = [check["id"] for check in report["accessibility"]["checks"] if not check["pass"]]
    if failed_accessibility:
        risks.append({"kind": "accessibility", "severity": "low", "label": "Accessibility gaps", "checks": failed_accessibility, "recommendation": "Review accessibility before public distribution."})
    high = sum(risk["severity"] == "high" for risk in risks)
    medium = sum(risk["severity"] == "medium" for risk in risks)
    status = "blocked" if high else "review" if medium or risks else "ready"
    return {
        "status": status,
        "safeToSend": status == "ready",
        "riskCount": len(risks),
        "riskSummary": {"high": high, "medium": medium, "low": len(risks) - high - medium},
        "risks": risks,
        "evidence": {"pageCount": report["pageCount"], "textPages": report["textPages"], "metadataPresent": bool(metadata)},
    }
