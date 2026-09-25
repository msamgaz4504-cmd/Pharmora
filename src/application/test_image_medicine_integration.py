from __future__ import annotations

import sys

from src.application.image_medicine_service import (
    ImageMedicineService,
)


def main() -> None:
    if len(
        sys.argv
    ) != 2:
        raise RuntimeError(
            "Usage : python -m "
            "src.application.test_image_medicine_integration "
            "<image>"
        )

    service = (
        ImageMedicineService()
    )

    result = (
        service.identify_and_select(
            sys.argv[1]
        )
    )

    print("=" * 72)
    print(
        "PHARMORA - IMAGE MEDICINE E2E"
    )
    print("=" * 72)

    print()
    print(
        "STATUS :",
        result["status"],
    )

    identification = (
        result[
            "identification"
        ]
    )

    print(
        "QUERY USED :",
        identification.get(
            "query_used"
        ),
    )

    if result[
        "status"
    ] != "resolved":
        print()
        print(
            "IDENTIFICATION :",
            result[
                "status"
            ],
        )
        return

    profile = result[
        "profile"
    ]

    if not isinstance(
        profile,
        dict,
    ):
        raise AssertionError(
            "La fiche médicament "
            "est absente."
        )

    print()
    print("PROFILE")
    print("-" * 72)

    print(
        "CIS :",
        profile.get(
            "cis"
        ),
    )

    print(
        "NAME :",
        profile.get(
            "name"
        ),
    )

    print(
        "STRENGTH :",
        profile.get(
            "strength"
        ),
    )

    print(
        "FORM :",
        profile.get(
            "pharmaceutical_form"
        ),
    )

    print(
        "ROUTES :",
        profile.get(
            "administration_routes"
        ),
    )

    if not profile.get(
        "cis"
    ):
        raise AssertionError(
            "CIS absent."
        )

    if not profile.get(
        "name"
    ):
        raise AssertionError(
            "Nom absent."
        )

    print()
    print(
        "STATUS FINAL : PASS"
    )


if __name__ == "__main__":
    main()