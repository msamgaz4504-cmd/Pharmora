from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


DATA_DIR = Path("data")
CATALOG_PATH = DATA_DIR / "catalog" / "medicines.json"
DOCUMENTS_DIR = DATA_DIR / "documents"

EXPECTED_MEDICINES = 15
EXPECTED_DOCUMENTS = 30

NOTICE_REQUIRED = {"1", "2", "3", "4", "5", "6"}

RCP_REQUIRED = {
    "1",
    "2",
    "3",
    "4",
    "4.1",
    "4.2",
    "4.3",
    "4.4",
    "4.5",
    "4.6",
    "4.7",
    "4.8",
    "4.9",
    "5",
    "6",
}

CRITICAL_RCP = {
    "1",
    "2",
    "3",
    "4.1",
    "4.2",
    "4.3",
    "4.4",
    "4.5",
    "4.6",
    "4.7",
    "4.8",
    "4.9",
}

NOISE_PATTERNS = [
    r"\bHaut de page\b",
    r"\bRedirection vers le haut de page\b",
    r"\bRetour à l'accueil\b",
    r"\bPlan du site\b",
    r"\bMentions légales\b",
    r"\bMinistère de la Santé\b",
    r"\bRépublique Française\b",
    r"\bScanner un médicament\b",
]

NOTICE_MARKERS = [
    "qu'est-ce que",
    "qu’est-ce que",
    "comment prendre",
    "comment utiliser",
    "comment conserver",
]

RCP_MARKERS = [
    "dénomination du médicament",
    "composition qualitative et quantitative",
    "données cliniques",
    "propriétés pharmacologiques",
    "données pharmaceutiques",
]


