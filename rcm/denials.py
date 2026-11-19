"""Denial triage: categorize, prioritize by deadline and dollars, and draft an appeal for human approval.

Reason categories here are internal labels. Map your payer's remittance codes to them in REASON_MAP.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

REASON_MAP = {
    "missing_info": "Missing or invalid information on the claim",
    "not_covered": "Service not covered under the plan",
    "authorization": "Prior authorization required or missing",
    "timely_filing": "Filed after the payer's deadline",
}

ACTION = {
    "missing_info": "Correct the claim and resubmit (no appeal needed)",
    "not_covered": "Appeal with medical necessity documentation",
    "authorization": "Appeal with the authorization record or request retro-authorization",
    "timely_filing": "Appeal with proof of timely submission (clearinghouse acceptance report)",
}

APPEALABLE = {"not_covered", "authorization", "timely_filing"}

APPEAL_TEMPLATE = """Dear {payer} Appeals Department,

We are appealing claim {claim_id} for {amount} denied on {denied_on} with the reason: {reason}.

{argument}

Please reconsider this claim. Supporting documents are attached.

Sincerely,
{practice}
"""


@dataclass
class Denial:
    claim_id: str
    payer: str
    amount: Decimal
    denied_on: date
    reason_key: str
    appeal_deadline: date


@dataclass
class TriageItem:
    claim_id: str
    category: str
    action: str
    days_left: int
    priority: float
    appeal_draft: str | None = None
    status: str = "needs_review"  # the draft is never sent without approval
    notes: list[str] = field(default_factory=list)


def triage(denial: Denial, today: date) -> TriageItem:
    if denial.reason_key not in REASON_MAP:
        raise ValueError(f"unknown denial reason: {denial.reason_key}")
    days_left = (denial.appeal_deadline - today).days
    # Urgency (fewer days left) times dollars: the most valuable, most urgent claims first.
    urgency = 1 / max(days_left, 1)
    priority = round(float(denial.amount) * urgency, 2)
    item = TriageItem(
        claim_id=denial.claim_id,
        category=REASON_MAP[denial.reason_key],
        action=ACTION[denial.reason_key],
        days_left=days_left,
        priority=priority,
    )
    if days_left < 0:
        item.notes.append("appeal window closed: escalate to supervisor")
    elif denial.reason_key in APPEALABLE:
        item.appeal_draft = APPEAL_TEMPLATE.format(
            payer=denial.payer,
            claim_id=denial.claim_id,
            amount=f"${denial.amount:,.2f}",
            denied_on=denial.denied_on.isoformat(),
            reason=REASON_MAP[denial.reason_key].lower(),
            argument="[Add the clinical or policy argument, referencing the attached records.]",
            practice="[Practice name]",
        )
    return item


def work_queue(denials: list[Denial], today: date) -> list[TriageItem]:
    items = [triage(d, today) for d in denials]
    return sorted(items, key=lambda i: i.priority, reverse=True)
