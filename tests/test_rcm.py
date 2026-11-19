from datetime import date
from decimal import Decimal

import pytest

from rcm.coding import suggest_codes, suggest_codes_rules
from rcm.denials import Denial, triage, work_queue
from rcm.privacy import redact, redact_note

TODAY = date(2026, 11, 19)


def test_redaction_removes_identifiers():
    note = "Patient: Jane Doe, MRN: 88421, DOB: 03/14/1961, call (555) 123-4567, jane@example.com, SSN 123-45-6789."
    out = redact(note)
    for leaked in ["Jane Doe", "88421", "03/14/1961", "555", "jane@example.com", "123-45-6789"]:
        assert leaked not in out


def test_rule_coder_finds_known_conditions_with_evidence():
    codes = suggest_codes_rules("Pt with type 2 diabetes and hypertension, follow-up in 3 months.")
    assert [c.code for c in codes] == ["E11.9", "I10"]
    assert all(c.needs_review for c in codes)  # every code needs a coder's confirmation
    assert codes[0].evidence.lower() == "type 2 diabetes"


def test_suggest_codes_uses_redacted_text_offline():
    codes = suggest_codes("Jane Doe, MRN: 99, has asthma.")
    assert [c.code for c in codes] == ["J45.909"]


def test_triage_prioritizes_urgent_and_valuable_claims():
    soon = Denial("C-1", "Payer A", Decimal("500"), date(2026, 11, 1), "not_covered", date(2026, 12, 1))
    late = Denial("C-2", "Payer A", Decimal("500"), date(2026, 11, 1), "not_covered", date(2026, 11, 25))
    queue = work_queue([soon, late], TODAY)
    assert [i.claim_id for i in queue] == ["C-2", "C-1"]


def test_appealable_denial_gets_draft_that_needs_review():
    d = Denial("C-9", "Payer B", Decimal("1200.50"), date(2026, 11, 2), "authorization", date(2026, 12, 2))
    item = triage(d, TODAY)
    assert item.appeal_draft is not None
    assert "$1,200.50" in item.appeal_draft
    assert item.status == "needs_review"


def test_missing_info_is_fixed_not_appealed():
    d = Denial("C-3", "Payer B", Decimal("80"), date(2026, 11, 2), "missing_info", date(2026, 12, 2))
    item = triage(d, TODAY)
    assert item.appeal_draft is None
    assert "resubmit" in item.action


def test_expired_window_escalates_without_draft():
    d = Denial("C-4", "Payer B", Decimal("300"), date(2026, 9, 1), "not_covered", date(2026, 10, 1))
    item = triage(d, TODAY)
    assert item.appeal_draft is None
    assert "escalate" in item.notes[0]


def test_unknown_reason_is_rejected():
    d = Denial("C-5", "Payer B", Decimal("1"), date(2026, 11, 2), "made_up", date(2026, 12, 2))
    with pytest.raises(ValueError):
        triage(d, TODAY)


def test_narrative_name_is_removed_when_ehr_name_is_known():
    note = "Mr. Ali Khan seen today. Ali Khan agreed with the plan. Asthma."
    out = redact_note(note, known_name="Ali Khan")
    assert "Khan" not in out


def test_title_based_name_removed_without_ehr_name():
    assert "Hassan" not in redact_note("Dr. Sara Hassan reviewed the chart.")


def test_negated_condition_is_not_coded():
    codes = [c.code for c in suggest_codes_rules("Patient denies asthma. Has hypertension.")]
    assert codes == ["I10"]


def test_ehr_name_reaches_the_coder_without_leaking_into_codes():
    codes = suggest_codes("Ali Khan has asthma.", )
    assert [c.code for c in codes] == ["J45.909"]
