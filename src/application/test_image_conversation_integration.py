from __future__ import annotations

import sys

from src.application.image_conversation_service import (
    ImageConversationService,
)


def main() -> None:
    if len(sys.argv) != 2:
        raise RuntimeError(
            "Usage : python -m "
            "src.application."
            "test_image_conversation_integration "
            "<image>"
        )

    service = (
        ImageConversationService()
    )

    print("=" * 72)
    print(
        "PHARMORA - IMAGE + CONVERSATION E2E"
    )
    print("=" * 72)

    selection = (
        service.select_from_image(
            sys.argv[1]
        )
    )

    print()
    print("IMAGE IDENTIFICATION")
    print("-" * 72)

    print(
        "Status :",
        selection["status"],
    )

    if selection["status"] != "resolved":
        raise AssertionError(
            "Le médicament "
            "n'a pas été identifié."
        )

    profile = service.get_profile()

    if profile is None:
        raise AssertionError(
            "Profil médicament absent."
        )

    print(
        "CIS :",
        profile["cis"],
    )

    print(
        "Medicine :",
        profile["name"],
    )

    session = service.session

    if session is None:
        raise AssertionError(
            "Session absente."
        )

    print(
        "Session CIS :",
        session.cis,
    )

    print(
        "Session medicine :",
        session.medicine_name,
    )

    question = (
        "Quels sont ses effets "
        "indésirables ?"
    )

    print()
    print("QUESTION")
    print("-" * 72)
    print(question)

    result = service.ask(
        question
    )

    print()
    print("RAG")
    print("-" * 72)

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

    print(
        "Standalone query :",
        result.get(
            "standalone_query"
        ),
    )

    print(
        "Retrieval query :",
        result.get(
            "retrieval_query"
        ),
    )

    print()
    print("ANSWER")
    print("-" * 72)

    print(
        result.get(
            "answer"
        )
    )

    print()
    print("SOURCES")
    print("-" * 72)

    for source in result.get(
        "sources",
        [],
    ):
        print(
            source.get(
                "reference"
            ),
            "-",
            source.get(
                "section_number"
            ),
            source.get(
                "section_title"
            ),
        )

    if result.get(
        "status"
    ) != "answered":
        raise AssertionError(
            "Le RAG n'a pas répondu."
        )

    if not result.get(
        "sources"
    ):
        raise AssertionError(
            "Aucune source retournée."
        )

    if session.message_count != 2:
        raise AssertionError(
            "L'historique doit "
            "contenir 2 messages."
        )

    if (
        session.cis
        != profile["cis"]
    ):
        raise AssertionError(
            "Le CIS de la session "
            "ne correspond pas "
            "au médicament identifié."
        )

    print()
    print("HISTORY")
    print("-" * 72)

    for message in (
        session.full_history()
    ):
        print(
            message["role"],
            ":",
            message["content"],
        )

    print()
    print(
        "STATUS FINAL : PASS"
    )


if __name__ == "__main__":
    main()