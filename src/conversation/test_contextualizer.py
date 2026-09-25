from __future__ import annotations

import json

from src.conversation.contextualizer import (
    ConversationContextualizer,
)


MEDICINE_NAME = (
    "DOLIPRANE 500 mg, gélule"
)


class FakeMessage:
    def __init__(
        self,
        content: str,
    ):
        self.content = content


class FakeChoice:
    def __init__(
        self,
        content: str,
    ):
        self.message = FakeMessage(
            content
        )


class FakeResponse:
    def __init__(
        self,
        content: str,
    ):
        self.choices = [
            FakeChoice(
                content
            )
        ]


class FakeCompletions:
    def __init__(
        self,
        standalone_query: str,
        context_relation: str = "continuation",
    ):
        self.standalone_query = (
            standalone_query
        )

        self.context_relation = (
            context_relation
        )

        self.call_count = 0
        self.last_kwargs = None

    def create(
        self,
        **kwargs,
    ):
        self.call_count += 1
        self.last_kwargs = kwargs

        return FakeResponse(
            json.dumps(
                {
                    "context_relation": (
                        self.context_relation
                    ),
                    "standalone_query": (
                        self.standalone_query
                    ),
                }
            )
        )


class FakeChat:
    def __init__(
        self,
        completions: FakeCompletions,
    ):
        self.completions = completions


class FakeClient:
    def __init__(
        self,
        standalone_query: str,
        context_relation: str = "continuation",
    ):
        self.completions = (
            FakeCompletions(
                standalone_query=(
                    standalone_query
                ),
                context_relation=(
                    context_relation
                ),
            )
        )

        self.chat = FakeChat(
            self.completions
        )


def check(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise AssertionError(
            message
        )


def test_no_history_no_llm_call() -> None:
    client = FakeClient(
        standalone_query=(
            "Cette réponse ne doit "
            "jamais être utilisée."
        ),
        context_relation="standalone",
    )

    contextualizer = (
        ConversationContextualizer(
            client=client
        )
    )

    question = (
        "Quels sont les effets "
        "indésirables ?"
    )

    result = (
        contextualizer.contextualize(
            question=question,
            medicine_name=MEDICINE_NAME,
            history=[],
        )
    )

    check(
        result["standalone_query"]
        == question,
        "Sans historique, la question "
        "doit rester inchangée.",
    )

    check(
        result["rewritten"]
        is False,
        "rewritten doit être False.",
    )

    check(
        client.completions.call_count
        == 0,
        "Aucun appel LLM ne doit être "
        "effectué sans historique.",
    )


def test_follow_up_rewrite() -> None:
    standalone_query = (
        "Que dit le RCP concernant "
        "l'utilisation de DOLIPRANE "
        "500 mg, gélule pendant "
        "la grossesse ?"
    )

    client = FakeClient(
        standalone_query=(
            standalone_query
        ),
        context_relation="new_topic",
    )

    contextualizer = (
        ConversationContextualizer(
            client=client
        )
    )

    history = [
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
                "Réponse pharmaceutique "
                "sourcée."
            ),
        },
    ]

    result = (
        contextualizer.contextualize(
            question=(
                "Et pendant la grossesse ?"
            ),
            medicine_name=MEDICINE_NAME,
            history=history,
        )
    )

    check(
        result["standalone_query"]
        == standalone_query,
        "La requête autonome "
        "est incorrecte.",
    )

    check(
        result["rewritten"]
        is True,
        "La question doit être "
        "marquée comme réécrite.",
    )

    check(
        client.completions.call_count
        == 1,
        "Un seul appel LLM est attendu.",
    )


def test_prompt_contains_context() -> None:
    client = FakeClient(
        standalone_query=(
            "Question autonome"
        ),
        context_relation="continuation",
    )

    contextualizer = (
        ConversationContextualizer(
            client=client
        )
    )

    history = [
        {
            "role": "user",
            "content": (
                "Première question"
            ),
        },
        {
            "role": "assistant",
            "content": (
                "Première réponse"
            ),
        },
    ]

    contextualizer.contextualize(
        question="Et ensuite ?",
        medicine_name=MEDICINE_NAME,
        history=history,
    )

    kwargs = (
        client.completions.last_kwargs
    )

    check(
        kwargs is not None,
        "Les paramètres de l'appel "
        "sont absents.",
    )

    messages = kwargs[
        "messages"
    ]

    user_prompt = messages[
        1
    ]["content"]

    check(
        MEDICINE_NAME
        in user_prompt,
        "Le médicament actif doit "
        "être présent dans le prompt.",
    )

    check(
        "Première question"
        in user_prompt,
        "La question historique "
        "est absente.",
    )

    check(
        "Première réponse"
        in user_prompt,
        "La réponse historique "
        "est absente.",
    )

    check(
        "Et ensuite ?"
        in user_prompt,
        "La question actuelle "
        "est absente.",
    )


