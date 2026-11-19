"""Synthetic clinical notes with known identifiers and known diagnoses (ground truth for evaluation)."""
import json
import random
from pathlib import Path

from faker import Faker

CONDITIONS = {
    "type 2 diabetes": "E11.9",
    "hypertension": "I10",
    "pneumonia": "J18.9",
    "asthma": "J45.909",
    "urinary tract infection": "N39.0",
}
NEGATABLE = ["denies asthma", "no hypertension", "without pneumonia", "negative for urinary tract infection"]
TEMPLATES = [
    "Patient: {name}, MRN: {mrn}, DOB: {dob}. Follow-up visit. Known {cond}. Phone {phone}. {extra}",
    "Mr. {first} {last} seen today for review. {cond} stable. Contact {email}. {extra}",
    "Name: {name}\nAddress: {address}\nAssessment: {cond}. {extra} Date of service {dos}.",
    "{name} presents with symptoms. History notable for {cond}. MRN {mrn}. {extra}",
]


def make(n: int, out: Path, seed: int = 11) -> None:
    rng = random.Random(seed)
    fake = Faker()
    Faker.seed(seed)
    records = []
    for i in range(n):
        first, last = fake.first_name(), fake.last_name()
        name = f"{first} {last}"
        mrn = str(rng.randint(10000, 99999))
        dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y")
        phone = fake.numerify("###-###-####")
        email = f"{first.lower()}.{last.lower()}@{fake.domain_name()}"
        address = fake.street_address()
        positives = rng.sample(list(CONDITIONS), k=rng.randint(1, 3))
        cond_text = " and ".join(positives)
        extra = rng.choice(NEGATABLE) + "."  # a negated mention that must NOT be coded
        note = rng.choice(TEMPLATES).format(name=name, first=first, last=last, mrn=mrn, dob=dob, phone=phone,
                                             email=email, address=address, cond=cond_text, extra=extra,
                                             dos=fake.date_this_year().isoformat())
        if rng.random() < 0.3:  # name reappears in the narrative, as clinicians often write it
            note += f" {name} agreed with the plan."
        records.append({
            "note": note,
            "identifiers": {"name": name, "mrn": mrn, "phone": phone, "email": email, "dob": dob},
            "codes": sorted(CONDITIONS[c] for c in positives),
        })
    out.mkdir(parents=True, exist_ok=True)
    (out / "notes.json").write_text(json.dumps(records, indent=2), encoding="utf-8")


if __name__ == "__main__":
    make(200, Path("eval/data"))
    print("generated 200 notes in eval/data/notes.json")
