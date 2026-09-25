from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "intfloat/multilingual-e5-small"

CHUNKS_PATH = Path(
    "data/chunks/chunks.json"
)

INDEX_DIR = Path("data/index")

INDEX_PATH = (
    INDEX_DIR / "pharmora.faiss"
)

METADATA_PATH = (
    INDEX_DIR / "metadata.json"
)

CONFIG_PATH = (
    INDEX_DIR / "config.json"
)

MAX_MODEL_TOKENS = 512
BATCH_SIZE = 32


def load_chunks():
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            CHUNKS_PATH
        )

    chunks = json.loads(
        CHUNKS_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not chunks:
        raise RuntimeError(
            "Aucun chunk"
        )

    return chunks


def main():
    print(
        "\n=== PHARMORA VECTOR INDEX ===\n"
    )

    chunks = load_chunks()

    print(
        f"Chunks loaded: {len(chunks)}"
    )

    print(
        f"Model: {MODEL_NAME}"
    )

    model = SentenceTransformer(
        MODEL_NAME
    )

    tokenizer = model.tokenizer

    texts = [
        "passage: "
        + chunk["embedding_text"]
        for chunk in chunks
    ]

    lengths = [
        len(
            tokenizer.encode(
                text,
                add_special_tokens=True,
                truncation=False,
            )
        )
        for text in texts
    ]

    maximum = max(lengths)

    over_limit = sum(
        length > MAX_MODEL_TOKENS
        for length in lengths
    )

    print(
        f"Maximum tokens: {maximum}"
    )

    print(
        f"Passages > {MAX_MODEL_TOKENS}: "
        f"{over_limit}"
    )

    if over_limit:
        raise RuntimeError(
            "Index refusé : certains "
            "passages seraient tronqués"
        )

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype="float32",
    )

    if not np.isfinite(
        embeddings
    ).all():
        raise RuntimeError(
            "Embeddings invalides"
        )

    norms = np.linalg.norm(
        embeddings,
        axis=1,
    )

    if not np.allclose(
        norms,
        1.0,
        atol=1e-3,
    ):
        raise RuntimeError(
            "Embeddings non normalisés"
        )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(
        dimension
    )

    index.add(
        embeddings
    )

    if index.ntotal != len(
        chunks
    ):
        raise RuntimeError(
            "Nombre de vecteurs incorrect"
        )

    INDEX_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    faiss.write_index(
        index,
        str(INDEX_PATH),
    )

    METADATA_PATH.write_text(
        json.dumps(
            chunks,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    config = {
        "model_name": MODEL_NAME,
        "dimension": dimension,
        "vector_count": len(chunks),
        "metric": "inner_product",
        "normalized_embeddings": True,
        "similarity": "cosine",
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
        "maximum_tokens_seen": maximum,
        "passages_over_512": over_limit,
    }

    CONFIG_PATH.write_text(
        json.dumps(
            config,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Embedding shape: "
        f"{embeddings.shape}"
    )

    print(
        f"Vectors indexed: "
        f"{index.ntotal}"
    )

    print(
        f"Dimension: {dimension}"
    )

    print(
        "Normalization: PASS"
    )

    print(
        "Token safety: PASS"
    )

    print(
        "FAISS persistence: PASS"
    )

    print(
        f"Saved: {INDEX_PATH}"
    )

    print(
        "\nFINAL STATUS: PASS"
    )


if __name__ == "__main__":
    main()