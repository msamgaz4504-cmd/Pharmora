from __future__ import annotations

from src.application.conversation_service import (
    ConversationService,
)
from src.conversation.session import (
    ConversationSession,
)

import re
import time

from groq import RateLimitError

DOLIPRANE_CIS = "67119691"
DOLIPRANE_NAME = (
    "DOLIPRANE 500 mg, gélule"
)

def ask_with_retry(
    service: ConversationService,
    question: str,
) -> dict:
    try:
        return service.ask(
            question
        )

    except RateLimitError as error:
        message = str(
            error
        )

        match = re.search(
            r"try again in\s+"
            r"([0-9.]+)s",
            message,
            flags=re.IGNORECASE,
        )

        if match is None:
            raise

        wait_seconds = float(
            match.group(1)
        )

        if wait_seconds > 60:
            raise

        wait_seconds += 1.0

        print(
            f"Rate limit TPM : "
            f"nouvelle tentative dans "
            f"{wait_seconds:.1f}s."
        )

        time.sleep(
            wait_seconds
        )

        return service.ask(
            question
        )

def check(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(
            message
        )


def print_result(
    title: str,
    result: dict,
) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)

    print(
        "Status :",
        result.get(
            "status"
        ),
    )

    print(
        "Request type :",
        result.get(
            "request_type"
        ),
    )

    print()
    print("QUESTION")
    print("-" * 72)

    print(
        "Question originale :",
        result.get(
            "original_question"
        ),
    )

    print(
        "Standalone query :",
        result.get(
            "standalone_query"
        ),
    )

    print(
        "Conversation rewritten :",
        result.get(
            "conversation_rewritten"
        ),
    )

    print()
    print("RAG")
    print("-" * 72)

    print(
        "Retrieval query :",
        result.get(
            "retrieval_query"
        ),
    )

    print(
        "Query rewritten :",
        result.get(
            "query_rewritten"
        ),
    )

    print(
        "Evidence reason :",
        result.get(
            "evidence_reason"
        ),
    )

    print(
        "Invalid citations :",
        result.get(
            "invalid_citations"
        ),
    )

    print()
    print("CANDIDATS RETRIEVAL")
    print("-" * 72)

    candidates = result.get(
        "candidates",
        [],
    )

    print(
        "Nombre de candidats :",
        len(candidates),
    )

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        print()
        print(
            f"Candidat {index}"
        )

        print(
            "Score :",
            candidate.get(
                "score"
            ),
        )

        print(
            "Dense score :",
            candidate.get(
                "dense_score"
            ),
        )

        print(
            "Document :",
            candidate.get(
                "document_type"
            ),
        )

        print(
            "Section :",
            candidate.get(
                "section_number"
            ),
            "-",
            candidate.get(
                "section_title"
            ),
        )

        content = str(
            candidate.get(
                "content",
                "",
            )
        ).strip()

        print(
            "Contenu :",
            content[:500],
        )

        if len(content) > 500:
            print(
                "[contenu tronqué]"
            )

    print()
    print("PASSAGES SELECTIONNES")
    print("-" * 72)

    passages = result.get(
        "passages",
        [],
    )

    print(
        "Nombre de passages :",
        len(passages),
    )

    for index, passage in enumerate(
        passages,
        start=1,
    ):
        print()
        print(
            f"Passage {index}"
        )

        print(
            "Document :",
            passage.get(
                "document_type"
            ),
        )

        print(
            "Section :",
            passage.get(
                "section_number"
            ),
            "-",
            passage.get(
                "section_title"
            ),
        )

        content = str(
            passage.get(
                "content",
                "",
            )
        ).strip()

        print(
            "Contenu :",
            content,
        )

    print()
    print("REPONSE GENEREE")
    print("-" * 72)

    print(
        result.get(
            "answer"
        )
    )

    print()
    print("SOURCES FINALES")
    print("-" * 72)

    sources = result.get(
        "sources",
        [],
    )

    print(
        "Nombre de sources :",
        len(sources),
    )

    for source in sources:
        print()
        print(
            "Référence :",
            source.get(
                "reference"
            ),
        )

        print(
            "Document :",
            source.get(
                "document_type"
            ),
        )

        print(
            "Section :",
            source.get(
                "section_number"
            ),
            "-",
            source.get(
                "section_title"
            ),
        )

        print(
            "Source :",
            source.get(
                "source"
            ),
        )

        print(
            "URL :",
            source.get(
                "source_url"
            ),
        )