def test_structured_output_contract() -> None:
    client = FakeClient(
        standalone_query=(
            "Question autonome"
        ),
        context_relation="new_topic",
    )

    contextualizer = (
        ConversationContextualizer(
            client=client
        )
    )

    contextualizer.contextualize(
        question="Et la grossesse ?",
        medicine_name=MEDICINE_NAME,
        history=[
            {
                "role": "user",
                "content": "Question",
            }
        ],
    )

    kwargs = (
        client.completions.last_kwargs
    )

    response_format = kwargs[
        "response_format"
    ]

    check(
        response_format["type"]
        == "json_schema",
        "Le format doit être "
        "json_schema.",
    )

    schema = (
        response_format[
            "json_schema"
        ]
    )

    check(
        schema["strict"] is True,
        "Le JSON Schema doit "
        "être strict.",
    )

    required = (
        schema[
            "schema"
        ][
            "required"
        ]
    )

    check(
        "standalone_query"
        in required,
        "standalone_query doit être "
        "obligatoire.",
    )

    check(
        "context_relation"
        in required,
        "context_relation doit être "
        "obligatoire.",
    )

    relation_schema = (
        schema[
            "schema"
        ][
            "properties"
        ][
            "context_relation"
        ]
    )

    check(
        set(
            relation_schema[
                "enum"
            ]
        )
        == {
            "new_topic",
            "continuation",
            "standalone",
        },
        "Les relations conversationnelles "
        "sont incorrectes.",
    )


def test_same_question() -> None:
    question = (
        "Quels sont les effets "
        "indésirables ?"
    )

    client = FakeClient(
        standalone_query=question,
        context_relation="standalone",
    )

    contextualizer = (
        ConversationContextualizer(
            client=client
        )
    )

    result = (
        contextualizer.contextualize(
            question=question,
            medicine_name=MEDICINE_NAME,
            history=[
                {
                    "role": "user",
                    "content": (
                        "Question précédente"
                    ),
                }
            ],
        )
    )

    check(
        result["rewritten"]
        is False,
        "Une question conservée "
        "ne doit pas être considérée "
        "comme réécrite.",
    )


def test_invalid_question() -> None:
    client = FakeClient(
        standalone_query="Question",
        context_relation="standalone",
    )

    contextualizer = (
        ConversationContextualizer(
            client=client
        )
    )

    errors = 0

    try:
        contextualizer.contextualize(
            question="   ",
            medicine_name=MEDICINE_NAME,
            history=[],
        )
    except ValueError:
        errors += 1

    try:
        contextualizer.contextualize(
            question="Question",
            medicine_name="   ",
            history=[],
        )
    except ValueError:
        errors += 1

    check(
        errors == 2,
        "Les entrées invalides "
        "ne sont pas toutes rejetées.",
    )


def test_invalid_history() -> None:
    client = FakeClient(
        standalone_query="Question",
        context_relation="standalone",
    )

    contextualizer = (
        ConversationContextualizer(
            client=client
        )
    )

    errors = 0

    try:
        contextualizer.contextualize(
            question="Question",
            medicine_name=MEDICINE_NAME,
            history="invalid",
        )
    except TypeError:
        errors += 1

    try:
        contextualizer.contextualize(
            question="Question",
            medicine_name=MEDICINE_NAME,
            history=[
                {
                    "role": "system",
                    "content": "Message",
                }
            ],
        )
    except ValueError:
        errors += 1

    try:
        contextualizer.contextualize(
            question="Question",
            medicine_name=MEDICINE_NAME,
            history=[
                {
                    "role": "user",
                    "content": "   ",
                }
            ],
        )
    except ValueError:
        errors += 1

    check(
        errors == 3,
        "Les historiques invalides "
        "ne sont pas tous rejetés.",
    )


def test_invalid_context_relation() -> None:
    client = FakeClient(
        standalone_query=(
            "Question autonome"
        ),
        context_relation="invalid_relation",
    )

    contextualizer = (
        ConversationContextualizer(
            client=client
        )
    )

    error = False

    try:
        contextualizer.contextualize(
            question="Et ensuite ?",
            medicine_name=MEDICINE_NAME,
            history=[
                {
                    "role": "user",
                    "content": (
                        "Question précédente"
                    ),
                }
            ],
        )
    except RuntimeError:
        error = True

    check(
        error,
        "Une relation invalide doit "
        "être rejetée.",
    )


def main() -> None:
    tests = [
        test_no_history_no_llm_call,
        test_follow_up_rewrite,
        test_prompt_contains_context,
        test_structured_output_contract,
        test_same_question,
        test_invalid_question,
        test_invalid_history,
        test_invalid_context_relation,
    ]

    passed = 0

    print("=" * 72)
    print(
        "PHARMORA - TEST "
        "CONVERSATION CONTEXTUALIZER"
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