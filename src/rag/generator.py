from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

from src.rag.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)


load_dotenv()


DEFAULT_MODEL = "openai/gpt-oss-120b"


class PharmoraGenerator:
    def __init__(
        self,
        model: str | None = None,
    ):
        api_key = os.getenv("GROQ_API_KEY")

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

    def generate(
        self,
        question: str,
        medicine_name: str,
        source_passages: list[tuple[str, dict]],
    ) -> str:
        if not question.strip():
            raise ValueError(
                "La question est vide."
            )

        if not source_passages:
            raise ValueError(
                "Aucune source fournie au générateur."
            )

        user_prompt = build_user_prompt(
            question=question,
            medicine_name=medicine_name,
            source_passages=source_passages,
        )

        response = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.1,
                max_completion_tokens=1000,
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
                "Groq n'a retourné aucune réponse."
            )

        return content.strip()