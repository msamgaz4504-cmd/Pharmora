from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from transformers import AutoTokenizer


MODEL_NAME = "intfloat/multilingual-e5-small"
TOKEN_LIMIT = 480
OVERLAP_TOKENS = 40

DATA_DIR = Path("data")
DOCUMENTS_DIR = DATA_DIR / "documents"
CHUNKS_DIR = DATA_DIR / "chunks"
OUTPUT_PATH = CHUNKS_DIR / "chunks.json"

NOISE_LINES = {
    "précédent",
    "suivant",
    "haut de page",
    "plan du site",
    "mentions légales",
    "retour à l'accueil",
}


def load_json(path: Path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def save_json(data, path: Path):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.replace("\xa0", " ")
    text = text.replace("\u202f", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_text(text: str) -> str:
    text = normalize_text(text)

    lines = []

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            lines.append("")
            continue

        if stripped.lower() in NOISE_LINES:
            continue

        lines.append(stripped)

    return normalize_text(
        "\n".join(lines)
    )


def word_count(text: str) -> int:
    return len(
        re.findall(r"\S+", text)
    )


def build_embedding_text(
    medicine_name: str,
    document_type: str,
    section_number: str,
    section_title: str,
    content: str,
) -> str:
    return (
        f"Médicament : {medicine_name}\n"
        f"Document : {document_type}\n"
        f"Section : {section_number} - {section_title}\n\n"
        f"{content}"
    ).strip()


def passage_text(
    medicine_name: str,
    document_type: str,
    section_number: str,
    section_title: str,
    content: str,
) -> str:
    return (
        "passage: "
        + build_embedding_text(
            medicine_name,
            document_type,
            section_number,
            section_title,
            content,
        )
    )


def token_count(
    tokenizer,
    text: str,
) -> int:
    return len(
        tokenizer.encode(
            text,
            add_special_tokens=True,
            truncation=False,
        )
    )


def split_sentences(text: str) -> list[str]:
    text = normalize_text(text)

    parts = re.split(
        r"(?<=[.!?;:])\s+(?=[A-ZÀ-ÖØ-Ý0-9•·\-])",
        text,
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def build_units(text: str) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(
            r"\n\s*\n",
            text,
        )
        if paragraph.strip()
    ]

    units = []

    for paragraph in paragraphs:
        sentences = split_sentences(
            paragraph
        )

        if sentences:
            units.extend(sentences)
        else:
            units.append(paragraph)

    if not units and text.strip():
        units = [text.strip()]

    return units


def split_oversized_unit(
    tokenizer,
    unit: str,
    medicine_name: str,
    document_type: str,
    section_number: str,
    section_title: str,
) -> list[str]:
    header = passage_text(
        medicine_name,
        document_type,
        section_number,
        section_title,
        "",
    )

    header_tokens = token_count(
        tokenizer,
        header,
    )

    available = (
        TOKEN_LIMIT
        - header_tokens
        - 8
    )

    if available <= 50:
        raise RuntimeError(
            "Budget token insuffisant pour "
            f"{medicine_name} {section_number}"
        )

    ids = tokenizer.encode(
        unit,
        add_special_tokens=False,
        truncation=False,
    )

    parts = []

    start = 0

    while start < len(ids):
        end = min(
            start + available,
            len(ids),
        )

        part_ids = ids[start:end]

        part = tokenizer.decode(
            part_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        ).strip()

        if part:
            parts.append(part)

        start = end

    return parts


def get_overlap(
    tokenizer,
    text: str,
) -> str:
    ids = tokenizer.encode(
        text,
        add_special_tokens=False,
        truncation=False,
    )

    if len(ids) <= OVERLAP_TOKENS:
        return text.strip()

    overlap_ids = ids[
        -OVERLAP_TOKENS:
    ]

    return tokenizer.decode(
        overlap_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    ).strip()


def chunk_section(
    tokenizer,
    medicine_name: str,
    document_type: str,
    section_number: str,
    section_title: str,
    text: str,
) -> list[str]:
    text = clean_text(text)

    if not text:
        return []

    complete = passage_text(
        medicine_name,
        document_type,
        section_number,
        section_title,
        text,
    )

    if (
        token_count(
            tokenizer,
            complete,
        )
        <= TOKEN_LIMIT
    ):
        return [text]

    raw_units = build_units(text)

    units = []

    for unit in raw_units:
        candidate = passage_text(
            medicine_name,
            document_type,
            section_number,
            section_title,
            unit,
        )

        if (
            token_count(
                tokenizer,
                candidate,
            )
            <= TOKEN_LIMIT
        ):
            units.append(unit)
        else:
            units.extend(
                split_oversized_unit(
                    tokenizer,
                    unit,
                    medicine_name,
                    document_type,
                    section_number,
                    section_title,
                )
            )

    chunks = []
    current = ""

    for unit in units:
        candidate = (
            f"{current}\n\n{unit}"
            if current
            else unit
        ).strip()

        full_candidate = passage_text(
            medicine_name,
            document_type,
            section_number,
            section_title,
            candidate,
        )

        if (
            token_count(
                tokenizer,
                full_candidate,
            )
            <= TOKEN_LIMIT
        ):
            current = candidate
            continue

        if current:
            chunks.append(
                current.strip()
            )

        overlap = (
            get_overlap(
                tokenizer,
                current,
            )
            if current
            else ""
        )

        with_overlap = (
            f"{overlap}\n\n{unit}"
            if overlap
            else unit
        ).strip()

        full_overlap = passage_text(
            medicine_name,
            document_type,
            section_number,
            section_title,
            with_overlap,
        )

        if (
            token_count(
                tokenizer,
                full_overlap,
            )
            <= TOKEN_LIMIT
        ):
            current = with_overlap
        else:
            current = unit

    if current:
        chunks.append(
            current.strip()
        )

    return chunks


def main():
    print(
        "\n=== PHARMORA TOKEN-AWARE CHUNKING ===\n"
    )

    paths = sorted(
        DOCUMENTS_DIR.glob("*.json")
    )

    if len(paths) != 30:
        raise RuntimeError(
            f"30 documents attendus, "
            f"{len(paths)} trouvés"
        )

    print(
        f"Tokenizer: {MODEL_NAME}"
    )

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME
    )

    chunks = []
    documents_seen = set()
    cis_seen = set()

    for path in paths:
        document = load_json(path)

        required = {
            "document_id",
            "cis",
            "medicine_name",
            "document_type",
            "source",
            "source_url",
            "sections",
        }

        missing = required - set(
            document
        )

        if missing:
            raise RuntimeError(
                f"{path.name}: champs manquants "
                f"{sorted(missing)}"
            )

        document_chunks = []

        for section in document[
            "sections"
        ]:
            number = str(
                section.get(
                    "section_number",
                    "",
                )
            ).strip()

            title = str(
                section.get(
                    "title",
                    "",
                )
            ).strip()

            content = clean_text(
                section.get(
                    "text",
                    "",
                )
            )

            if not content:
                continue

            parts = chunk_section(
                tokenizer,
                document["medicine_name"],
                document["document_type"],
                number,
                title,
                content,
            )

            for index, part in enumerate(
                parts
            ):
                embedding_text = (
                    build_embedding_text(
                        document[
                            "medicine_name"
                        ],
                        document[
                            "document_type"
                        ],
                        number,
                        title,
                        part,
                    )
                )

                tokens = token_count(
                    tokenizer,
                    "passage: "
                    + embedding_text,
                )

                if tokens > TOKEN_LIMIT:
                    raise RuntimeError(
                        f"Chunk > {TOKEN_LIMIT}: "
                        f"{document['document_id']} "
                        f"{number} ({tokens})"
                    )

                chunk_id = (
                    f"{document['cis']}_"
                    f"{document['document_type'].lower()}_"
                    f"{number.replace('.', '_')}_"
                    f"{index:03d}"
                )

                document_chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": document[
                            "document_id"
                        ],
                        "cis": document["cis"],
                        "medicine_name": document[
                            "medicine_name"
                        ],
                        "document_type": document[
                            "document_type"
                        ],
                        "section_number": number,
                        "section_title": title,
                        "section_index": section.get(
                            "section_index"
                        ),
                        "chunk_index": index,
                        "chunks_in_section": len(
                            parts
                        ),
                        "word_count": word_count(
                            part
                        ),
                        "token_count": tokens,
                        "content": part,
                        "embedding_text": (
                            embedding_text
                        ),
                        "source": document[
                            "source"
                        ],
                        "source_url": document[
                            "source_url"
                        ],
                        "retrieved_at": document.get(
                            "retrieved_at"
                        ),
                        "content_hash": document.get(
                            "content_hash"
                        ),
                    }
                )

        if not document_chunks:
            raise RuntimeError(
                f"{document['document_id']}: "
                "aucun chunk"
            )

        chunks.extend(
            document_chunks
        )

        documents_seen.add(
            document["document_id"]
        )

        cis_seen.add(
            str(document["cis"])
        )

        print(
            f"{document['document_id']}: "
            f"{len(document_chunks)} chunks"
        )

    ids = [
        chunk["chunk_id"]
        for chunk in chunks
    ]

    duplicates = [
        key
        for key, value
        in Counter(ids).items()
        if value > 1
    ]

    if duplicates:
        raise RuntimeError(
            f"IDs dupliqués: {duplicates[:10]}"
        )

    if len(documents_seen) != 30:
        raise RuntimeError(
            "Tous les documents ne sont "
            "pas représentés"
        )

    if len(cis_seen) != 15:
        raise RuntimeError(
            "Tous les médicaments ne sont "
            "pas représentés"
        )

    required_rcp = {
        "4.1",
        "4.2",
        "4.3",
        "4.4",
        "4.5",
        "4.6",
        "4.8",
    }

    rcp_documents = {
        chunk["document_id"]
        for chunk in chunks
        if chunk["document_type"]
        == "RCP"
    }

    for document_id in rcp_documents:
        sections = {
            chunk["section_number"]
            for chunk in chunks
            if chunk["document_id"]
            == document_id
        }

        missing = (
            required_rcp - sections
        )

        if missing:
            raise RuntimeError(
                f"{document_id}: sections "
                f"manquantes {sorted(missing)}"
            )

    token_counts = [
        chunk["token_count"]
        for chunk in chunks
    ]

    over_limit = sum(
        count > TOKEN_LIMIT
        for count in token_counts
    )

    save_json(
        chunks,
        OUTPUT_PATH,
    )

    print(
        "\n=== TOKEN QA ==="
    )

    print(
        f"Documents: "
        f"{len(documents_seen)}/30"
    )

    print(
        f"Medicines: {len(cis_seen)}/15"
    )

    print(
        f"Chunks: {len(chunks)}"
    )

    print(
        f"Maximum tokens: "
        f"{max(token_counts)}"
    )

    print(
        f"Average tokens: "
        f"{sum(token_counts) / len(token_counts):.1f}"
    )

    print(
        f"Passages > {TOKEN_LIMIT}: "
        f"{over_limit}"
    )

    print(
        f"Unique IDs: "
        f"{len(set(ids))}/{len(ids)}"
    )

    if over_limit != 0:
        raise RuntimeError(
            "Des chunks dépassent encore "
            "la limite"
        )

    print(
        "Critical sections: PASS"
    )

    print(
        "Token limits: PASS"
    )

    print(
        "\nFINAL STATUS: PASS"
    )

    print(
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()