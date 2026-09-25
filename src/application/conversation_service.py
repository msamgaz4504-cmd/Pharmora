from __future__ import annotations

from src.conversation.contextualizer import (
    ConversationContextualizer,
)
from src.conversation.session import (
    ConversationSession,
)
from src.rag.service import (
    PharmoraRAG,
)


class ConversationService:
    def __init__(
        self,
        session: ConversationSession,
        rag: PharmoraRAG | None = None,
        contextualizer: ConversationContextualizer | None = None,
        max_history_turns: int = 4,
    ):
        if not isinstance(
            session,
            ConversationSession,
        ):
            raise TypeError(
                "session doit être une ConversationSession."
            )

        if max_history_turns < 1:
            raise ValueError(
                "max_history_turns doit être supérieur ou égal à 1."
            )

        self.session = session

        self.rag = (
            rag
            if rag is not None
            else PharmoraRAG()
        )

        self.contextualizer = (
            contextualizer
            if contextualizer is not None
            else ConversationContextualizer()
        )

        self.max_history_turns = (
            max_history_turns
        )

    def ask(
        self,
        question: str,
    ) -> dict:
        question = question.strip()

        if not question:
            raise ValueError(
                "La question est vide."
            )

        history = (
            self.session.history_for_llm(
                max_turns=self.max_history_turns
            )
        )

        context_result = (
            self.contextualizer.contextualize(
                question=question,
                medicine_name=(
                    self.session.medicine_name
                ),
                history=history,
            )
        )

        standalone_query = (
            context_result[
                "standalone_query"
            ]
        )

        rag_result = self.rag.ask(
            question=standalone_query,
            cis=self.session.cis,
            medicine_name=(
                self.session.medicine_name
            ),
        )

        answer = str(
            rag_result.get(
                "answer",
                "",
            )
        ).strip()

        self.session.add_user_message(
            question
        )

        if answer:
            self.session.add_assistant_message(
                answer
            )

        result = dict(
            rag_result
        )

        result[
            "original_question"
        ] = question

        result[
            "standalone_query"
        ] = standalone_query

        result[
            "conversation_rewritten"
        ] = context_result[
            "rewritten"
        ]

        result[
            "conversation_history_size"
        ] = self.session.message_count

        return result