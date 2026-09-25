from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.retrieval.search import PharmoraRetriever


CATALOG_PATH = Path("data/catalog/medicines.json")


@dataclass(frozen=True)
class RecallCase:
    name: str
    medicine_name: str
    question: str
    expected_section: str


CASES = [
    RecallCase(
        name="Doliprane effets indésirables",
        medicine_name="DOLIPRANE 500 mg, gélule",
        question="Quels sont les effets indésirables de ce médicament ?",
        expected_section="4.8",
    ),
    RecallCase(
        name="Doliprane paraphrase effets",
        medicine_name="DOLIPRANE 500 mg, gélule",
        question="Quels problèmes ou réactions gênantes peuvent apparaître après sa prise ?",
        expected_section="4.8",
    ),
    RecallCase(
        name="Ibuprofène grossesse",
        medicine_name="IBUPROFENE ARROW 5 %, gel",
        question="Peut-on utiliser ce médicament pendant la grossesse ?",
        expected_section="4.6",
    ),
    RecallCase(
        name="Ibuprofène paraphrase grossesse",
        medicine_name="IBUPROFENE ARROW 5 %, gel",
        question="Que faut-il savoir si une femme enceinte utilise ce gel ?",
        expected_section="4.6",
    ),
    RecallCase(
        name="Amoxicilline indications",
        medicine_name="AMOXICILLINE BENTA 500 mg, gélule",
        question="Dans quels cas cet antibiotique est-il utilisé ?",
        expected_section="4.1",
    ),
    RecallCase(
        name="Amoxicilline paraphrase indications",
        medicine_name="AMOXICILLINE BENTA 500 mg, gélule",
        question="Pourquoi pourrait-on donner ce médicament à un patient ?",
        expected_section="4.1",
    ),
]


def load_catalog() -> list[dict]:
    data = json.loads(
        CATALOG_PATH.read_text(
            encoding="utf-8"
        )
    )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(
            data.get("medicines"),
            list,
        ):
            return data["medicines"]

        return [
            value
            for value in data.values()
            if isinstance(value, dict)
        ]

    raise RuntimeError(
        "Format de catalogue non reconnu."
    )


def get_name(
    medicine: dict,
) -> str:
    for key in (
        "name",
        "medicine_name",
        "denomination",
    ):
        value = medicine.get(key)

        if value:
            return str(value).strip()

    raise RuntimeError(
        "Nom du médicament absent."
    )


def get_cis(
    medicine: dict,
) -> str:
    for key in (
        "cis",
        "CIS",
        "cis_code",
    ):
        value = medicine.get(key)

        if value is not None:
            return str(value).strip()

    raise RuntimeError(
        "CIS absent."
    )


def normalize(
    value: str,
) -> str:
    return " ".join(
        value.casefold().split()
    )


def resolve(
    medicines: list[dict],
    medicine_name: str,
) -> dict:
    target = normalize(
        medicine_name
    )

    matches = [
        medicine
        for medicine in medicines
        if normalize(
            get_name(medicine)
        ) == target
    ]

    if len(matches) != 1:
        raise LookupError(
            f"Résolution impossible pour "
            f"{medicine_name}"
        )

    return matches[0]


def first_expected_rank(
    results: list[dict],
    expected_section: str,
) -> int | None:
    for rank, result in enumerate(
        results,
        start=1,
    ):
        section = str(
            result.get(
                "section_number",
                "",
            )
        ).strip()

        if section == expected_section:
            return rank

    return None


def main():
    medicines = load_catalog()

    retriever = PharmoraRetriever()

    ranks = []

    print("=" * 72)
    print("PHARMORA - CANDIDATE RECALL")
    print("=" * 72)

    for case in CASES:
        medicine = resolve(
            medicines=medicines,
            medicine_name=case.medicine_name,
        )

        cis = get_cis(
            medicine
        )

        results = retriever.search(
            question=case.question,
            cis=cis,
            document_type="RCP",
            top_k=30,
        )

        rank = first_expected_rank(
            results=results,
            expected_section=case.expected_section,
        )

        ranks.append(rank)

        print()
        print(case.name)
        print(
            f"Question : {case.question}"
        )
        print(
            f"Section attendue : "
            f"{case.expected_section}"
        )

        if rank is None:
            print(
                "Premier rang : ABSENTE DU TOP 30"
            )
        else:
            print(
                f"Premier rang : {rank}"
            )

        print("Top sections :")

        for index, result in enumerate(
            results[:15],
            start=1,
        ):
            print(
                f"  {index:02d}. "
                f"{result.get('section_number')} - "
                f"{result.get('section_title')} "
                f"| {result.get('dense_score', 0):.4f}"
            )

    total = len(
        CASES
    )

    recall_5 = sum(
        rank is not None and rank <= 5
        for rank in ranks
    )

    recall_10 = sum(
        rank is not None and rank <= 10
        for rank in ranks
    )

    recall_15 = sum(
        rank is not None and rank <= 15
        for rank in ranks
    )

    recall_20 = sum(
        rank is not None and rank <= 20
        for rank in ranks
    )

    recall_30 = sum(
        rank is not None and rank <= 30
        for rank in ranks
    )

    print()
    print("=" * 72)
    print("RECALL")
    print("=" * 72)
    print(
        f"Recall@5  : {recall_5}/{total}"
    )
    print(
        f"Recall@10 : {recall_10}/{total}"
    )
    print(
        f"Recall@15 : {recall_15}/{total}"
    )
    print(
        f"Recall@20 : {recall_20}/{total}"
    )
    print(
        f"Recall@30 : {recall_30}/{total}"
    )


if __name__ == "__main__":
    main()