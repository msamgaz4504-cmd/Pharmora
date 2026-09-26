from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parents[2]

INDEX_DIR = BASE_DIR / "data" / "index"
INDEX_PATH = INDEX_DIR / "pharmora.faiss"
METADATA_PATH = INDEX_DIR / "metadata.json"
CONFIG_PATH = INDEX_DIR / "config.json"

DEFAULT_CANDIDATE_K = 10


class PharmoraRetriever:
    def __init__(self):
        self._validate_files()

        self.config = json.loads(
            CONFIG_PATH.read_text(
                encoding="utf-8"
            )
        )

        self.metadata = json.loads(
            METADATA_PATH.read_text(
                encoding="utf-8"
            )
        )

        self.index = faiss.read_index(
            str(INDEX_PATH)
        )

        self.model = SentenceTransformer(
            self.config["model_name"]
        )

        self._validate_index()

    def _validate_files(self):
        required = [
            INDEX_PATH,
            METADATA_PATH,
            CONFIG_PATH,
        ]

        missing = [
            str(path)
            for path in required
            if not path.exists()
        ]

        if missing:
            raise FileNotFoundError(
                "Index incomplet : "
                + ", ".join(missing)
            )

    def _validate_index(self):
        if self.index.ntotal != len(
            self.metadata
        ):
            raise RuntimeError(
                "FAISS et metadata désynchronisés."
            )

        if self.index.d != self.config[
            "dimension"
        ]:
            raise RuntimeError(
                "Dimension FAISS incorrecte."
            )

    def _encode_query(
        self,
        question: str,
    ) -> np.ndarray:
        question = question.strip()

        if not question:
            raise ValueError(
                "La question est vide."
            )

        query = (
            question
            if question.lower().startswith(
                "query:"
            )
            else f"query: {question}"
        )

        vector = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        vector = np.asarray(
            vector,
            dtype=np.float32,
        )

        if not np.isfinite(
            vector
        ).all():
            raise RuntimeError(
                "Embedding de requête invalide."
            )

        return vector

    def search(
        self,
        question: str,
        top_k: int = DEFAULT_CANDIDATE_K,
        cis: str | None = None,
        document_type: str | None = None,
    ) -> list[dict]:
        if top_k < 1:
            raise ValueError(
                "top_k doit être >= 1."
            )

        query_vector = self._encode_query(
            question
        )

        has_filter = (
            cis is not None
            or document_type is not None
        )

        search_k = (
            self.index.ntotal
            if has_filter
            else min(
                max(
                    top_k * 10,
                    100,
                ),
                self.index.ntotal,
            )
        )

        scores, indexes = (
            self.index.search(
                query_vector,
                search_k,
            )
        )

        results = []

        for score, index in zip(
            scores[0],
            indexes[0],
        ):
            if index < 0:
                continue

            item = self.metadata[
                int(index)
            ]

            if (
                cis is not None
                and str(
                    item["cis"]
                ) != str(cis)
            ):
                continue

            if (
                document_type is not None
                and item[
                    "document_type"
                ].upper()
                != document_type.upper()
            ):
                continue

            result = dict(
                item
            )

            result[
                "dense_score"
            ] = float(
                score
            )

            result[
                "score"
            ] = float(
                score
            )

            results.append(
                result
            )

            if len(
                results
            ) >= top_k:
                break

        return results