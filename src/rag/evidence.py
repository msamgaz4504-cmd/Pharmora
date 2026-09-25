from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"

EVIDENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "request_type": {
            "type": "string",
            "enum": [
                "informational",
                "personalized_medical_decision",
                "out_of_scope",
            ],
        },
        "sufficient": {
            "type": "boolean",
        },
        "relevant_sources": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "reason": {
            "type": "string",
        },
    },
    "required": [
        "request_type",
        "sufficient",
        "relevant_sources",
        "reason",
    ],
    "additionalProperties": False,
}


class EvidenceSelector:
    def __init__(
        self,
        model: str | None = None,
    ):
        api_key = os.getenv(
            "GROQ_API_KEY"
        )

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY est absente."
            )

        self.model = (
            model
            or os.getenv(
                "GROQ_MODEL",
                DEFAULT_MODEL,
            )
        )

        self.client = Groq(
            api_key=api_key
        )

    def select(
        self,
        question: str,
        passages: list[dict],
    ) -> dict:
        if not question.strip():
            raise ValueError(
                "La question est vide."
            )

        if not passages:
            return {
                "request_type": "informational",
                "sufficient": False,
                "relevant_sources": [],
                "reason": (
                    "Aucun passage candidat "
                    "n'a été fourni."
                ),
                "passages": [],
            }

        source_blocks = []

        for index, passage in enumerate(
            passages,
            start=1,
        ):
            source_id = f"S{index}"

            source_blocks.append(
                "\n".join(
                    [
                        f"[{source_id}]",
                        (
                            "Médicament : "
                            f"{passage['medicine_name']}"
                        ),
                        (
                            "Document : "
                            f"{passage['document_type']}"
                        ),
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

        context = "\n\n".join(
            source_blocks
        )

        system_prompt = """
Tu es le composant de contrôle sémantique d'un système RAG pharmaceutique.

Tu dois effectuer deux tâches indépendantes.

TÂCHE 1 — CLASSIFIER LA DEMANDE

Utilise exactement une catégorie :

informational :
La personne demande des informations générales, factuelles ou documentaires sur un médicament, par exemple ses indications, effets indésirables, contre-indications, interactions, composition, posologie décrite dans le document ou utilisation réglementaire.

personalized_medical_decision :
La personne demande une décision, une recommandation ou une conduite thérapeutique adaptée à sa propre situation ou à celle d'une personne particulière. Cela inclut notamment choisir un médicament, décider de le prendre, commencer, arrêter, remplacer ou modifier un traitement, déterminer personnellement une dose, ou obtenir une décision clinique individualisée.

out_of_scope :
La demande n'est pas une demande d'information pharmaceutique concernant le médicament sélectionné.

Une question n'est pas personnalisée simplement parce qu'elle porte sur la grossesse, les effets indésirables, la posologie ou les contre-indications. Si elle demande ce que disent les informations pharmaceutiques de manière générale, elle est informational.

TÂCHE 2 — ÉVALUER LES PREUVES

Pour une demande informational, détermine si les extraits fournis contiennent suffisamment d'informations pour répondre précisément à la question.

Pour personalized_medical_decision ou out_of_scope :
- sufficient doit être false ;
- relevant_sources doit être une liste vide.

Pour informational :
- sélectionne uniquement les sources qui répondent réellement à la question ;
- sufficient doit être true uniquement si les extraits sélectionnés permettent une réponse fondée ;
- si l'information demandée est absente, sufficient doit être false ;
- ne considère jamais le simple fait qu'un extrait parle du médicament comme une preuve suffisante ;
- n'utilise aucune connaissance externe.

Les identifiants de relevant_sources doivent être exclusivement des identifiants présents dans le contexte.
""".strip()

        user_prompt = (
            f"Question utilisateur :\n"
            f"{question}\n\n"
            f"Extraits candidats :\n"
            f"{context}"
        )

        response = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "evidence_selection",
                        "strict": True,
                        "schema": EVIDENCE_SCHEMA,
                    },
                },
                temperature=0,
                reasoning_effort="low",
                max_completion_tokens=500,
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            raise RuntimeError(
                "Le sélecteur de preuves "
                "n'a retourné aucune réponse."
            )

        data = json.loads(
            content
        )

        request_type = data[
            "request_type"
        ]

        available_sources = {
            f"S{index}": passage
            for index, passage
            in enumerate(
                passages,
                start=1,
            )
        }

        selected_ids = []

        for source_id in data[
            "relevant_sources"
        ]:
            source_id = str(
                source_id
            ).strip()

            if (
                source_id
                in available_sources
                and source_id
                not in selected_ids
            ):
                selected_ids.append(
                    source_id
                )

        sufficient = bool(
            data["sufficient"]
        )

        if request_type != "informational":
            sufficient = False
            selected_ids = []

        if (
            sufficient
            and not selected_ids
        ):
            sufficient = False

        if not sufficient:
            selected_ids = []

        selected_passages = [
            available_sources[
                source_id
            ]
            for source_id
            in selected_ids
        ]

        return {
            "request_type": request_type,
            "sufficient": sufficient,
            "relevant_sources": selected_ids,
            "reason": str(
                data["reason"]
            ).strip(),
            "passages": selected_passages,
        }