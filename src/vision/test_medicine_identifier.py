from __future__ import annotations

import sys

from src.vision.medicine_identifier import (
    MedicineImageIdentifier,
)


def main() -> None:
    if len(
        sys.argv
    ) != 2:
        raise RuntimeError(
            "Usage : python -m "
            "src.vision.test_medicine_identifier "
            "<image>"
        )

    identifier = (
        MedicineImageIdentifier()
    )

    result = identifier.identify(
        sys.argv[1]
    )

    print("=" * 72)
    print(
        "PHARMORA - MEDICINE IMAGE IDENTIFICATION"
    )
    print("=" * 72)

    print()
    print(
        "STATUS :",
        result["status"],
    )

    print(
        "QUERY USED :",
        result[
            "query_used"
        ],
    )

    print()
    print("OCR TEXT")
    print("-" * 72)

    print(
        result[
            "ocr"
        ][
            "text"
        ]
    )

    print()
    print("CATALOG RESOLUTION")
    print("-" * 72)

    print(
        result[
            "resolution"
        ]
    )


if __name__ == "__main__":
    main()