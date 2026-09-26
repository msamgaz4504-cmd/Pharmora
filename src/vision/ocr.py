from __future__ import annotations

from pathlib import Path

from rapidocr import RapidOCR


class MedicineOCR:
    def __init__(self):
        self.ocr = RapidOCR()

    def extract(
        self,
        image_path: str | Path,
    ) -> dict:
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image introuvable : {image_path}"
            )

        result = self.ocr(str(image_path))

        texts = []
        scores = []
        boxes = []

        if result is not None:
            raw_texts = getattr(
                result,
                "txts",
                None,
            ) or []

            raw_scores = getattr(
                result,
                "scores",
                None,
            ) or []

            raw_boxes = getattr(
                result,
                "boxes",
                None,
            )

            if raw_boxes is None:
                raw_boxes = []

            for index, text in enumerate(
                raw_texts
            ):
                text = str(text).strip()

                if not text:
                    continue

                score = None

                if index < len(
                    raw_scores
                ):
                    score = float(
                        raw_scores[index]
                    )

                box = None

                if index < len(
                    raw_boxes
                ):
                    current_box = (
                        raw_boxes[index]
                    )

                    if hasattr(
                        current_box,
                        "tolist",
                    ):
                        box = (
                            current_box.tolist()
                        )
                    else:
                        box = current_box

                texts.append(text)
                scores.append(score)
                boxes.append(box)

        full_text = "\n".join(texts)

        valid_scores = [
            score
            for score in scores
            if score is not None
        ]

        average_confidence = (
            sum(valid_scores)
            / len(valid_scores)
            if valid_scores
            else None
        )

        return {
            "text": full_text,
            "lines": texts,
            "scores": scores,
            "boxes": boxes,
            "average_confidence": (
                average_confidence
            ),
        }