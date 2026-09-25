from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr"
MOBILE_URL = "https://m.base-donnees-publique.medicaments.gouv.fr"

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
CATALOG_DIR = DATA_DIR / "catalog"
DOCUMENTS_DIR = DATA_DIR / "documents"

for directory in (RAW_DIR, CATALOG_DIR, DOCUMENTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


DOWNLOADS = {
    "specialties": f"{BASE_URL}/download/file/CIS_bdpm.txt",
    "compositions": f"{BASE_URL}/download/file/CIS_COMPO_bdpm.txt",
    "presentations": f"{BASE_URL}/download/file/CIS_CIP_bdpm.txt",
}


TARGET_NAMES = [
    "DOLIPRANE",
    "AMOXICILLINE",
    "IBUPROFENE",
    "CETIRIZINE",
    "OMEPRAZOLE",
]


SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/140 Safari/537.36"
        )
    }
)


def normalize(value: str) -> str:
    value = value or ""
    value = value.replace("\xa0", " ")
    value = value.replace("\u202f", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def fold_text(value: str) -> str:
    value = normalize(value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )
    value = value.replace("’", "'")
    value = value.replace("ʼ", "'")
    value = value.replace("–", "-")
    value = value.replace("—", "-")
    return value.upper()


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("\u202f", " ")

    footer_patterns = [
        r"(?mi)^Haut de page\s*$",
        r"(?mi)^Plan du site\s*$",
        r"(?mi)^Mentions légales\s*$",
    ]

    footer_positions = []

    for pattern in footer_patterns:
        match = re.search(pattern, text)

        if match:
            footer_positions.append(match.start())

    if footer_positions:
        text = text[:min(footer_positions)]

    text = re.sub(
        r"\s*Redirection vers le haut de page\s*",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def save_json(data, path: Path) -> None:
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def download_file(url: str, destination: Path) -> None:
    print(f"Downloading {destination.name}...")

    response = SESSION.get(
        url,
        timeout=60,
    )

    response.raise_for_status()
    destination.write_bytes(response.content)


def ensure_raw_files() -> dict[str, Path]:
    paths = {}

    for key, url in DOWNLOADS.items():
        path = RAW_DIR / Path(url).name

        if not path.exists():
            download_file(url, path)

        paths[key] = path

    return paths


def read_tsv(path: Path) -> list[list[str]]:
    for encoding in (
        "utf-8-sig",
        "cp1252",
        "latin-1",
    ):
        try:
            with path.open(
                "r",
                encoding=encoding,
                newline="",
            ) as file:
                return list(
                    csv.reader(
                        file,
                        delimiter="\t",
                    )
                )

        except UnicodeDecodeError:
            continue

    raise RuntimeError(
        f"Impossible de lire {path}"
    )


def load_specialties(
    path: Path,
) -> dict[str, dict]:
    medicines = {}

    for row in read_tsv(path):
        if len(row) < 12:
            continue

        cis = normalize(row[0])

        if not cis:
            continue

        medicines[cis] = {
            "cis": cis,
            "name": normalize(row[1]),
            "pharmaceutical_form": normalize(row[2]),
            "administration_routes": [
                normalize(route)
                for route in row[3].split(";")
                if normalize(route)
            ],
            "authorization_status": normalize(row[4]),
            "authorization_type": normalize(row[5]),
            "commercialization_status": normalize(row[6]),
            "authorization_date": normalize(row[7]),
            "bdpm_status": normalize(row[8]),
            "authorization_number_eu": normalize(row[9]),
            "holder": normalize(row[10]),
            "enhanced_monitoring": normalize(row[11]),
            "active_substances": [],
            "presentations": [],
        }

    return medicines


def attach_compositions(
    medicines: dict[str, dict],
    path: Path,
) -> None:
    substances = defaultdict(list)

    for row in read_tsv(path):
        if len(row) < 7:
            continue

        cis = normalize(row[0])

        if not cis:
            continue

        substances[cis].append(
            {
                "pharmaceutical_element": normalize(row[1]),
                "substance_code": normalize(row[2]),
                "substance_name": normalize(row[3]),
                "strength": normalize(row[4]),
                "strength_reference": normalize(row[5]),
                "component_type": normalize(row[6]),
            }
        )

    for cis, components in substances.items():
        if cis in medicines:
            medicines[cis]["active_substances"] = components


def attach_presentations(
    medicines: dict[str, dict],
    path: Path,
) -> None:
    presentations = defaultdict(list)

    for row in read_tsv(path):
        if len(row) < 7:
            continue

        cis = normalize(row[0])

        if not cis:
            continue

        presentations[cis].append(
            {
                "cip7": normalize(row[1]),
                "label": normalize(row[2]),
                "administrative_status": normalize(row[3]),
                "commercialization_status": normalize(row[4]),
                "commercialization_date": normalize(row[5]),
                "cip13": normalize(row[6]),
            }
        )

    for cis, values in presentations.items():
        if cis in medicines:
            medicines[cis]["presentations"] = values


def select_v1_medicines(
    medicines: dict[str, dict],
    max_per_name: int = 3,
) -> list[dict]:
    selected = []

    for target in TARGET_NAMES:
        matches = []

        for medicine in medicines.values():
            name = medicine["name"].upper()

            status = (
                medicine["commercialization_status"]
                .strip()
                .lower()
            )

            if not name.startswith(target.upper()):
                continue

            if status != "commercialisée":
                continue

            matches.append(medicine)

        matches.sort(
            key=lambda medicine: (
                len(medicine["name"]),
                medicine["name"],
            )
        )

        selected.extend(
            matches[:max_per_name]
        )

    unique = {}

    for medicine in selected:
        unique[medicine["cis"]] = medicine

    return list(unique.values())


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        "\n",
        strip=True,
    )

    return clean_text(text)


def fetch_url(url: str) -> str:
    response = SESSION.get(
        url,
        timeout=30,
    )

    response.raise_for_status()

    return html_to_text(
        response.text
    )


def fetch_mobile_document(
    cis: str,
    document_type: str,
) -> tuple[str, str] | None:
    if document_type == "RCP":
        url = f"{MOBILE_URL}/rcp-{cis}-0"
    else:
        url = f"{MOBILE_URL}/notice-{cis}-0"

    try:
        text = fetch_url(url)
    except requests.RequestException:
        return None

    folded = fold_text(text)

    if document_type == "RCP":
        valid = (
            "DENOMINATION DU MEDICAMENT"
            in folded
            and
            "DONNEES CLINIQUES"
            in folded
            and len(text) > 1500
        )
    else:
        valid = (
            "NOTICE"
            in folded
            and len(text) > 1000
        )

    if not valid:
        return None

    return text, url


def fetch_desktop_page(
    cis: str,
) -> tuple[str, str]:
    url = (
        f"{BASE_URL}/medicament/"
        f"{cis}/extrait"
    )

    text = fetch_url(url)

    if len(text) < 1500:
        raise ValueError(
            "Page BDPM desktop anormalement courte"
        )

    return text, url


RCP_SECTION_PATTERN = re.compile(
    r"(?mi)^"
    r"(?P<number>"
    r"(?:[1-9]|1[0-2])"
    r"(?:\.\d+)?"
    r")"
    r"\.\s+"
    r"(?P<title>[^\n]+)"
    r"$"
)


NOTICE_SECTION_PATTERN = re.compile(
    r"(?mi)^"
    r"(?P<number>[1-6])"
    r"\.\s+"
    r"(?P<title>[^\n]+)"
    r"$"
)


def is_real_rcp_section(
    number: str,
    title: str,
) -> bool:
    title = fold_text(title)

    rules = {
        "1": [
            "DENOMINATION DU MEDICAMENT",
        ],
        "2": [
            "COMPOSITION QUALITATIVE ET QUANTITATIVE",
        ],
        "3": [
            "FORME PHARMACEUTIQUE",
        ],
        "4": [
            "DONNEES CLINIQUES",
        ],
        "4.1": [
            "INDICATIONS THERAPEUTIQUES",
        ],
        "4.2": [
            "POSOLOGIE ET MODE D'ADMINISTRATION",
        ],
        "4.3": [
            "CONTRE-INDICATIONS",
            "CONTRE INDICATIONS",
        ],
        "4.4": [
            "MISES EN GARDE",
        ],
        "4.5": [
            "INTERACTIONS AVEC D'AUTRES MEDICAMENTS",
        ],
        "4.6": [
            "FERTILITE",
            "GROSSESSE",
        ],
        "4.7": [
            "EFFETS SUR L'APTITUDE",
        ],
        "4.8": [
            "EFFETS INDESIRABLES",
        ],
        "4.9": [
            "SURDOSAGE",
        ],
        "5": [
            "PROPRIETES PHARMACOLOGIQUES",
        ],
        "5.1": [
            "PROPRIETES PHARMACODYNAMIQUES",
        ],
        "5.2": [
            "PROPRIETES PHARMACOCINETIQUES",
        ],
        "5.3": [
            "DONNEES DE SECURITE PRECLINIQUE",
        ],
        "6": [
            "DONNEES PHARMACEUTIQUES",
        ],
        "6.1": [
            "LISTE DES EXCIPIENTS",
        ],
        "6.2": [
            "INCOMPATIBILITES",
        ],
        "6.3": [
            "DUREE DE CONSERVATION",
        ],
        "6.4": [
            "PRECAUTIONS PARTICULIERES DE CONSERVATION",
        ],
        "6.5": [
            "NATURE ET CONTENU DE L'EMBALLAGE",
        ],
        "6.6": [
            "PRECAUTIONS PARTICULIERES D'ELIMINATION",
        ],
        "7": [
            "TITULAIRE DE L'AUTORISATION",
        ],
        "8": [
            "NUMERO(S) D'AUTORISATION",
            "NUMEROS D'AUTORISATION",
            "NUMERO D'AUTORISATION",
        ],
        "9": [
            "DATE DE PREMIERE AUTORISATION",
        ],
        "10": [
            "DATE DE MISE A JOUR",
        ],
        "11": [
            "DOSIMETRIE",
        ],
        "12": [
            "INSTRUCTIONS POUR LA PREPARATION",
        ],
    }

    expected = rules.get(number)

    if not expected:
        return False

    return any(
        phrase in title
        for phrase in expected
    )


def is_real_notice_section(
    number: str,
    title: str,
) -> bool:
    title = fold_text(title)

    rules = {
        "1": [
            "QU'EST-CE QUE",
            "QU EST-CE QUE",
            "QU'EST CE QUE",
        ],
        "2": [
            "QUELLES SONT LES INFORMATIONS",
        ],
        "3": [
            "COMMENT PRENDRE",
            "COMMENT UTILISER",
        ],
        "4": [
            "QUELS SONT LES EFFETS",
            "QUELLES SONT LES EFFETS",
        ],
        "5": [
            "COMMENT CONSERVER",
        ],
        "6": [
            "CONTENU DE L'EMBALLAGE",
            "INFORMATIONS SUPPLEMENTAIRES",
        ],
    }

    expected = rules.get(number)

    if not expected:
        return False

    return any(
        phrase in title
        for phrase in expected
    )


def get_valid_matches(
    text: str,
    document_type: str,
) -> list[re.Match]:
    pattern = (
        RCP_SECTION_PATTERN
        if document_type == "RCP"
        else NOTICE_SECTION_PATTERN
    )

    matches = []

    for match in pattern.finditer(text):
        number = match.group("number")
        title = match.group("title")

        if document_type == "RCP":
            valid = is_real_rcp_section(
                number,
                title,
            )
        else:
            valid = is_real_notice_section(
                number,
                title,
            )

        if valid:
            matches.append(match)

    return matches


def choose_real_start(
    text: str,
    document_type: str,
) -> int:
    matches = get_valid_matches(
        text,
        document_type,
    )

    section_ones = [
        match
        for match in matches
        if match.group("number") == "1"
    ]

    if not section_ones:
        raise ValueError(
            f"Début réel {document_type} introuvable"
        )

    candidates = []

    for section_one in section_ones:
        following = [
            match
            for match in matches
            if match.start() >= section_one.start()
        ]

        numbers = [
            match.group("number")
            for match in following
        ]

        if document_type == "RCP":
            required = {
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
        else:
            required = {
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
            }

        score = len(
            required.intersection(numbers)
        )

        candidates.append(
            (
                score,
                section_one.start(),
            )
        )

    best_score = max(
        candidate[0]
        for candidate in candidates
    )

    best_candidates = [
        candidate
        for candidate in candidates
        if candidate[0] == best_score
    ]

    return max(
        best_candidates,
        key=lambda candidate: candidate[1],
    )[1]


def isolate_desktop_document(
    full_text: str,
    document_type: str,
) -> str:
    if document_type == "RCP":
        notice_markers = [
            match.start()
            for match in re.finditer(
                r"(?mi)^Sommaire de la notice\s*$",
                full_text,
            )
        ]

        if notice_markers:
            region = full_text[
                :notice_markers[-1]
            ]
        else:
            region = full_text

    else:
        notice_patient_matches = list(
            re.finditer(
                r"(?mi)^Notice patient\s*$",
                full_text,
            )
        )

        if notice_patient_matches:
            region = full_text[
                notice_patient_matches[-1].end():
            ]
        else:
            region = full_text

    start = choose_real_start(
        region,
        document_type,
    )

    return clean_text(
        region[start:]
    )


def isolate_mobile_document(
    text: str,
    document_type: str,
) -> str:
    start = choose_real_start(
        text,
        document_type,
    )

    document = text[start:]

    footer_patterns = [
        r"(?mi)^Dernière mise à jour le \d{2}/\d{2}/\d{4}\s*$",
        r"(?mi)^Informations\s*$",
        r"(?mi)^Scanner un médicament\s*$",
    ]

    end_positions = []

    for pattern in footer_patterns:
        match = re.search(
            pattern,
            document,
        )

        if match:
            end_positions.append(
                match.start()
            )

    if end_positions:
        document = document[
            :min(end_positions)
        ]

    return clean_text(document)


def obtain_document_text(
    cis: str,
    document_type: str,
) -> tuple[str, str, str]:
    mobile = fetch_mobile_document(
        cis,
        document_type,
    )

    if mobile is not None:
        mobile_text, mobile_url = mobile

        try:
            document = isolate_mobile_document(
                mobile_text,
                document_type,
            )

            return (
                document,
                mobile_url,
                "mobile_document",
            )

        except ValueError:
            pass

    desktop_text, desktop_url = (
        fetch_desktop_page(cis)
    )

    document = isolate_desktop_document(
        desktop_text,
        document_type,
    )

    return (
        document,
        desktop_url,
        "desktop_extrait_fallback",
    )


def split_sections(
    document_text: str,
    document_type: str,
) -> list[dict]:
    matches = get_valid_matches(
        document_text,
        document_type,
    )

    if not matches:
        raise ValueError(
            f"Aucune section réelle {document_type}"
        )

    sections = []

    for index, match in enumerate(matches):
        number = match.group("number")
        title = normalize(
            match.group("title")
        )

        content_start = match.end()

        content_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(document_text)
        )

        content = clean_text(
            document_text[
                content_start:
                content_end
            ]
        )

        sections.append(
            {
                "section_index": len(sections),
                "section_number": number,
                "title": title,
                "text": content,
            }
        )

    return sections


def deduplicate_sections(
    sections: list[dict],
) -> list[dict]:
    grouped = defaultdict(list)

    for section in sections:
        grouped[
            section["section_number"]
        ].append(section)

    selected = []

    for candidates in grouped.values():
        best = max(
            candidates,
            key=lambda section: len(
                section["text"].strip()
            ),
        )

        selected.append(best)

    selected.sort(
        key=lambda section: (
            tuple(
                int(part)
                for part in section[
                    "section_number"
                ].split(".")
            )
        )
    )

    for index, section in enumerate(
        selected
    ):
        section["section_index"] = index

    return selected


def validate_notice(
    sections: list[dict],
) -> None:
    by_number = {
        section["section_number"]: section
        for section in sections
    }

    required = {
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    }

    missing = (
        required
        - set(by_number)
    )

    if missing:
        raise ValueError(
            "Notice incomplète. "
            f"Sections manquantes: {sorted(missing)}"
        )

    for number in required:
        if len(
            by_number[number]["text"].strip()
        ) < 20:
            raise ValueError(
                "Section Notice vide: "
                f"{number}"
            )


def validate_rcp(
    sections: list[dict],
) -> None:
    by_number = {
        section["section_number"]: section
        for section in sections
    }

    required = {
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

    missing = (
        required
        - set(by_number)
    )

    if missing:
        raise ValueError(
            "RCP incomplet. "
            f"Sections manquantes: {sorted(missing)}"
        )

    content_required = {
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

    for number in content_required:
        if len(
            by_number[number]["text"].strip()
        ) < 3:
            raise ValueError(
                "Section RCP sans contenu réel: "
                f"{number}"
            )


def build_document(
    cis: str,
    medicine_name: str,
    document_type: str,
) -> dict:
    document_text, source_url, extraction_method = (
        obtain_document_text(
            cis,
            document_type,
        )
    )

    sections = split_sections(
        document_text,
        document_type,
    )

    sections = deduplicate_sections(
        sections
    )

    if document_type == "RCP":
        validate_rcp(sections)
    else:
        validate_notice(sections)

    canonical_text = "\n\n".join(
        (
            f"{section['section_number']}. "
            f"{section['title']}\n"
            f"{section['text']}"
        ).strip()
        for section in sections
    )

    content_hash = hashlib.sha256(
        canonical_text.encode(
            "utf-8"
        )
    ).hexdigest()

    empty_sections = [
        section["section_number"]
        for section in sections
        if not section["text"].strip()
    ]

    return {
        "document_id": (
            f"{cis}_{document_type.lower()}"
        ),
        "cis": cis,
        "medicine_name": medicine_name,
        "document_type": document_type,
        "source": (
            "Base de données publique "
            "des médicaments"
        ),
        "source_url": source_url,
        "extraction_method": extraction_method,
        "retrieved_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "content_hash": content_hash,
        "character_count": len(
            canonical_text
        ),
        "section_count": len(
            sections
        ),
        "non_empty_section_count": sum(
            1
            for section in sections
            if section["text"].strip()
        ),
        "empty_sections": empty_sections,
        "sections": sections,
    }


def validate_pair(
    notice: dict,
    rcp: dict,
) -> None:
    if notice["cis"] != rcp["cis"]:
        raise ValueError(
            "CIS Notice/RCP incohérent"
        )

    if (
        notice["content_hash"]
        == rcp["content_hash"]
    ):
        raise ValueError(
            "Notice et RCP identiques"
        )


def ingest_medicine(
    medicine: dict,
) -> tuple[list[dict], list[dict]]:
    cis = medicine["cis"]

    try:
        rcp = build_document(
            cis,
            medicine["name"],
            "RCP",
        )

        notice = build_document(
            cis,
            medicine["name"],
            "NOTICE",
        )

        validate_pair(
            notice,
            rcp,
        )

        documents = [
            notice,
            rcp,
        ]

        for document in documents:
            path = (
                DOCUMENTS_DIR
                / (
                    f"{cis}_"
                    f"{document['document_type'].lower()}"
                    ".json"
                )
            )

            save_json(
                document,
                path,
            )

        return documents, []

    except Exception as exc:
        return (
            [],
            [
                {
                    "cis": cis,
                    "medicine": medicine["name"],
                    "error": str(exc),
                }
            ],
        )


def main() -> None:
    print(
        "\n=== PHARMORA BDPM INGESTION ===\n"
    )

    raw = ensure_raw_files()

    print(
        "Building medicine catalogue..."
    )

    medicines = load_specialties(
        raw["specialties"]
    )

    attach_compositions(
        medicines,
        raw["compositions"],
    )

    attach_presentations(
        medicines,
        raw["presentations"],
    )

    selected = select_v1_medicines(
        medicines
    )

    if len(selected) != 15:
        raise RuntimeError(
            "Le corpus V1 doit contenir "
            f"15 médicaments, obtenu: "
            f"{len(selected)}"
        )

    save_json(
        selected,
        CATALOG_DIR / "medicines.json",
    )

    print(
        f"{len(selected)} medicines selected."
    )

    for path in DOCUMENTS_DIR.glob(
        "*.json"
    ):
        path.unlink()

    report = {
        "requested_medicines": 15,
        "expected_documents": 30,
        "successful_medicines": 0,
        "successful_documents": 0,
        "failed_medicines": [],
        "documents": [],
    }

    for index, medicine in enumerate(
        selected,
        start=1,
    ):
        print(
            f"[{index}/15] "
            f"{medicine['name']} "
            f"({medicine['cis']})"
        )

        documents, failures = (
            ingest_medicine(
                medicine
            )
        )

        if failures:
            report[
                "failed_medicines"
            ].extend(
                failures
            )

            print(
                "   ✗ "
                f"{failures[0]['error']}"
            )

        else:
            report[
                "successful_medicines"
            ] += 1

            report[
                "successful_documents"
            ] += 2

            for document in documents:
                report[
                    "documents"
                ].append(
                    {
                        "document_id":
                            document[
                                "document_id"
                            ],
                        "type":
                            document[
                                "document_type"
                            ],
                        "sections":
                            document[
                                "section_count"
                            ],
                        "non_empty_sections":
                            document[
                                "non_empty_section_count"
                            ],
                        "empty_sections":
                            document[
                                "empty_sections"
                            ],
                        "characters":
                            document[
                                "character_count"
                            ],
                        "extraction_method":
                            document[
                                "extraction_method"
                            ],
                        "source_url":
                            document[
                                "source_url"
                            ],
                    }
                )

                print(
                    "   ✓ "
                    f"{document['document_type']} "
                    f"— {document['section_count']} sections "
                    f"— {document['non_empty_section_count']} non-empty "
                    f"— {document['character_count']} chars "
                    f"— {document['extraction_method']}"
                )

        time.sleep(0.2)

    report[
        "finished_at"
    ] = datetime.now(
        timezone.utc
    ).isoformat()

    report["status"] = (
        "SUCCESS"
        if (
            report[
                "successful_medicines"
            ] == 15
            and
            report[
                "successful_documents"
            ] == 30
            and not report[
                "failed_medicines"
            ]
        )
        else "FAILED"
    )

    save_json(
        report,
        DATA_DIR
        / "ingestion_report.json",
    )

    print(
        "\n=== INGESTION VALIDATION ==="
    )

    print(
        "Medicines: "
        f"{report['successful_medicines']}/15"
    )

    print(
        "Documents: "
        f"{report['successful_documents']}/30"
    )

    print(
        "Failures: "
        f"{len(report['failed_medicines'])}"
    )

    print(
        "Status: "
        f"{report['status']}"
    )


if __name__ == "__main__":
    main()