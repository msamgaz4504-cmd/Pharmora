from __future__ import annotations

from pathlib import Path

from src.application.conversation_service import (
    ConversationService,
)
from src.application.image_medicine_service import (
    ImageMedicineService,
)
from src.conversation.contextualizer import (
    ConversationContextualizer,
)
from src.conversation.session import (
    ConversationSession,
)
from src.rag.service import (
    PharmoraRAG,
)


class ImageConversationService:
    def __init__(
        self,
        image_service: ImageMedicineService | None = None,
        rag: PharmoraRAG | None = None,
        contextualizer: ConversationContextualizer | None = None,
        max_history_turns: int = 4,
    ):
        self.image_service = (
            image_service
            if image_service is not None
            else ImageMedicineService()
        )

        self._rag = (
            rag
            if rag is not None
            else PharmoraRAG()
        )

        self._contextualizer = (
            contextualizer
            if contextualizer is not None
            else ConversationContextualizer()
        )

        if max_history_turns < 1:
            raise ValueError(
                "max_history_turns doit être supérieur ou égal à 1."
            )

        self.max_history_turns = (
            max_history_turns
        )

        self._conversation_service: (
            ConversationService | None
        ) = None

    @property
    def session(
        self,
    ) -> ConversationSession | None:
        return (
            self.image_service
            .medicine_service
            .session
        )

    @property
    def has_active_medicine(
        self,
    ) -> bool:
        return (
            self.image_service
            .medicine_service
            .has_selection
        )

    def select_from_image(
        self,
        image_path: str | Path,
    ) -> dict:
        result = (
            self.image_service
            .identify_and_select(
                image_path
            )
        )

        if result["status"] != "resolved":
            self._conversation_service = None
            return result

        session = self.session

        if session is None:
            raise RuntimeError(
                "La session conversationnelle "
                "n'a pas été créée."
            )

        self._conversation_service = (
            ConversationService(
                session=session,
                rag=self._rag,
                contextualizer=(
                    self._contextualizer
                ),
                max_history_turns=(
                    self.max_history_turns
                ),
            )
        )

        return result

    def ask(
        self,
        question: str,
    ) -> dict:
        if (
            self._conversation_service
            is None
        ):
            raise RuntimeError(
                "Aucun médicament actif. "
                "Une image doit d'abord "
                "être identifiée."
            )

        return (
            self._conversation_service.ask(
                question
            )
        )

    def get_profile(
        self,
    ) -> dict | None:
        return (
            self.image_service
            .medicine_service
            .get_profile()
        )

    def get_display_profile(
        self,
    ) -> dict | None:
        return (
            self.image_service
            .medicine_service
            .get_display_profile()
        )