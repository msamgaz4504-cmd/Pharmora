from __future__ import annotations

from pathlib import Path

from paddleocr import PaddleOCR


class MedicineOCR:
    def __init__(self):
        self.ocr = PaddleOCR(
            lang="fr",
            ocr_version="PP-OCRv5",
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True,
            enable_mkldnn=False,
        )

    def extract(
        self,
        image_path: str | Path,
    ) -> dict:
        image_path = Path(
            image_path
        )

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image introuvable : {image_path}"
            )

        results = self.ocr.predict(
            str(image_path)
        )

        texts = []
        scores = []
        boxes = []

        for result in results:
            data = result.json

            if callable(data):
                data = data()

            payload = data.get(
                "res",
                data,
            )

            rec_texts = payload.get(
                "rec_texts",
                [],
            )

            rec_scores = payload.get(
                "rec_scores",
                [],
            )

            rec_boxes = payload.get(
                "rec_boxes",
                [],
            )

            for index, text in enumerate(
                rec_texts
            ):
                text = str(
                    text
                ).strip()

                if not text:
                    continue

                score = None

                if index < len(
                    rec_scores
                ):
                    score = float(
                        rec_scores[
                            index
                        ]
                    )

                box = None

                if index < len(
                    rec_boxes
                ):
                    current_box = (
                        rec_boxes[
                            index
                        ]
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

                texts.append(
                    text
                )

                scores.append(
                    score
                )

                boxes.append(
                    box
                )

        full_text = "\n".join(
            texts
        )

        valid_scores = [
            score
            for score in scores
            if score is not None
        ]

        average_confidence = (
            sum(
                valid_scores
            )
            / len(
                valid_scores
            )
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