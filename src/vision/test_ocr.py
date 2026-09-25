from __future__ import annotations

import sys

from src.vision.ocr import (
    MedicineOCR,
)


def main() -> None:
    if len(
        sys.argv
    ) != 2:
        raise RuntimeError(
            "Usage : python -m "
            "src.vision.test_ocr "
            "<image>"
        )

    image_path = sys.argv[
        1
    ]

    ocr = MedicineOCR()

    result = ocr.extract(
        image_path
    )

    print("=" * 72)
    print("PHARMORA - OCR TEST")
    print("=" * 72)

    print()
    print("TEXT EXTRACTED")
    print("-" * 72)

    print(
        result["text"]
    )

    print()
    print(
        "Average confidence :",
        result[
            "average_confidence"
        ],
    )

    print()
    print("LINES")
    print("-" * 72)

    for index, (
        text,
        score,
    ) in enumerate(
        zip(
            result["lines"],
            result["scores"],
        ),
        start=1,
    ):
        print(
            f"{index}. "
            f"{text} "
            f"| score={score}"
        )


if __name__ == "__main__":
    main()