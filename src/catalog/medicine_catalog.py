from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


DEFAULT_CATALOG_PATH = Path(
    "data/catalog/medicines.json"
)


class MedicineCatalog:
    def __init__(
        self,
        catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    ):
        self.catalog_path = Path(
            catalog_path
        )

        self._medicines = (
            self._load_catalog()
        )

        if not self._medicines:
            raise RuntimeError(
                "Le catalogue des médicaments est vide."
            )

    @property
    def medicines(
        self,
    ) -> list[dict]:
        return [
            dict(medicine)
            for medicine in self._medicines
        ]

    @property
    def count(self) -> int:
        return len(
            self._medicines
        )

    def get_by_cis(
        self,
        cis: str,
    ) -> dict | None:
        target = str(
            cis
        ).strip()

        if not target:
            return None

        for medicine in self._medicines:
            if (
                self._get_cis(
                    medicine
                )
                == target
            ):
                return dict(
                    medicine
                )

        return None

    def search(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[dict]:
        query = self.normalize(
            query
        )

        if not query:
            return []

        if (
            limit is not None
            and limit < 1
        ):
            raise ValueError(
                "limit doit être supérieur "
                "ou égal à 1."
            )

        exact_matches = []

        for medicine in self._medicines:
            name = self.normalize(
                self._get_name(
                    medicine
                )
            )

            if name == query:
                exact_matches.append(
                    medicine
                )

        if exact_matches:
            return self._copy_results(
                exact_matches,
                limit=limit,
            )

        query_tokens = (
            self._tokens(
                query
            )
        )

        ranked = []

        for medicine in self._medicines:
            name = self.normalize(
                self._get_name(
                    medicine
                )
            )

            name_tokens = (
                self._tokens(
                    name
                )
            )

            score = self._search_score(
                query=query,
                query_tokens=query_tokens,
                name=name,
                name_tokens=name_tokens,
            )

            if score is None:
                continue

            ranked.append(
                (
                    score,
                    name,
                    medicine,
                )
            )

        ranked.sort(
            key=lambda item: (
                -item[0],
                item[1],
            )
        )

        results = [
            medicine
            for _, _, medicine
            in ranked
        ]

        return self._copy_results(
            results,
            limit=limit,
        )

    def resolve(
        self,
        query: str,
    ) -> dict:
        normalized_query = (
            self.normalize(
                query
            )
        )

        if not normalized_query:
            return {
                "status": "not_found",
                "query": query,
                "matches": [],
                "medicine": None,
            }

        exact_matches = [
            medicine
            for medicine in self._medicines
            if self.normalize(
                self._get_name(
                    medicine
                )
            )
            == normalized_query
        ]

        if len(exact_matches) == 1:
            medicine = dict(
                exact_matches[0]
            )

            return {
                "status": "resolved",
                "query": query,
                "matches": [
                    medicine
                ],
                "medicine": medicine,
            }

        if len(exact_matches) > 1:
            matches = [
                dict(medicine)
                for medicine
                in exact_matches
            ]

            return {
                "status": "ambiguous",
                "query": query,
                "matches": matches,
                "medicine": None,
            }

        matches = self.search(
            query
        )

        if not matches:
            return {
                "status": "not_found",
                "query": query,
                "matches": [],
                "medicine": None,
            }

        if len(matches) == 1:
            return {
                "status": "resolved",
                "query": query,
                "matches": matches,
                "medicine": matches[0],
            }

        return {
            "status": "ambiguous",
            "query": query,
            "matches": matches,
            "medicine": None,
        }

    @staticmethod
    def normalize(
        value: str,
    ) -> str:
        value = unicodedata.normalize(
            "NFKD",
            str(value),
        )

        value = "".join(
            character
            for character in value
            if not unicodedata.combining(
                character
            )
        )

        value = value.casefold()

        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value,
        )

        return " ".join(
            value.split()
        )

    def _load_catalog(
        self,
    ) -> list[dict]:
        if not self.catalog_path.exists():
            raise FileNotFoundError(
                "Catalogue introuvable : "
                f"{self.catalog_path}"
            )

        data = json.loads(
            self.catalog_path.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            data,
            list,
        ):
            medicines = data

        elif isinstance(
            data,
            dict,
        ):
            if isinstance(
                data.get(
                    "medicines"
                ),
                list,
            ):
                medicines = data[
                    "medicines"
                ]

            else:
                medicines = [
                    value
                    for value
                    in data.values()
                    if isinstance(
                        value,
                        dict,
                    )
                ]

        else:
            raise RuntimeError(
                "Format du catalogue "
                "non reconnu."
            )

        validated = []

        seen_cis = set()

        for medicine in medicines:
            if not isinstance(
                medicine,
                dict,
            ):
                continue

            cis = self._get_cis(
                medicine
            )

            name = self._get_name(
                medicine
            )

            if not cis or not name:
                continue

            if cis in seen_cis:
                raise RuntimeError(
                    "CIS dupliqué dans "
                    f"le catalogue : {cis}"
                )

            seen_cis.add(
                cis
            )

            validated.append(
                medicine
            )

        return validated

    def _search_score(
        self,
        query: str,
        query_tokens: set[str],
        name: str,
        name_tokens: set[str],
    ) -> float | None:
        if query in name:
            return (
                1000.0
                + len(query)
                / max(
                    len(name),
                    1,
                )
            )

        if not query_tokens:
            return None

        if not query_tokens.issubset(
            name_tokens
        ):
            return None

        coverage = (
            len(query_tokens)
            / max(
                len(name_tokens),
                1,
            )
        )

        return (
            100.0
            + coverage
        )

    def _tokens(
        self,
        value: str,
    ) -> set[str]:
        return {
            token
            for token
            in value.split()
            if token
        }

    def _copy_results(
        self,
        medicines: list[dict],
        limit: int | None,
    ) -> list[dict]:
        if limit is not None:
            medicines = (
                medicines[:limit]
            )

        return [
            dict(medicine)
            for medicine
            in medicines
        ]

    def _get_name(
        self,
        medicine: dict,
    ) -> str:
        for key in (
            "name",
            "medicine_name",
            "denomination",
        ):
            value = medicine.get(
                key
            )

            if value:
                return str(
                    value
                ).strip()

        return ""

    def _get_cis(
        self,
        medicine: dict,
    ) -> str:
        for key in (
            "cis",
            "CIS",
            "cis_code",
        ):
            value = medicine.get(
                key
            )

            if value is not None:
                return str(
                    value
                ).strip()

        return ""