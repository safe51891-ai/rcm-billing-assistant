"""Strip direct identifiers from clinical text before it leaves the system (HIPAA minimum-necessary).

Works on free-text notes: labeled fields, honorific names ("Mr. Ali Khan"), and standard identifier formats.
A name is removed when it follows a title or a label; a missed name is the main risk, so the eval reports leaks.
"""
import re

_NAME = r"[A-Z][a-z]+(?:\s[A-Z][a-z'\-]+){1,2}"

_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"\b(?:MRN|Medical Record(?: No\.?)?|Patient ID|Acct(?:ount)?)[:#\s]*[A-Za-z0-9-]+", re.IGNORECASE), "[MRN]"),
    (re.compile(r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", re.IGNORECASE), "[DOB]"),
    (re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"), "[DATE]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), "[EMAIL]"),
    (re.compile(r"\(?\b\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b(?:Patient|Name|Pt)[:\s]+" + _NAME), "[NAME]"),
    (re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+" + _NAME), "[NAME]"),
    (re.compile(r"\b(?:Address)[:\s]+[^\n,]+"), "[ADDRESS]"),
]


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


_HEADER_NAME = re.compile(r"\b(?:Patient|Name|Pt)[:\s]+(" + _NAME + ")")


def scrub_patient_name(text: str, known_name: str | None = None) -> str:
    """Remove every mention of the patient's name.

    Best source: known_name, from the EHR's patient record (structured data, always available in a real system).
    Fallback: a name found after a label in the note header. Narrative mentions without a label are
    only caught when known_name is supplied.
    """
    names = {m.group(1) for m in _HEADER_NAME.finditer(text)}
    if known_name:
        names.add(known_name)
    for name in sorted(names, key=len, reverse=True):
        text = re.sub(re.escape(name), "[NAME]", text)
    return text


def redact_note(text: str, known_name: str | None = None) -> str:
    return redact(scrub_patient_name(text, known_name))
