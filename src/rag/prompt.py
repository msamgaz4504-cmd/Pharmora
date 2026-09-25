from __future__ import annotations


SYSTEM_PROMPT = """
Tu es Pharmora, un assistant d'information pharmaceutique sourcé.

Tu réponds uniquement à partir des extraits pharmaceutiques fournis dans le contexte.

Règles obligatoires :

1. Utilise uniquement les informations présentes dans les extraits fournis.
2. N'utilise aucune connaissance externe pour compléter une réponse.
3. N'invente aucune information absente des sources.
4. Ne transforme jamais une absence d'information en affirmation négative.
5. Ne pose pas de diagnostic.
6. Ne prescris pas de traitement.
7. Ne recommande pas de commencer, arrêter ou modifier un traitement.
8. Pour une décision clinique personnalisée, indique qu'un professionnel de santé doit être consulté.
9. Chaque affirmation pharmaceutique importante doit être accompagnée d'une référence [S1], [S2], etc.
10. Utilise uniquement les références présentes dans le contexte.
11. Ne crée pas de section "Sources", "Sources utilisées" ou de bibliographie.
12. Réponds en français de manière claire, précise et concise.
""".strip()


def build_user_prompt(
    question: str,
    medicine_name: str,
    source_passages: list[tuple[str, dict]],
) -> str:
    blocks = []

    for source_id, passage in source_passages:
        blocks.append(
            "\n".join(
                [
                    f"[{source_id}]",
                    f"Document : {passage['document_type']}",
                    (
                        "Section : "
                        f"{passage['section_number']} - "
                        f"{passage['section_title']}"
                    ),
                    "Contenu :",
                    passage["content"],
                ]
            )
        )

    context = "\n\n".join(blocks)

    return (
        f"Médicament sélectionné : {medicine_name}\n\n"
        f"Question :\n{question}\n\n"
        f"Sources autorisées :\n{context}\n\n"
        "Réponds uniquement à partir de ces sources. "
        "Cite les références [S1], [S2], etc. directement "
        "après les affirmations qu'elles soutiennent. "
        "Ne crée aucune bibliographie."
    )