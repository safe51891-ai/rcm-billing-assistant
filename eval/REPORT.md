# RCM Assistant: Evaluation Report

Data: 200 synthetic clinical notes (`eval/generate_notes.py`). Each note has known identifiers (name, MRN, phone, email, DOB), known current diagnoses, and a negated mention (for example "denies asthma") that must not be coded.

## Redaction: identifiers that survived

| Source of patient name | Name leaks | Other identifiers (MRN, phone, email, DOB) |
|---|---|---|
| Note text only (no EHR record) | **40.5%** (81/200) | 0% |
| Patient name from EHR record | **0%** (0/200) | 0% |

Reading: without the patient's record, the rules miss names written in narrative. In production the name always comes from the EHR, so the second row is the one that applies.

## Coding: rule set, public ICD-10-CM codes

| Version | Precision | Recall | Exact match per note |
|---|---|---|---|
| Without negation handling | 0.771 | 1.000 | 38.5% |
| With negation handling | 1.000 | 1.000 | 100% |

## Limits

- The templates are simple and the codes come from five conditions. Real notes are messier, so expect lower numbers on real data.
- The rule coder does not know about abbreviations beyond T2DM or UTI, misspellings, or conditions outside its five rules.
- Redaction tests cover the identifier formats above. Real notes also contain addresses, employer names, and free-text family names, which these rules do not catch.
- Measure on a sample of real, de-identified notes before relying on any number.
