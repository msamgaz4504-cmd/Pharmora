from __future__ import annotations

from src.application.conversation_service import (
    ConversationService,
)
from src.conversation.session import (
    ConversationSession,
)


DOLIPRANE_CIS = "67119691"

DOLIPRANE_NAME = (
    "DOLIPRANE 500 mg, gélule"
)


class FakeContextualizer:
    def __init__(
        self,
        standalone_query: str | None = None,
        rewritten: bool = False,
    ):
        self.standalone_query = (
            standalone_query
        )

        self.rewritten = rewritten

        self.call_count = 0
        self.last_question = None
        self.last_medicine_name = None
        self.last_history = None

    def contextualize(
        self,
        question: str,
        medicine_name: str,
        history: list[dict[str, str]],
    ) -> dict:
        self.call_count += 1

        self.last_question = question
        self.last_medicine_name = (
            medicine_name
        )
        self.last_history = list(
            history
        )

        return {
            "standalone_query": (
                self.standalone_query
                if self.standalone_query
                is not None
                else question
            ),
            "rewritten": self.rewritten,
        }


class FakeRAG:
    def __init__(
        self,
        status: str = "answered",
        answer: str = (
            "Réponse pharmaceutique sourcée."
        ),
    ):
        self.status = status
        self.answer = answer

        self.call_count = 0
        self.last_question = None
        self.last_cis = None
        self.last_medicine_name = None

    def ask(
        self,
        question: str,
        cis: str,
        medicine_name: str,
    ) -> dict:
        self.call_count += 1

        self.last_question = question
        self.last_cis = cis
        self.last_medicine_name = (
            medicine_name
        )

        return {
            "status": self.status,
            "answer": self.answer,
            "sources": [],
            "passages": [],
            "candidates": [],
            "evidence_reason": "",
            "invalid_citations": [],
            "retrieval_query": question,
            "query_rewritten": False,
            "request_type": "informational",
        }


def check(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(
            message
        )


def create_session() -> ConversationSession:
    return ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )


def test_first_question() -> None:
    session = create_session()

    contextualizer = (
        FakeContextualizer()
    )

    rag = FakeRAG()

    service = ConversationService(
        session=session,
        rag=rag,
        contextualizer=contextualizer,
    )

    result = service.ask(
        "Quels sont les effets indésirables ?"
    )

    check(
        contextualizer.call_count == 1,
        "Le contextualizer doit être appelé une fois.",
    )

    check(
        contextualizer.last_history == [],
        "La première question doit avoir un historique vide.",
    )

    check(
        rag.call_count == 1,
        "Le RAG doit être appelé une fois.",
    )

    check(
        rag.last_question
        == "Quels sont les effets indésirables ?",
        "La mauvaise question a été envoyée au RAG.",
    )

    check(
        session.message_count == 2,
        "La question et la réponse doivent être enregistrées.",
    )

    check(
        result["conversation_rewritten"]
        is False,
        "La première question ne doit pas être marquée comme réécrite.",
    )


def test_follow_up() -> None:
    session = create_session()

    session.add_user_message(
        "Quels sont les effets indésirables ?"
    )

    session.add_assistant_message(
        "Réponse précédente."
    )

    standalone_query = (
        "Que dit le RCP concernant "
        "DOLIPRANE 500 mg, gélule "
        "pendant la grossesse ?"
    )

    contextualizer = FakeContextualizer(
        standalone_query=standalone_query,
        rewritten=True,
    )

    rag = FakeRAG()

    service = ConversationService(
        session=session,
        rag=rag,
        contextualizer=contextualizer,
    )

    result = service.ask(
        "Et pendant la grossesse ?"
    )

    check(
        len(
            contextualizer.last_history
        )
        == 2,
        "L'historique précédent doit être transmis.",
    )

    check(
        rag.last_question
        == standalone_query,
        "Le RAG doit recevoir la requête contextualisée.",
    )

    check(
        result[
            "original_question"
        ]
        == "Et pendant la grossesse ?",
        "La question originale doit être conservée.",
    )

    check(
        result[
            "standalone_query"
        ]
        == standalone_query,
        "La requête autonome doit être exposée.",
    )

    check(
        result[
            "conversation_rewritten"
        ]
        is True,
        "Le follow-up doit être marqué comme réécrit.",
    )

    check(
        session.message_count == 4,
        "Le nouveau tour doit être ajouté à l'historique.",
    )

    check(
        session.messages[-2].content
        == "Et pendant la grossesse ?",
        "L'historique doit conserver la question originale.",
    )


