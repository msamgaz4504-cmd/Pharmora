from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"


class ConversationContextualizer:
    def __init__(
        self,
        model: str | None = None,
        client=None,
    ):
        self.model = (
            model
            or os.getenv(
                "GROQ_MODEL",
                DEFAULT_MODEL,
            )
        )

        if client is not None:
            self.client = client
            return

        api_key = os.getenv(
            "GROQ_API_KEY"
        )

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY est absente."
            )

        self.client = Groq(
            api_key=api_key
        )

    def contextualize(
        self,
        question: str,
        medicine_name: str,
        history: list[dict[str, str]],
    ) -> dict:
        question = question.strip()
        medicine_name = (
            medicine_name.strip()
        )

        if not question:
            raise ValueError(
                "La question est vide."
            )

        if not medicine_name:
            raise ValueError(
                "Le nom du médicament est vide."
            )

        clean_history = (
            self._validate_history(
                history
            )
        )

        if not clean_history:
            return {
                "standalone_query": question,
                "rewritten": False,
            }

        history_text = (
            self._format_history(
                clean_history
            )
        )

        response = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu contextualises des questions "
                            "pour un système RAG pharmaceutique. "
                            "Tu ne réponds jamais à la question "
                            "et tu n'ajoutes aucune information médicale. "
                            "Tu dois d'abord déterminer la relation entre "
                            "la question actuelle et l'historique. "
                            "Utilise exactement l'une de ces catégories : "
                            "new_topic, continuation ou standalone. "
                            "new_topic signifie que la question actuelle "
                            "introduit explicitement un nouveau sujet. "
                            "Dans ce cas, n'importe aucun sujet précédent "
                            "qui n'est pas explicitement demandé. "
                            "continuation signifie que la question actuelle "
                            "est incomplète et dépend réellement du sujet "
                            "précédent pour être comprise. "
                            "standalone signifie qu'elle est déjà "
                            "compréhensible seule. "
                            "Utilise l'historique uniquement pour résoudre "
                            "les pronoms, références, ellipses ou sujets "
                            "réellement nécessaires. "
                            "Préserve exactement l'intention actuelle. "
                            "Exemple : après une question sur les effets "
                            "indésirables, 'Et les plus fréquents ?' est "
                            "une continuation et doit conserver la notion "
                            "d'effets indésirables. "
                            "En revanche, après cette même question, "
                            "'Et pendant la grossesse ?' est un new_topic. "
                            "La requête autonome doit alors porter sur "
                            "l'utilisation ou les informations concernant "
                            "le médicament pendant la grossesse, sans ajouter "
                            "'effets indésirables' ou tout autre thème "
                            "de la question précédente. "
                            "En cas de doute, utilise la contextualisation "
                            "minimale."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Médicament actif : "
                            f"{medicine_name}\n\n"
                            f"Historique récent :\n"
                            f"{history_text}\n\n"
                            f"Question actuelle :\n"
                            f"{question}\n\n"
                            "Détermine d'abord la relation avec "
                            "l'historique, puis produis une requête "
                            "autonome destinée au moteur documentaire."
                        ),
                    },
                ],
                temperature=0,
                max_completion_tokens=250,
                reasoning_effort="low",
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": (
                            "conversation_context"
                        ),
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "context_relation": {
                                    "type": "string",
                                    "enum": [
                                        "new_topic",
                                        "continuation",
                                        "standalone",
                                    ],
                                },
                                "standalone_query": {
                                    "type": "string"
                                },
                            },
                            "required": [
                                "context_relation",
                                "standalone_query",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
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
                "Le contextualizer n'a "
                "retourné aucun résultat."
            )

        try:
            data = json.loads(
                content
            )
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Réponse JSON invalide "
                "du contextualizer."
            ) from error

        context_relation = str(
            data.get(
                "context_relation",
                "",
            )
        ).strip()

        if context_relation not in {
            "new_topic",
            "continuation",
            "standalone",
        }:
            raise RuntimeError(
                "Relation conversationnelle "
                "invalide."
            )

        standalone_query = str(
            data.get(
                "standalone_query",
                "",
            )
        ).strip()

        if not standalone_query:
            raise RuntimeError(
                "Le contextualizer a retourné "
                "une requête vide."
            )

        return {
            "standalone_query": (
                standalone_query
            ),
            "rewritten": (
                standalone_query.casefold()
                != question.casefold()
            ),
        }

    def _validate_history(
        self,
        history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        if history is None:
            return []

        if not isinstance(
            history,
            list,
        ):
            raise TypeError(
                "history doit être une liste."
            )

        validated = []

        for message in history:
            if not isinstance(
                message,
                dict,
            ):
                raise TypeError(
                    "Chaque message de "
                    "l'historique doit être "
                    "un dictionnaire."
                )

            role = str(
                message.get(
                    "role",
                    "",
                )
            ).strip()

            content = str(
                message.get(
                    "content",
                    "",
                )
            ).strip()

            if role not in {
                "user",
                "assistant",
            }:
                raise ValueError(
                    "Rôle invalide dans "
                    "l'historique."
                )

            if not content:
                raise ValueError(
                    "Message vide dans "
                    "l'historique."
                )

            validated.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return validated

    def _format_history(
        self,
        history: list[dict[str, str]],
    ) -> str:
        lines = []

        for message in history:
            label = (
                "Utilisateur"
                if message["role"] == "user"
                else "Assistant"
            )

            lines.append(
                f"{label} : "
                f"{message['content']}"
            )

        return "\n".join(
            lines
        )