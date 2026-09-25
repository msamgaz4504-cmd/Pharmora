from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"

REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "rewritten_query": {
            "type": "string",
        },
    },
    "required": [
        "rewritten_query",
    ],
    "additionalProperties": False,
}


class QueryRewriter:
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

    def rewrite(
        self,
        question: str,
        medicine_name: str,
    ) -> str:
        if not question.strip():
            raise ValueError(
                "La question est vide."
            )

        prompt = (
            "Transforme la question utilisateur en une requête "
            "documentaire pharmaceutique explicite destinée à un "
            "moteur de recherche sémantique.\n\n"
            f"Médicament : {medicine_name}\n"
            f"Question utilisateur : {question}\n\n"
            "La requête reformulée doit conserver exactement "
            "l'intention de la question. "
            "Elle ne doit pas répondre à la question. "
            "Elle ne doit pas ajouter de fait médical. "
            "Elle doit utiliser une formulation pharmaceutique "
            "claire lorsqu'elle peut être déduite de la question. "
            "Elle doit rester concise et autonome."
        )

        response = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu reformules des questions en "
                            "requêtes documentaires pour un "
                            "système RAG pharmaceutique. "
                            "Tu préserves strictement "
                            "l'intention originale."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "query_rewrite",
                        "strict": True,
                        "schema": REWRITE_SCHEMA,
                    },
                },
                temperature=0,
                reasoning_effort="low",
                max_completion_tokens=200,
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
                "Le Query Rewriter n'a retourné "
                "aucune réponse."
            )

        data = json.loads(
            content
        )

        rewritten_query = str(
            data["rewritten_query"]
        ).strip()

        if not rewritten_query:
            raise RuntimeError(
                "La requête reformulée est vide."
            )

        return rewritten_query