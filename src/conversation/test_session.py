from __future__ import annotations

from src.conversation.session import (
    ConversationSession,
)


DOLIPRANE_CIS = "67119691"
DOLIPRANE_NAME = (
    "DOLIPRANE 500 mg, gélule"
)

IBUPROFENE_CIS = "63691015"
IBUPROFENE_NAME = (
    "IBUPROFENE ARROW 5 %, gel"
)


def check(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(
            message
        )


def test_creation() -> None:
    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    check(
        session.cis
        == DOLIPRANE_CIS,
        "CIS incorrect.",
    )

    check(
        session.medicine_name
        == DOLIPRANE_NAME,
        "Nom incorrect.",
    )

    check(
        session.message_count == 0,
        "La session doit être vide.",
    )

    check(
        session.is_empty(),
        "is_empty doit être True.",
    )


def test_messages() -> None:
    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    user_message = (
        session.add_user_message(
            "Quels sont les effets "
            "indésirables ?"
        )
    )

    assistant_message = (
        session.add_assistant_message(
            "Les sources indiquent..."
        )
    )

    check(
        user_message.role == "user",
        "Rôle user incorrect.",
    )

    check(
        assistant_message.role
        == "assistant",
        "Rôle assistant incorrect.",
    )

    check(
        session.message_count == 2,
        "Deux messages attendus.",
    )

    check(
        bool(user_message.timestamp),
        "Timestamp user absent.",
    )

    check(
        bool(
            assistant_message.timestamp
        ),
        "Timestamp assistant absent.",
    )


def test_recent_turns() -> None:
    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    for index in range(1, 7):
        session.add_user_message(
            f"Question {index}"
        )

        session.add_assistant_message(
            f"Réponse {index}"
        )

    recent = session.recent_turns(
        max_turns=2
    )

    check(
        len(recent) == 4,
        "Deux tours doivent donner "
        "quatre messages.",
    )

    check(
        recent[0].content
        == "Question 5",
        "Le premier message récent "
        "devrait être Question 5.",
    )

    check(
        recent[-1].content
        == "Réponse 6",
        "Le dernier message récent "
        "devrait être Réponse 6.",
    )

    check(
        session.message_count == 12,
        "L'historique complet ne doit "
        "pas être tronqué.",
    )


def test_history_for_llm() -> None:
    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    session.add_user_message(
        "Quels sont les effets "
        "indésirables ?"
    )

    session.add_assistant_message(
        "Réponse sourcée."
    )

    history = (
        session.history_for_llm(
            max_turns=4
        )
    )

    check(
        history
        == [
            {
                "role": "user",
                "content": (
                    "Quels sont les effets "
                    "indésirables ?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Réponse sourcée."
                ),
            },
        ],
        "Format LLM incorrect.",
    )

    check(
        "timestamp"
        not in history[0],
        "Le timestamp ne doit pas "
        "être envoyé au LLM.",
    )


def test_full_history() -> None:
    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    session.add_user_message(
        "Question"
    )

    history = (
        session.full_history()
    )

    check(
        len(history) == 1,
        "Un message attendu.",
    )

    check(
        history[0]["role"]
        == "user",
        "Rôle incorrect.",
    )

    check(
        history[0]["content"]
        == "Question",
        "Contenu incorrect.",
    )

    check(
        "timestamp"
        in history[0],
        "Timestamp absent de "
        "l'historique complet.",
    )


def test_change_medicine() -> None:
    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    session.add_user_message(
        "Question sur Doliprane"
    )

    session.add_assistant_message(
        "Réponse Doliprane"
    )

    session.change_medicine(
        cis=IBUPROFENE_CIS,
        medicine_name=IBUPROFENE_NAME,
    )

    check(
        session.cis
        == IBUPROFENE_CIS,
        "Le CIS n'a pas changé.",
    )

    check(
        session.medicine_name
        == IBUPROFENE_NAME,
        "Le nom n'a pas changé.",
    )

    check(
        session.is_empty(),
        "L'historique doit être "
        "réinitialisé après changement "
        "de médicament.",
    )


def test_same_medicine_keeps_history() -> None:
    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    session.add_user_message(
        "Question"
    )

    session.change_medicine(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    check(
        session.message_count == 1,
        "Sélectionner le même médicament "
        "ne doit pas supprimer "
        "l'historique.",
    )


def test_manual_clear() -> None:
    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    session.add_user_message(
        "Question"
    )

    session.add_assistant_message(
        "Réponse"
    )

    session.clear()

    check(
        session.message_count == 0,
        "clear n'a pas vidé "
        "l'historique.",
    )

    check(
        session.is_empty(),
        "La session doit être vide.",
    )


def test_invalid_inputs() -> None:
    errors = 0

    try:
        ConversationSession(
            cis="",
            medicine_name=DOLIPRANE_NAME,
        )
    except ValueError:
        errors += 1

    try:
        ConversationSession(
            cis=DOLIPRANE_CIS,
            medicine_name="",
        )
    except ValueError:
        errors += 1

    session = ConversationSession(
        cis=DOLIPRANE_CIS,
        medicine_name=DOLIPRANE_NAME,
    )

    try:
        session.add_user_message(
            "   "
        )
    except ValueError:
        errors += 1

    try:
        session.recent_turns(
            max_turns=0
        )
    except ValueError:
        errors += 1

    check(
        errors == 4,
        "Toutes les entrées invalides "
        "n'ont pas été rejetées.",
    )


def main() -> None:
    tests = [
        test_creation,
        test_messages,
        test_recent_turns,
        test_history_for_llm,
        test_full_history,
        test_change_medicine,
        test_same_medicine_keeps_history,
        test_manual_clear,
        test_invalid_inputs,
    ]

    passed = 0

    print("=" * 72)
    print(
        "PHARMORA - TEST CONVERSATION SESSION"
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
        f"PASS : {passed}/{len(tests)}"
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