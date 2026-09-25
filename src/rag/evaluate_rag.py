from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from groq import RateLimitError

from src.rag.service import PharmoraRAG


CATALOG_PATH = Path("data/catalog/medicines.json")

MAX_RETRIES = 5
BASE_RETRY_DELAY = 3.0
DELAY_BETWEEN_TESTS = 2.0


@dataclass(frozen=True)
class TestCase:
    name: str
    medicine_name: str
    question: str
    expected_status: str
    expected_sections: tuple[str, ...] = ()


TEST_CASES = [
    TestCase(
        name="Doliprane - effets indésirables",
        medicine_name="DOLIPRANE 500 mg, gélule",
        question="Quels sont les effets indésirables de ce médicament ?",
        expected_status="answered",
        expected_sections=("4.8",),
    ),
    TestCase(
        name="Doliprane - paraphrase effets indésirables",
        medicine_name="DOLIPRANE 500 mg, gélule",
        question="Quels problèmes ou réactions gênantes peuvent apparaître après sa prise ?",
        expected_status="answered",
        expected_sections=("4.8",),
    ),
    TestCase(
        name="Ibuprofène - grossesse",
        medicine_name="IBUPROFENE ARROW 5 %, gel",
        question="Peut-on utiliser ce médicament pendant la grossesse ?",
        expected_status="answered",
        expected_sections=("4.6",),
    ),
    TestCase(
        name="Ibuprofène - paraphrase grossesse",
        medicine_name="IBUPROFENE ARROW 5 %, gel",
        question="Que faut-il savoir si une femme enceinte utilise ce gel ?",
        expected_status="answered",
        expected_sections=("4.6",),
    ),
    TestCase(
        name="Amoxicilline - indications",
        medicine_name="AMOXICILLINE BENTA 500 mg, gélule",
        question="Dans quels cas cet antibiotique est-il utilisé ?",
        expected_status="answered",
        expected_sections=("4.1",),
    ),
    TestCase(
        name="Amoxicilline - paraphrase indications",
        medicine_name="AMOXICILLINE BENTA 500 mg, gélule",
        question="Pourquoi pourrait-on donner ce médicament à un patient ?",
        expected_status="answered",
        expected_sections=("4.1",),
    ),
    TestCase(
        name="Doliprane - prix absent",
        medicine_name="DOLIPRANE 500 mg, gélule",
        question="Quel est aujourd'hui le prix de ce médicament dans une pharmacie de Safi ?",
        expected_status="insufficient_evidence",
    ),
    TestCase(
        name="Ibuprofène - ventes absentes",
        medicine_name="IBUPROFENE ARROW 5 %, gel",
        question="Combien de tubes de ce médicament ont été vendus au Maroc cette année ?",
        expected_status="insufficient_evidence",
    ),
]


def load_catalog() -> list[dict]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Catalogue introuvable : {CATALOG_PATH}"
        )

    data = json.loads(
        CATALOG_PATH.read_text(
            encoding="utf-8"
        )
    )

    if isinstance(data, list):
        medicines = data

    elif isinstance(data, dict):
        if isinstance(
            data.get("medicines"),
            list,
        ):
            medicines = data["medicines"]
        else:
            medicines = [
                value
                for value in data.values()
                if isinstance(value, dict)
            ]

    else:
        raise RuntimeError(
            "Format de medicines.json non reconnu."
        )

    if not medicines:
        raise RuntimeError(
            "Le catalogue ne contient aucun médicament."
        )

    return medicines


def get_medicine_name(
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
        "Nom du médicament introuvable dans le catalogue."
    )


def get_medicine_cis(
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
        "CIS du médicament introuvable dans le catalogue."
    )


def normalize_name(
    value: str,
) -> str:
    return " ".join(
        value.casefold().split()
    )


def resolve_medicine(
    medicines: list[dict],
    medicine_name: str,
) -> dict:
    target = normalize_name(
        medicine_name
    )

    exact_matches = [
        medicine
        for medicine in medicines
        if normalize_name(
            get_medicine_name(
                medicine
            )
        ) == target
    ]

    if len(exact_matches) == 1:
        return exact_matches[0]

    if len(exact_matches) > 1:
        raise LookupError(
            f"Plusieurs entrées exactes trouvées pour "
            f"'{medicine_name}'."
        )

    partial_matches = [
        medicine
        for medicine in medicines
        if target
        in normalize_name(
            get_medicine_name(
                medicine
            )
        )
    ]

    if len(partial_matches) == 1:
        return partial_matches[0]

    if not partial_matches:
        raise LookupError(
            f"Médicament introuvable : {medicine_name}"
        )

    names = [
        get_medicine_name(
            medicine
        )
        for medicine in partial_matches
    ]

    raise LookupError(
        f"Recherche ambiguë pour '{medicine_name}' : "
        + " | ".join(names)
    )


def resolve_test_medicines(
    medicines: list[dict],
) -> dict[str, dict]:
    resolved = {}

    for case in TEST_CASES:
        if case.medicine_name in resolved:
            continue

        resolved[
            case.medicine_name
        ] = resolve_medicine(
            medicines=medicines,
            medicine_name=case.medicine_name,
        )

    return resolved


