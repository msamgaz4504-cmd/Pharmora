from __future__ import annotations

from src.vision.medicine_identifier import (
    MedicineImageIdentifier,
)


class FakeOCR:
    def __init__(
        self,
        lines: list[str],
    ):
        self.lines = lines

    def extract(
        self,
        image_path,
    ) -> dict:
        return {
            "text": "\n".join(
                self.lines
            ),
            "lines": list(
                self.lines
            ),
            "scores": [
                0.99
                for _ in self.lines
            ],
            "boxes": [
                None
                for _ in self.lines
            ],
            "average_confidence": 0.99,
        }


def get_cis(
    result: dict,
) -> str | None:
    resolution = result.get(
        "resolution"
    )

    if not isinstance(
        resolution,
        dict,
    ):
        return None

    medicine = resolution.get(
        "medicine"
    )

    if not isinstance(
        medicine,
        dict,
    ):
        return None

    return str(
        medicine.get(
            "cis",
            "",
        )
    ).strip() or None


def run_case(
    name: str,
    lines: list[str],
    expected_status: str,
    expected_cis: str | None = None,
) -> bool:
    identifier = (
        MedicineImageIdentifier(
            ocr=FakeOCR(
                lines
            )
        )
    )

    result = identifier.identify(
        "fake-image.jpg"
    )

    status = result[
        "status"
    ]

    cis = get_cis(
        result
    )

    passed = (
        status
        == expected_status
    )

    if expected_cis is not None:
        passed = (
            passed
            and cis
            == expected_cis
        )

    print(
        (
            "PASS"
            if passed
            else "FAIL"
        ),
        "-",
        name,
    )

    print(
        "       Status :",
        status,
    )

    print(
        "       CIS :",
        cis,
    )

    print(
        "       Query :",
        result.get(
            "query_used"
        ),
    )

    return passed


def main() -> None:
    print("=" * 72)
    print(
        "PHARMORA - IMAGE IDENTIFICATION EVALUATION"
    )
    print("=" * 72)

    cases = [
        {
            "name": "Doliprane exact",
            "lines": [
                "Doliprane",
                "500",
                "mg",
                "comprimés",
                "PARACÉTAMOL",
            ],
            "expected_status": "resolved",
            "expected_cis": "63368332",
        },
        {
            "name": "Amoxicilline exacte",
            "lines": [
                "Benta",
                "500",
                "mg",
                "gélule",
                "Amoxicilline",
                "Voie orale",
            ],
            "expected_status": "resolved",
            "expected_cis": "67459306",
        },
        {
            "name": "Doliprane sans forme",
            "lines": [
                "Doliprane",
                "500",
                "mg",
            ],
            "expected_status": "ambiguous",
            "expected_cis": None,
        },
        {
            "name": "Médicament inconnu",
            "lines": [
                "MEDICAMENT INCONNU",
                "999",
                "mg",
            ],
            "expected_status": "not_found",
            "expected_cis": None,
        },
        {
            "name": "OCR avec bruit Amoxicilline",
            "lines": [
                "Benta",
                "500",
                "mg",
                "gélule",
                "Amoxicilline",
                "Amoxicilliine",
                "12 gélules",
            ],
            "expected_status": "resolved",
            "expected_cis": "67459306",
        },
    ]

    passed = 0

    for case in cases:
        print()

        if run_case(
            name=case[
                "name"
            ],
            lines=case[
                "lines"
            ],
            expected_status=case[
                "expected_status"
            ],
            expected_cis=case[
                "expected_cis"
            ],
        ):
            passed += 1

    print()
    print("=" * 72)
    print("RESULTATS")
    print("=" * 72)

    print(
        f"PASS : {passed}/{len(cases)}"
    )

    if passed == len(
        cases
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