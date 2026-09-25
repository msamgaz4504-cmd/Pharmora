from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal


Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class ConversationMessage:
    role: Role
    content: str
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)


class ConversationSession:
    def __init__(
        self,
        cis: str,
        medicine_name: str,
    ):
        cis = str(cis).strip()
        medicine_name = medicine_name.strip()

        if not cis:
            raise ValueError(
                "Le CIS du médicament est vide."
            )

        if not medicine_name:
            raise ValueError(
                "Le nom du médicament est vide."
            )

        self._cis = cis
        self._medicine_name = medicine_name
        self._messages: list[
            ConversationMessage
        ] = []

    @property
    def cis(self) -> str:
        return self._cis

    @property
    def medicine_name(self) -> str:
        return self._medicine_name

    @property
    def messages(
        self,
    ) -> list[ConversationMessage]:
        return list(self._messages)

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def add_user_message(
        self,
        content: str,
    ) -> ConversationMessage:
        return self._add_message(
            role="user",
            content=content,
        )

    def add_assistant_message(
        self,
        content: str,
    ) -> ConversationMessage:
        return self._add_message(
            role="assistant",
            content=content,
        )

    def _add_message(
        self,
        role: Role,
        content: str,
    ) -> ConversationMessage:
        content = content.strip()

        if not content:
            raise ValueError(
                "Le contenu du message est vide."
            )

        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=self._now(),
        )

        self._messages.append(
            message
        )

        return message

    def recent_messages(
        self,
        max_messages: int = 8,
    ) -> list[ConversationMessage]:
        if max_messages < 1:
            raise ValueError(
                "max_messages doit être supérieur "
                "ou égal à 1."
            )

        return list(
            self._messages[
                -max_messages:
            ]
        )

    def recent_turns(
        self,
        max_turns: int = 4,
    ) -> list[ConversationMessage]:
        if max_turns < 1:
            raise ValueError(
                "max_turns doit être supérieur "
                "ou égal à 1."
            )

        maximum_messages = (
            max_turns * 2
        )

        return self.recent_messages(
            max_messages=maximum_messages,
        )

    def history_for_llm(
        self,
        max_turns: int = 4,
    ) -> list[dict[str, str]]:
        messages = self.recent_turns(
            max_turns=max_turns,
        )

        return [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in messages
        ]

    def full_history(
        self,
    ) -> list[dict]:
        return [
            message.to_dict()
            for message in self._messages
        ]

    def change_medicine(
        self,
        cis: str,
        medicine_name: str,
        clear_history: bool = True,
    ) -> None:
        cis = str(cis).strip()
        medicine_name = medicine_name.strip()

        if not cis:
            raise ValueError(
                "Le nouveau CIS est vide."
            )

        if not medicine_name:
            raise ValueError(
                "Le nouveau nom du médicament "
                "est vide."
            )

        medicine_changed = (
            cis != self._cis
            or medicine_name
            != self._medicine_name
        )

        self._cis = cis
        self._medicine_name = (
            medicine_name
        )

        if (
            medicine_changed
            and clear_history
        ):
            self.clear()

    def clear(self) -> None:
        self._messages.clear()

    def is_empty(self) -> bool:
        return not self._messages

    def _now(self) -> str:
        return (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        )