def ask_with_retry(
    rag: PharmoraRAG,
    question: str,
    cis: str,
    medicine_name: str,
) -> dict:
    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            return rag.ask(
                question=question,
                cis=cis,
                medicine_name=medicine_name,
            )

        except RateLimitError as error:
            if attempt == MAX_RETRIES:
                raise

            delay = (
                BASE_RETRY_DELAY
                * attempt
            )

            print(
                f"Rate limit Groq : attente "
                f"{delay:.0f} s avant retry "
                f"{attempt}/{MAX_RETRIES}"
            )

            time.sleep(delay)

    raise RuntimeError(
        "Le mécanisme de retry a échoué."
    )


def source_sections(
    result: dict,
) -> set[str]:
    return {
        str(
            source.get(
                "section_number",
                "",
            )
        ).strip()
        for source
        in result.get(
            "sources",
            [],
        )
    }


def validate_case(
    case: TestCase,
    result: dict,
) -> tuple[bool, list[str]]:
    errors = []

    status = result.get(
        "status"
    )

    if status != case.expected_status:
        errors.append(
            f"status attendu={case.expected_status}, "
            f"obtenu={status}"
        )

    if case.expected_status == "answered":
        answer = result.get(
            "answer",
            "",
        ).strip()

        sources = result.get(
            "sources",
            [],
        )

        if not answer:
            errors.append(
                "réponse vide"
            )

        if not sources:
            errors.append(
                "aucune source structurée"
            )

        sections = source_sections(
            result
        )

        for expected_section in (
            case.expected_sections
        ):
            if expected_section not in sections:
                errors.append(
                    f"section attendue absente="
                    f"{expected_section}"
                )

        for source in sources:
            reference = source.get(
                "reference"
            )

            if not reference:
                errors.append(
                    "source sans reference"
                )
                continue

            if f"[{reference}]" not in answer:
                errors.append(
                    f"{reference} absente de la réponse"
                )

        if result.get(
            "invalid_citations"
        ):
            errors.append(
                "citations invalides détectées"
            )

    if (
        case.expected_status
        == "insufficient_evidence"
    ):
        if result.get(
            "sources"
        ):
            errors.append(
                "sources retournées malgré "
                "insufficient_evidence"
            )

        if result.get(
            "invalid_citations"
        ):
            errors.append(
                "citations invalides détectées"
            )

    return (
        len(errors) == 0,
        errors,
    )


def main():
    medicines = load_catalog()

    resolved = resolve_test_medicines(
        medicines
    )

    print("=" * 72)
    print("PHARMORA - MEDICAMENTS DE TEST")
    print("=" * 72)

    for name, medicine in resolved.items():
        print(
            f"{name}"
            f" -> CIS {get_medicine_cis(medicine)}"
        )

    rag = PharmoraRAG()

    passed = 0
    failed = 0
    runtime_errors = 0

    print()
    print("=" * 72)
    print("PHARMORA - EVALUATION RAG")
    print("=" * 72)

    for index, case in enumerate(
        TEST_CASES,
        start=1,
    ):
        medicine = resolved[
            case.medicine_name
        ]

        cis = get_medicine_cis(
            medicine
        )

        canonical_name = (
            get_medicine_name(
                medicine
            )
        )

        print()
        print("-" * 72)
        print(
            f"TEST {index}/"
            f"{len(TEST_CASES)}"
        )
        print(case.name)
        print(
            f"Médicament : {canonical_name}"
        )
        print(
            f"CIS : {cis}"
        )
        print(
            f"Question : {case.question}"
        )

        try:
            result = ask_with_retry(
                rag=rag,
                question=case.question,
                cis=cis,
                medicine_name=canonical_name,
            )

            success, errors = (
                validate_case(
                    case=case,
                    result=result,
                )
            )

            print(
                f"Status attendu : "
                f"{case.expected_status}"
            )
            print(
                f"Status obtenu  : "
                f"{result.get('status')}"
            )

            sections = source_sections(
                result
            )

            if sections:
                print(
                    "Sections citées : "
                    + ", ".join(
                        sorted(sections)
                    )
                )

            reason = result.get(
                "evidence_reason"
            )

            if reason:
                print(
                    f"Evidence selector : "
                    f"{reason}"
                )

            if success:
                passed += 1
                print(
                    "Résultat : PASS"
                )

            else:
                failed += 1
                print(
                    "Résultat : FAIL"
                )

                for error in errors:
                    print(
                        f"  - {error}"
                    )

        except Exception as error:
            runtime_errors += 1

            print(
                "Résultat : ERROR"
            )
            print(
                f"{type(error).__name__}: "
                f"{error}"
            )

        if index < len(TEST_CASES):
            time.sleep(
                DELAY_BETWEEN_TESTS
            )

    total = len(
        TEST_CASES
    )

    print()
    print("=" * 72)
    print("RESULTATS")
    print("=" * 72)

    print(
        f"PASS  : {passed}/{total}"
    )
    print(
        f"FAIL  : {failed}/{total}"
    )
    print(
        f"ERROR : {runtime_errors}/{total}"
    )

    if (
        failed == 0
        and runtime_errors == 0
    ):
        print(
            "STATUS FINAL : PASS"
        )
    else:
        print(
            "STATUS FINAL : REVIEW REQUIRED"
        )


if __name__ == "__main__":
    main()