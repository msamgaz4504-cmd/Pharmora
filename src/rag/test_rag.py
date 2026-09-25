from src.rag.service import PharmoraRAG


def main():
    rag = PharmoraRAG()

    tests = [
        {
            "cis": "67119691",
            "medicine_name": "DOLIPRANE",
            "question": (
                "Quels sont les effets "
                "indésirables de ce médicament ?"
            ),
        },
        {
            "cis": "63691015",
            "medicine_name": "IBUPROFENE ARROW 5 %, gel",
            "question": (
                "Peut-on utiliser ce médicament "
                "pendant la grossesse ?"
            ),
        },
        {
            "cis": "67459306",
            "medicine_name": "AMOXICILLINE BENTA 500 mg, gélule",
            "question": (
                "Dans quels cas cet antibiotique "
                "est-il utilisé ?"
            ),
        },
    ]

    for index, test in enumerate(
        tests,
        start=1,
    ):
        print(
            f"\n{'=' * 70}"
        )

        print(
            f"TEST {index}"
        )

        print(
            f"Médicament : "
            f"{test['medicine_name']}"
        )

        print(
            f"Question : "
            f"{test['question']}"
        )

        result = rag.ask(
            question=test["question"],
            cis=test["cis"],
            medicine_name=test[
                "medicine_name"
            ],
        )

        print(
            f"\nStatus : "
            f"{result['status']}"
        )

        print(
            "\nRéponse :\n"
        )

        print(
            result["answer"]
        )

        print(
            "\nSources structurées :"
        )

        for source in result[
            "sources"
        ]:
            print(
                f"- [{source['reference']}] "
                f"{source['document_type']} "
                f"{source['section_number']} - "
                f"{source['section_title']}"
            )


if __name__ == "__main__":
    main()