def test_rag_identity() -> None:
    session = create_session()

    contextualizer = (
        FakeContextualizer()
    )

    rag = FakeRAG()

    service = ConversationService(
        session=session,
        rag=rag,
        contextualizer=contextualizer,
    )

    service.ask(
        "Question"
    )

    check(
        rag.last_cis
        == DOLIPRANE_CIS,
        "Le mauvais CIS a été envoyé au RAG.",
    )

    check(
        rag.last_medicine_name
        == DOLIPRANE_NAME,
        "Le mauvais médicament a été envoyé au RAG.",
    )


def test_history_limit() -> None:
    session = create_session()

    for index in range(
        1,
        7,
    ):
        session.add_user_message(
            f"Question {index}"
        )

        session.add_assistant_message(
            f"Réponse {index}"
        )

    contextualizer = (
        FakeContextualizer()
    )

    rag = FakeRAG()

    service = ConversationService(
        session=session,
        rag=rag,
        contextualizer=contextualizer,
        max_history_turns=2,
    )

    service.ask(
        "Nouvelle question"
    )

    history = (
        contextualizer.last_history
    )

    check(
        len(history) == 4,
        "Deux tours maximum doivent être envoyés.",
    )

    check(
        history[0]["content"]
        == "Question 5",
        "L'historique doit contenir les tours les plus récents.",
    )

    check(
        history[-1]["content"]
        == "Réponse 6",
        "Le dernier ancien message est incorrect.",
    )


def test_blocked_response_is_stored() -> None:
    session = create_session()

    contextualizer = (
        FakeContextualizer()
    )

    rag = FakeRAG(
        status=(
            "medical_decision_blocked"
        ),
        answer=(
            "Je ne peux pas décider "
            "si vous devez prendre "
            "ce médicament."
        ),
    )

    service = ConversationService(
        session=session,
        rag=rag,
        contextualizer=contextualizer,
    )

    result = service.ask(
        "Dois-je le prendre ?"
    )

    check(
        result["status"]
        == "medical_decision_blocked",
        "Le statut du RAG doit être conservé.",
    )

    check(
        session.message_count == 2,
        "Une réponse guardrail doit aussi être enregistrée.",
    )


def test_empty_answer() -> None:
    session = create_session()

    contextualizer = (
        FakeContextualizer()
    )

    rag = FakeRAG(
        status="error",
        answer="",
    )

    service = ConversationService(
        session=session,
        rag=rag,
        contextualizer=contextualizer,
    )

    service.ask(
        "Question"
    )

    check(
        session.message_count == 1,
        "Une réponse vide ne doit pas créer de message assistant.",
    )

    check(
        session.messages[0].role
        == "user",
        "La question utilisateur doit rester enregistrée.",
    )


def test_invalid_question() -> None:
    session = create_session()

    service = ConversationService(
        session=session,
        rag=FakeRAG(),
        contextualizer=(
            FakeContextualizer()
        ),
    )

    error = False

    try:
        service.ask(
            "   "
        )
    except ValueError:
        error = True

    check(
        error,
        "Une question vide doit être rejetée.",
    )

    check(
        session.message_count == 0,
        "Une question invalide ne doit pas modifier l'historique.",
    )


def test_invalid_history_limit() -> None:
    error = False

    try:
        ConversationService(
            session=create_session(),
            rag=FakeRAG(),
            contextualizer=(
                FakeContextualizer()
            ),
            max_history_turns=0,
        )
    except ValueError:
        error = True

    check(
        error,
        "Une limite d'historique invalide doit être rejetée.",
    )


def main() -> None:
    tests = [
        test_first_question,
        test_follow_up,
        test_rag_identity,
        test_history_limit,
        test_blocked_response_is_stored,
        test_empty_answer,
        test_invalid_question,
        test_invalid_history_limit,
    ]

    passed = 0

    print("=" * 72)
    print(
        "PHARMORA - TEST "
        "CONVERSATION SERVICE"
    )
    print("=" * 72)

    for test in tests:
        try:
            test()

            passed += 1

            print(
                f"PASS - {test.__name__}"
            )

        except Exception as error:
            print(
                f"FAIL - {test.__name__}"
            )

            print(
                f"       "
                f"{type(error).__name__}: "
                f"{error}"
            )

    print()
    print("=" * 72)
    print("RESULTATS")
    print("=" * 72)

    print(
        f"PASS : "
        f"{passed}/{len(tests)}"
    )

    if passed == len(tests):
        print(
            "STATUS FINAL : PASS"
        )
    else:
        print(
            "STATUS FINAL : REVIEW REQUIRED"
        )


if __name__ == "__main__":
    main()