def load_json(path: Path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def normalize(text: str) -> str:
    text = text or ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def section_map(document: dict) -> dict[str, dict]:
    return {
        section["section_number"]: section
        for section in document.get("sections", [])
    }


def full_document_text(document: dict) -> str:
    parts = []

    for section in document.get("sections", []):
        parts.append(section.get("title", ""))
        parts.append(section.get("text", ""))

    return "\n".join(parts)


def check_noise(document: dict) -> list[str]:
    text = full_document_text(document)

    found = []

    for pattern in NOISE_PATTERNS:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            found.append(pattern)

    return found


def check_duplicate_sections(
    document: dict,
) -> list[str]:
    numbers = [
        section.get("section_number")
        for section in document.get("sections", [])
    ]

    counts = Counter(numbers)

    return sorted(
        number
        for number, count in counts.items()
        if count > 1
    )


def validate_document(
    document: dict,
    catalogue_by_cis: dict,
) -> list[str]:
    errors = []

    cis = document.get("cis")
    medicine_name = document.get("medicine_name")
    document_type = document.get("document_type")

    if cis not in catalogue_by_cis:
        errors.append(
            f"CIS absent du catalogue: {cis}"
        )
        return errors

    expected_name = catalogue_by_cis[cis]["name"]

    if medicine_name != expected_name:
        errors.append(
            "Nom médicament différent du catalogue"
        )

    if document_type not in {"NOTICE", "RCP"}:
        errors.append(
            f"Type documentaire invalide: {document_type}"
        )
        return errors

    sections = document.get("sections", [])

    if not sections:
        errors.append("Aucune section")
        return errors

    duplicates = check_duplicate_sections(document)

    if duplicates:
        errors.append(
            f"Sections dupliquées: {duplicates}"
        )

    by_number = section_map(document)
    numbers = set(by_number)

    if document_type == "NOTICE":
        missing = NOTICE_REQUIRED - numbers

        if missing:
            errors.append(
                f"Sections Notice manquantes: {sorted(missing)}"
            )

        for number in NOTICE_REQUIRED:
            section = by_number.get(number)

            if section and len(
                section.get("text", "").strip()
            ) < 20:
                errors.append(
                    f"Notice section {number} trop courte"
                )

    if document_type == "RCP":
        missing = RCP_REQUIRED - numbers

        if missing:
            errors.append(
                f"Sections RCP manquantes: {sorted(missing)}"
            )

        for number in CRITICAL_RCP:
            section = by_number.get(number)

            if section and len(
                section.get("text", "").strip()
            ) < 3:
                errors.append(
                    f"RCP section {number} vide"
                )

    noise = check_noise(document)

    if noise:
        errors.append(
            f"Bruit web détecté: {noise}"
        )

    source_url = document.get("source_url", "")

    if "base-donnees-publique.medicaments.gouv.fr" not in source_url:
        errors.append(
            "URL source BDPM invalide"
        )

    if not document.get("content_hash"):
        errors.append(
            "content_hash absent"
        )

    if document.get("character_count", 0) < 500:
        errors.append(
            "Document anormalement court"
        )

    text = normalize(
        full_document_text(document)
    )

    if document_type == "NOTICE":
        marker_count = sum(
            marker in text
            for marker in NOTICE_MARKERS
        )

        if marker_count < 2:
            errors.append(
                "Contenu Notice peu cohérent"
            )

    return errors


def validate_pairs(
    documents_by_cis: dict,
) -> list[str]:
    errors = []

    for cis, documents in documents_by_cis.items():
        types = [
            document.get("document_type")
            for document in documents
        ]

        if sorted(types) != ["NOTICE", "RCP"]:
            errors.append(
                f"{cis}: paire NOTICE/RCP incorrecte: {types}"
            )
            continue

        notice = next(
            document
            for document in documents
            if document["document_type"] == "NOTICE"
        )

        rcp = next(
            document
            for document in documents
            if document["document_type"] == "RCP"
        )

        if (
            notice.get("content_hash")
            == rcp.get("content_hash")
        ):
            errors.append(
                f"{cis}: Notice et RCP identiques"
            )

    return errors


def print_representative_check(
    documents_by_cis: dict,
    catalogue_by_cis: dict,
) -> None:
    targets = [
        "DOLIPRANE",
        "AMOXICILLINE",
        "OMEPRAZOLE",
    ]

    print(
        "\n=== REPRESENTATIVE CONTENT ==="
    )

    for target in targets:
        medicine = next(
            (
                item
                for item in catalogue_by_cis.values()
                if item["name"].upper().startswith(target)
            ),
            None,
        )

        if not medicine:
            print(f"{target}: NOT FOUND")
            continue

        cis = medicine["cis"]

        documents = documents_by_cis.get(
            cis,
            [],
        )

        rcp = next(
            (
                document
                for document in documents
                if document["document_type"] == "RCP"
            ),
            None,
        )

        notice = next(
            (
                document
                for document in documents
                if document["document_type"] == "NOTICE"
            ),
            None,
        )

        print(
            f"\n{medicine['name']} ({cis})"
        )

        if rcp:
            rcp_sections = section_map(rcp)

            for number in [
                "4.1",
                "4.2",
                "4.3",
                "4.8",
            ]:
                section = rcp_sections.get(number)

                if section:
                    preview = normalize(
                        section["text"]
                    )[:120]

                    print(
                        f"  RCP {number}: PASS"
                    )
                    print(
                        f"    {preview}..."
                    )
                else:
                    print(
                        f"  RCP {number}: FAIL"
                    )

        if notice:
            notice_sections = section_map(
                notice
            )

            for number in ["1", "3"]:
                section = notice_sections.get(
                    number
                )

                if section:
                    preview = normalize(
                        section["text"]
                    )[:120]

                    print(
                        f"  NOTICE {number}: PASS"
                    )
                    print(
                        f"    {preview}..."
                    )
                else:
                    print(
                        f"  NOTICE {number}: FAIL"
                    )


def main() -> None:
    print(
        "\n=== PHARMORA CORPUS QA ===\n"
    )

    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Catalogue introuvable: {CATALOG_PATH}"
        )

    catalogue = load_json(
        CATALOG_PATH
    )

    catalogue_by_cis = {
        medicine["cis"]: medicine
        for medicine in catalogue
    }

    paths = sorted(
        DOCUMENTS_DIR.glob("*.json")
    )

    documents = [
        load_json(path)
        for path in paths
    ]

    documents_by_cis = defaultdict(list)

    for document in documents:
        documents_by_cis[
            document.get("cis")
        ].append(document)

    errors = []

    if len(catalogue) != EXPECTED_MEDICINES:
        errors.append(
            "Catalogue: "
            f"{len(catalogue)}/{EXPECTED_MEDICINES}"
        )

    if len(documents) != EXPECTED_DOCUMENTS:
        errors.append(
            "Documents: "
            f"{len(documents)}/{EXPECTED_DOCUMENTS}"
        )

    notice_count = sum(
        document.get("document_type") == "NOTICE"
        for document in documents
    )

    rcp_count = sum(
        document.get("document_type") == "RCP"
        for document in documents
    )

    print(
        f"Medicines       {len(catalogue)}/{EXPECTED_MEDICINES}"
    )
    print(
        f"Documents       {len(documents)}/{EXPECTED_DOCUMENTS}"
    )
    print(
        f"Notice          {notice_count}/15"
    )
    print(
        f"RCP             {rcp_count}/15"
    )

    for document in documents:
        document_errors = validate_document(
            document,
            catalogue_by_cis,
        )

        for error in document_errors:
            errors.append(
                f"{document.get('document_id')}: {error}"
            )

    errors.extend(
        validate_pairs(
            documents_by_cis
        )
    )

    print_representative_check(
        documents_by_cis,
        catalogue_by_cis,
    )

    print(
        "\n=== FINAL QA ==="
    )

    if errors:
        print(
            f"Errors: {len(errors)}"
        )

        for error in errors:
            print(
                f"  ✗ {error}"
            )

        print(
            "\nFINAL STATUS: FAILED"
        )

    else:
        print(
            "CIS / names      PASS"
        )
        print(
            "Document pairs   PASS"
        )
        print(
            "Sections         PASS"
        )
        print(
            "Duplicates       PASS"
        )
        print(
            "Critical content PASS"
        )
        print(
            "Web noise        PASS"
        )
        print(
            "Source URLs      PASS"
        )
        print(
            "\nFINAL STATUS: PASS"
        )


if __name__ == "__main__":
    main()