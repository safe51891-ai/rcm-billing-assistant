# RCM Medical Billing Assistant

Helps a billing team move faster without removing human review. It does three things:

1. **Redacts PHI** (`rcm/privacy.py`) from clinical notes before any external LLM call. Covers SSN, MRN, DOB, dates, email, phone, and patient names.
2. **Suggests ICD-10-CM codes** (`rcm/coding.py`) with the evidence phrase for each. Rules run offline; Claude runs when `ANTHROPIC_API_KEY` is set. Every code is marked `needs_review`.
3. **Triages denials** (`rcm/denials.py`): categorizes each denial, computes days left on the appeal window, ranks the queue by urgency times dollars, and drafts appeals. Drafts stay `needs_review`. Expired windows escalate instead of generating a draft.

## Measured results (synthetic notes, see eval/REPORT.md)
- Names left in notes: 40.5% without the EHR patient name, **0%** with it.
- Coding precision: 77% without negation handling, **100%** with it (synthetic data; real notes will be harder).

## Run
```bash
pip install -r requirements.txt
pytest -q                            # 12 tests, offline
python -m eval.generate_notes        # 200 synthetic notes
python -m eval.evaluate              # redaction and coding metrics
```

## Before production
- Use a licensed, current code set and a certified coder's review. The rules here are a demonstration with a few public ICD-10-CM codes.
- Map real payer remittance codes (CARC/RARC) into `REASON_MAP`. The categories here are internal labels.
- Keep the redaction tests in CI. Add a BAA with the LLM vendor before sending real PHI, or run a model you host.
- Log every suggestion and every human decision for audit.