def main() -> None:
    print("=" * 72)
    print(
        "PHARMORA - TEST "
        "CONVERSATION E2E"
    )
    print("=" * 72)

    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    service = ConversationService(
        session=session,
        max_history_turns=4,
    )

    passed = 0
    total = 2

    try:
        first = ask_with_retry(
            service,
            "Quels sont les effets indésirables de ce médicament ?",
        )

        print_result(
            "TOUR 1",
            first,
        )

        check(
            first["status"]
            == "answered",
            "Le premier tour doit être answered.",
        )

        check(
            first["request_type"]
            == "informational",
            "Le premier tour doit être informational.",
        )

        check(
            first[
                "conversation_rewritten"
            ]
            is False,
            "La première question ne doit pas "
            "être contextualisée.",
        )

        check(
            bool(
                first["sources"]
            ),
            "Le premier tour doit avoir "
            "au moins une source.",
        )

        check(
            session.message_count == 2,
            "Le premier tour doit produire "
            "deux messages dans la session.",
        )

        passed += 1

        print()
        print("TOUR 1 : PASS")

    except Exception as error:
        print()
        print("TOUR 1 : FAIL")

        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        print()
        print(
            "TEST ARRÊTÉ : "
            "le premier tour est nécessaire "
            "pour tester le follow-up."
        )

        print()
        print("=" * 72)
        print("RESULTATS")
        print("=" * 72)

        print(
            f"PASS : {passed}/{total}"
        )

        print(
            "STATUS FINAL : REVIEW REQUIRED"
        )

        return

    try:
        second = ask_with_retry(
            service,
            "Et pendant la grossesse ?",
        )

        print_result(
            "TOUR 2",
            second,
        )

        standalone_query = (
            second[
                "standalone_query"
            ].strip()
        )

        check(
            second["status"]
            == "answered",
            "Le second tour doit être answered.",
        )

        check(
            second["request_type"]
            == "informational",
            "La question générale sur "
            "la grossesse doit rester informational.",
        )

        check(
            second[
                "conversation_rewritten"
            ]
            is True,
            "Le follow-up doit être contextualisé.",
        )

        check(
            standalone_query
            != "Et pendant la grossesse ?",
            "La requête autonome doit être "
            "différente du follow-up original.",
        )

        check(
            "grossesse"
            in standalone_query.lower(),
            "La requête autonome doit conserver "
            "le thème explicite de la grossesse.",
        )

        check(
            "effets indésirables"
            not in standalone_query.lower(),
            "Le contextualizer ne doit pas "
            "transporter automatiquement "
            "le sujet précédent.",
        )

        check(
            "doliprane"
            in standalone_query.lower(),
            "La requête autonome doit identifier "
            "le médicament actif.",
        )

        check(
            bool(
                second["sources"]
            ),
            "Le second tour doit avoir "
            "au moins une source.",
        )

        check(
            session.message_count == 4,
            "Deux tours doivent produire "
            "quatre messages dans la session.",
        )

        check(
            session.messages[
                -2
            ].content
            == "Et pendant la grossesse ?",
            "La session doit conserver "
            "la question originale.",
        )

        passed += 1

        print()
        print("TOUR 2 : PASS")

    except Exception as error:
        print()
        print("TOUR 2 : FAIL")

        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

    print()
    print("=" * 72)
    print("HISTORIQUE FINAL")
    print("=" * 72)

    for index, message in enumerate(
        session.messages,
        start=1,
    ):
        print()
        print(
            f"{index}. "
            f"{message.role.upper()}"
        )

        print(
            message.content
        )

    print()
    print("=" * 72)
    print("RESULTATS")
    print("=" * 72)

    print(
        f"PASS : {passed}/{total}"
    )

    print(
        "Messages dans la session :",
        session.message_count,
    )

    if passed == total:
        print(
            "STATUS FINAL : PASS"
        )
    else:
        print(
            "STATUS FINAL : REVIEW REQUIRED"
        )


if __name__ == "__main__":
    main()