from __future__ import annotations

import re
import unicodedata
from itertools import combinations
from pathlib import Path

from src.catalog.medicine_catalog import MedicineCatalog
from src.vision.ocr import MedicineOCR


class MedicineImageIdentifier:
    def __init__(
        self,
        ocr: MedicineOCR | None = None,
        catalog: MedicineCatalog | None = None,
    ):
        self.ocr = ocr or MedicineOCR()
        self.catalog = catalog or MedicineCatalog()

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize(
            "NFKD",
            text,
        )

        text = "".join(
            char
            for char in text
            if not unicodedata.combining(
                char
            )
        )

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9%.,]+",
            " ",
            text,
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

    @staticmethod
    def _extract_dosage(
        lines: list[str],
    ) -> str | None:
        joined = " ".join(
            lines
        )

        match = re.search(
            r"\b\d+(?:[.,]\d+)?\s*(?:mg|g|ml|µg|mcg|%)\b",
            joined,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(
                0
            )

        for index in range(
            len(lines) - 1
        ):
            first = lines[index].strip()
            second = lines[
                index + 1
            ].strip()

            if re.fullmatch(
                r"\d+(?:[.,]\d+)?",
                first,
            ) and re.fullmatch(
                r"mg|g|ml|µg|mcg|%",
                second,
                flags=re.IGNORECASE,
            ):
                return (
                    f"{first} {second}"
                )

        return None

    @classmethod
    def _extract_form(
        cls,
        lines: list[str],
    ) -> str | None:
        forms = [
            "gélule",
            "gélules",
            "comprimé",
            "comprimés",
            "sirop",
            "solution",
            "gel",
            "suspension",
            "poudre",
            "granulés",
            "capsule",
            "capsules",
        ]

        for line in lines:
            normalized = cls._normalize(
                line
            )

            for form in forms:
                if cls._normalize(
                    form
                ) in normalized:
                    return form

        return None

    @classmethod
    def _name_lines(
        cls,
        lines: list[str],
    ) -> list[str]:
        excluded_fragments = [
            "voie orale",
            "douleurs",
            "fievre",
            "surdosage",
            "danger",
            "dose",
            "detruire le foie",
            "gelule",
            "gelules",
            "comprime",
            "comprimes",
            "sirop",
            "solution",
            "suspension",
            "poudre",
            "capsule",
            "capsules",
        ]

        result = []

        for line in lines:
            value = line.strip()

            if not value:
                continue

            normalized = cls._normalize(
                value
            )

            if len(
                normalized
            ) < 3:
                continue

            if not re.search(
                r"[a-z]",
                normalized,
            ):
                continue

            if re.fullmatch(
                r"\d+\s*(?:mg|g|ml|µg|mcg|%)?",
                normalized,
            ):
                continue

            if any(
                fragment in normalized
                for fragment in excluded_fragments
            ):
                continue

            if value not in result:
                result.append(
                    value
                )

        return result[
            :8
        ]

    @staticmethod
    def _status(
        resolution,
    ) -> str:
        if isinstance(
            resolution,
            dict,
        ):
            return str(
                resolution.get(
                    "status",
                    "not_found",
                )
            )

        status = getattr(
            resolution,
            "status",
            None,
        )

        if status is None:
            return "not_found"

        return str(
            status
        )

    def _build_queries(
        self,
        lines: list[str],
    ) -> list[str]:
        dosage = self._extract_dosage(
            lines
        )

        form = self._extract_form(
            lines
        )

        names = self._name_lines(
            lines
        )

        queries = []

        pair_candidates = list(
            combinations(
                names,
                2,
            )
        )

        for first, second in (
            pair_candidates
        ):
            variants = [
                f"{first} {second}",
                f"{second} {first}",
            ]

            for base in variants:
                parts = [
                    base
                ]

                if dosage:
                    parts.append(
                        dosage
                    )

                if form:
                    parts.append(
                        form
                    )

                queries.append(
                    " ".join(
                        parts
                    )
                )

        for name in names:
            parts = [
                name
            ]

            if dosage:
                parts.append(
                    dosage
                )

            if form:
                parts.append(
                    form
                )

            queries.append(
                " ".join(
                    parts
                )
            )

        queries.extend(
            names
        )

        unique_queries = []

        for query in queries:
            query = re.sub(
                r"\s+",
                " ",
                query,
            ).strip()

            if (
                query
                and query
                not in unique_queries
            ):
                unique_queries.append(
                    query
                )

        return unique_queries

    def identify(
        self,
        image_path: str | Path,
    ) -> dict:
        ocr_result = (
            self.ocr.extract(
                image_path
            )
        )

        lines = ocr_result[
            "lines"
        ]

        queries = (
            self._build_queries(
                lines
            )
        )

        ambiguous_results = []

        for query in queries:
            resolution = (
                self.catalog.resolve(
                    query
                )
            )

            status = self._status(
                resolution
            )

            if status == "resolved":
                return {
                    "status": "resolved",
                    "query_used": query,
                    "resolution": resolution,
                    "ocr": ocr_result,
                }

            if status == "ambiguous":
                ambiguous_results.append(
                    {
                        "query": query,
                        "resolution": (
                            resolution
                        ),
                    }
                )

        if ambiguous_results:
            return {
                "status": "ambiguous",
                "query_used": (
                    ambiguous_results[
                        0
                    ][
                        "query"
                    ]
                ),
                "resolution": (
                    ambiguous_results[
                        0
                    ][
                        "resolution"
                    ]
                ),
                "ocr": ocr_result,
            }

        return {
            "status": "not_found",
            "query_used": None,
            "resolution": None,
            "ocr": ocr_result,
        }