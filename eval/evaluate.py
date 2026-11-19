"""Evaluate redaction leaks and code suggestions. Run: python -m eval.evaluate

Compares the rules with and without negation handling, so the effect of each change is measured.
"""
import json
import re
from pathlib import Path

import rcm.coding as coding
from rcm.privacy import redact_note

DATA = Path("eval/data/notes.json")


def evaluate_redaction(records, use_known_name: bool):
    leaks = {"name": 0, "mrn": 0, "phone": 0, "email": 0, "dob": 0}
    for r in records:
        known = r["identifiers"]["name"] if use_known_name else None
        out = redact_note(r["note"], known_name=known)
        ids = r["identifiers"]
        for key, value in ids.items():
            if key == "dob":
                value = value.replace("/", "/")
            if re.search(re.escape(value), out):
                leaks[key] += 1
    total = len(records)
    return {k: {"leaked": v, "rate": round(v / total, 3)} for k, v in leaks.items()}


def evaluate_codes(records):
    tp = fp = fn = exact = 0
    for r in records:
        known = r["identifiers"]["name"]
        predicted = sorted(c.code for c in coding.suggest_codes_rules(redact_note(r["note"], known_name=known)))
        gold = set(r["codes"])
        pred = set(predicted)
        tp += len(gold & pred)
        fp += len(pred - gold)
        fn += len(gold - pred)
        exact += int(pred == gold)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "exact_match": round(exact / len(records), 3)}


if __name__ == "__main__":
    records = json.loads(DATA.read_text(encoding="utf-8"))
    print("redaction, names from note text only:", json.dumps(evaluate_redaction(records, False)["name"]))
    print("redaction, patient name from EHR record:", json.dumps(evaluate_redaction(records, True)))
    with_negation = evaluate_codes(records)
    original = coding.NEGATION
    coding.NEGATION = re.compile(r"(?!x)x")  # disable negation handling for the baseline
    without_negation = evaluate_codes(records)
    coding.NEGATION = original
    print("codes without negation handling:", without_negation)
    print("codes with negation handling:   ", with_negation)
