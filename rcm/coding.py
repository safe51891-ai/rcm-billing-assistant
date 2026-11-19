"""Suggest ICD-10-CM diagnosis codes from a clinical note, for a human coder to confirm.

Demonstration rule set using public ICD-10-CM codes. Real coding needs a current licensed code set,
payer rules, and a certified coder. Negated mentions ("denies asthma", "no hypertension") are not coded.
"""
import os
import re
from dataclasses import dataclass

from rcm.privacy import redact_note

RULES = [
    (r"type 2 diabetes|t2dm", "E11.9", "Type 2 diabetes mellitus without complications"),
    (r"hypertension|high blood pressure", "I10", "Essential (primary) hypertension"),
    (r"pneumonia", "J18.9", "Pneumonia, unspecified organism"),
    (r"asthma", "J45.909", "Unspecified asthma, uncomplicated"),
    (r"urinary tract infection|\bUTI\b", "N39.0", "Urinary tract infection, site not specified"),
]

NEGATION = re.compile(r"\b(?:no|denies|denied|without|negative for|ruled out|rule out|r/o|not)\b[^.;\n]{0,25}$",
                      re.IGNORECASE)


@dataclass
class CodeSuggestion:
    code: str
    description: str
    evidence: str
    needs_review: bool = True  # every code is confirmed by a coder


def suggest_codes_rules(note: str) -> list[CodeSuggestion]:
    found = {}
    for pattern, code, description in RULES:
        for m in re.finditer(pattern, note, flags=re.IGNORECASE):
            before = note[max(0, m.start() - 40):m.start()]
            if NEGATION.search(before):
                continue  # "denies asthma" is not a current diagnosis
            found.setdefault(code, CodeSuggestion(code, description, m.group(0)))
            break
    return list(found.values())


def suggest_codes(note: str) -> list[CodeSuggestion]:
    """Redacts first. Uses Claude when ANTHROPIC_API_KEY is set, otherwise the rule set."""
    safe = redact_note(note)
    if not os.getenv("ANTHROPIC_API_KEY"):
        return suggest_codes_rules(safe)
    import json

    import anthropic

    client = anthropic.Anthropic()
    prompt = ('List current ICD-10-CM diagnosis codes for this note as JSON '
              '[{"code": "...", "description": "...", "evidence": "..."}]. Exclude negated conditions. '
              'Return only JSON.\n\n' + safe)
    msg = client.messages.create(model=os.getenv("AGENT_MODEL", "claude-haiku-5-5"), max_tokens=400,
                                 messages=[{"role": "user", "content": prompt}])
    m = re.search(r"\[.*\]", msg.content[0].text, flags=re.DOTALL)
    items = json.loads(m.group(0)) if m else []
    return [CodeSuggestion(i["code"], i["description"], i.get("evidence", "")) for i in items]
